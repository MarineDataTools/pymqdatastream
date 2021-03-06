"""
.. module:: datastream
   :platform: Unix, Windows
   :synopsis: The datastream module

.. moduleauthor:: Peter Holterman <peter.holtermann@io-warnemuende.de>



This module is the basis of pymqdatastream. Here the three classes datastream, 
Stream and zmq_sockets are defined. Each datastream object consists of at least
one Stream of type "control". Each Stream is connected to a zmq_socket.

.. note::
   TODO: 
   
   * remove sockets from DataStream object
   * Do socket init into Stream object, Streams should now their sockets, DataStreams not
   * put zmw_socket=None and use local socket for wait_for_request_and_reply()
     to make it thread save, similar to start_poll_substream_thread()

"""


import numpy as np
import time
import datetime
import json
import ubjson
import collections
import zmq
import os
try:
    import queue as queue # python 3
except:
    import Queue as queue # python 2.7

import threading
import uuid as uuid_mod
# Get the version
from pkg_resources import Requirement, resource_filename
filename = resource_filename(Requirement.parse('pymqdatastream'),'pymqdatastream/VERSION')

with open(filename) as version_file:
    version = version_file.read().strip()

__datastream_version__ = version

import uuid as uuid_module
import sys
import logging

# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('datastream')
logger.setLevel(logging.INFO)

# Create a zmq Context if not already existing
if 'Context' in globals():
    logger.debug('A zmq context is already existing, will not create a new one')
else:
    logger.debug('Creating zmq Context')
    Context = zmq.Context()




# TODO:
# Control socket is partly thread, partly direct send in stream object. Do it fully thread controlled
# Pubstream: Add a thread, which is regularly reading the deque and sending the data
class zmq_socket(object):
    """
    A class of a zmq socket for the actual connection. The main ingredien of this objects is a zmq_socket
    which is in self.zmq_socket.
    
    Args:
       socket_type (str): socket type of stream object: e.g. 'control', 'remote_control', 'pubstream', 'substream',
        
          * control: A control socket (zmq.REP) used to communicate the basic informations between the datastream objects
          * remote_control: A socket to send requests via a zmq.REQ socket to a control socket. This socket is used to receive informations of a remote control socket
          * pubstream: A publish socket (zmq.PUB), the standard way to distribute data
          * substream: A subscribe socket (zmq.SUB), used to subscribe to a pubstream socket
          * repstream: A reply socket (zmq.REP) answering request send from a reqstream
          * reqstream: A request socket (zmq.REQ), sending request and expecting answer from a repstream

       address (str): zmq address string, e.g. address = 'tcp://127.0.0.1:20000'
       deque:
       socket_reply_function: For control and rep socket a reply function to process the reply is needed
       filter_uuid (str): message filter for the subscribe sockets, default '', only use it if a 'substream' socket is created
       connect (bool): If True a zmq bind will be done [default=True]
       remote (bool): If True the socket is remote and information is of informative type
       statistic (bool): Collect statistics
       logging_level (str or logging.DEBUG etc.): 


    """
    def __init__(self, socket_type, address = '', deque = None, socket_reply_function = None, filter_uuid = '', connect = True, remote = False, statistic = False, logging_level='INFO'):
        """
        """
        funcname = '__init__()'
        self.logger = logging.getLogger(self.__class__.__name__ + '(' + socket_type + ')')
        self.logging_level = logging_level
        if((logging_level == 'DEBUG') | (logging_level == logging.DEBUG)):
            self.logger.setLevel(logging.DEBUG)
        elif((logging_level == 'INFO') | (logging_level == logging.INFO)):
            self.logger.setLevel(logging.INFO)            
        else:
            self.logger.setLevel(logging.CRITICAL)

        self.logger.debug(funcname + ': socket_type:' + socket_type)
        
        self.context = Context
        self.uuid = 'pymqds_' + __datastream_version__ + '_zmq_socket_' + socket_type +  ':' + str(uuid_module.uuid1())
        self.socket_type = socket_type
        self.address = address
        self.logger.debug(funcname + ': address:' + str(self.address))
        self.filter_uuid = filter_uuid
        self.connected = False
        self.do_statistic = False
        self.deque = deque
        self.packets = 0 # Packets sent via pub_data
        self.thread_queue = None
    
        # The serialise function
        #self.dumps = self.dumps_json
        #self.loads = self.loads_json
        # binary json
        self.dumps = self.dumps_ubjson
        self.loads = self.loads_ubjson
        
        if(statistic):
            self.do_statistic = True
            self.statistic = {}
            self.statistic['packets_received'] = 0
            self.statistic['bytes_received'] = 0            
            self.statistic['packets_sent'] = 0            

        # Test which kind of socket is to initialize
        # The sockets which will need a zmq 'bind'
        if(socket_type == 'control' or socket_type == 'repstream'):
            self.zmq_socket_type = zmq.REP
            # Init the function of the control socket reply thread 
            if(socket_reply_function == None):
                self.socket_reply_function = self.process_client_request_bare
            else:
                self.socket_reply_function = socket_reply_function

            # bind the socket if its a local socket
            if((connect == True) and (remote == False)):
                ret = self.bind_socket(self.zmq_socket_type,self.address)

                if(ret):
                    self.logger.debug(funcname + ': succeeded')
                    #if(self.socket_type == 'control'):
                    if(True):
                        # There is now a socket, lets start a blocking thread for reading and answering control requests/replies
                        # http://stackoverflow.com/questions/2846653/python-multithreading-for-dummies
                        self.logger.debug(funcname + ': Start request reply thread')
                        self.thread_queue = queue.Queue()
                        self.reply_thread = threading.Thread(target=self.wait_for_request_and_reply)
                        self.reply_thread.daemon = True
                        self.reply_thread.start()
                else:
                    raise Exception("zmq_socket_init_failed")

        # pubstream
        elif(socket_type == 'pubstream'):
            self.zmq_socket_type = zmq.PUB

            # bind the socket if its a local socket
            if((connect == True) and (remote == False)):
                ret = self.bind_socket(self.zmq_socket_type,self.address)
                # Start the pubstream thread, to put the socket into a thread
                if(ret):
                    self.start_pub_data_thread()
        #
        #   
        # These sockets need a zmq 'connect'
        #
        #
        # substream
        elif(socket_type == 'substream'):
            self.zmq_socket_type = zmq.SUB
            self.local_uuid = 'pyds_' + __datastream_version__ + '_zmq_socket_' + socket_type +  ':' + str(uuid_module.uuid1())
            if((connect == True) and (remote == False)):
                # Get a zmq socket and start a thread with this
                self.connect_socket(filter_uuid = self.filter_uuid)
                self.start_poll_substream_thread()
                

        # 'remote_control'
        elif(socket_type == 'remote_control'):
            self.zmq_socket_type = zmq.REQ
            if((connect == True) and (remote == False)):
                ret = self.connect_socket(filter_uuid = '')
                self.send_req = self._send_req_
                self.get_rep = self._get_rep_


        
        # 'reqstream'
        elif(socket_type == 'reqstream'):
            self.zmq_socket_type = zmq.REQ
            if((connect == True) and (remote == False)):
                ret = self.connect_socket(filter_uuid = '')
                self.send_req = self._send_req_
                self.get_rep = self._get_rep_
                
        else:
            raise Exception("unknown socket_type:", socket_type)


        # end __init__
    def dumps_json(self, data):
        '''
        
        Dumps a utf-8 encoded serial string
        
        '''

        return json.dumps(data).encode('utf-8')    

    
    def loads_json(self, data):
        ''' Converts a serial json utf-8 string into a python object
        '''
        #recv_dict_packet_info = json.loads(recv[1].decode('utf-8'))
        #recv_dict_data = json.loads(recv[2].decode('utf-8'))        
        return json.loads(data.decode('utf-8'))


    def dumps_ubjson(self, data):
        '''
        
        Dumps a utf-8 encoded serial string
        
        '''

        return ubjson.dumpb(data)

    
    def loads_ubjson(self, data):
        ''' Converts a serial ubjson package into a python object
        '''

        return ubjson.loadb(data)    
    

    def bind_socket(self, zmq_socket_type, address):
        """
        Binding the socket to a port

        Args:
            zmq_socket_type:
        
            address: Address or list of addresses for the binding, the first free address will be used
        """
        funcname = 'bind_socket()'
        if(not(isinstance(address,list))):
            address = [address]


        for addr in address:
            #self.logger.debug(funcname + ': Trying to bind to address:' + addr)
            try:
                self.logger.debug(funcname + ': Binding to address: ' + addr)
                # A socket to receive incoming requests about status etc.
                self.zmq_socket       = self.context.socket(zmq_socket_type)
                self.zmq_socket.bind(addr)
                self.zmq_socket_type = zmq_socket_type
                self.address = addr
                self.connected = True
                return True
            except Exception as e :
                #self.logger.debug(funcname + ': Exception:' + str(e))    
                #self.logger.debug(funcname + ': Couldnt bind zmq on address: ' + addr)
                self.connected = False

        self.logger.debug(funcname + ': Couldnt bind zmq to any address, failed ')
        return False

    
    def connect_socket(self,filter_uuid = ''):
        ''' Creating a socket and connecting it socket to a remote zmq socket with address of this zmq_socket

        '''
        funcname = 'connect_socket()'
        address = self.address
        zmq_socket_type = self.zmq_socket_type
        #self.logger.debug(funcname + ': Connecting to address: ' + str(address) + ' Type:' + str(zmq_socket_type))
        try:
            #self.logger.debug(funcname + ': Connecting to address: ' + str(address))
            # Lets create a socket
            self.zmq_socket       = self.context.socket(zmq_socket_type)
            if(zmq_socket_type == zmq.SUB):
                #self.logger.debug(funcname + ': Using filter_uuid: ' + filter_uuid)
                self.zmq_socket.setsockopt(zmq.SUBSCRIBE, filter_uuid.encode('utf-8')) # subscribe uuid

            # And connect it
            self.zmq_socket.connect(address)
            #self.zmq_socket.linger = 50
            #self.logger.debug(funcname + ': Connecting to address: ' + str(address) + ' done')
            self.connected = True
            return True
        except Exception as e :
            self.logger.warning(funcname + ': Exception:' + str(e))    
            self.logger.warning(funcname + ': Couldnt connect zmq to address: ' + str(address) + ' Type:' + str(zmq_socket_type))
            self.connected = False
            return False

        
    def get_connected_socket(self,filter_uuid = ''):
        """
        """
        funcname = 'get_connected_socket()'
        try:
            self.logger.debug(funcname + ': Connecting to address: ' + self.address)
            # A socket to receive incoming requests about status etc.
            socket       = self.context.socket(self.zmq_socket_type)
            if(self.zmq_socket_type == zmq.SUB):
                self.logger.debug(funcname + ': Using filter_uuid: ' + filter_uuid)
                socket.setsockopt(zmq.SUBSCRIBE, filter_uuid.encode('utf-8')) # subscribe uuid
                
            socket.connect(self.address)
            #self.zmq_socket.linger = 50
            self.logger.debug(funcname + ': Connecting to address: ' + self.address + ' done')
            self.connected = True
            return socket
        except Exception as e :
            self.logger.warning(funcname + ': Exception:' + str(e))    
            self.logger.warning(funcname + ': Couldnt connect zmq to address: ' + self.address)
            self.connected = False
            return None
    

    def reconnect_subsocket(self):
        """
        Reconnects to a disconnected socket
        """
        funcname = 'reconnect_subsocket()'
        try:
            if(self.connected == False):
                self.zmq_socket = self.get_connected_socket(filter_uuid = self.filter_uuid)
                self.start_poll_substream_thread()
            else:
                self.logger.warning(funcname + ': already connected')    
                
        except Exception as e :
            self.logger.warning(funcname + ': Exception:' + str(e))    
            self.logger.warning(funcname + ': Couldnt reconnect zmq to address: ' + self.address)
            self.connected = False
            return False


    def status_json(self):
        '''
        returns a json string of status
        '''
        status_dict = {'uuid':self.uuid,'address':self.address,'socket_type':self.socket_type}
        status_dict_json = json.dumps(status_dict).encode('utf-8')
        return status_dict_json

    
    def wait_for_request_and_reply(self, dt_wait = 0.05):
        """
        Here requests of a zmq.REQ socket will be processed
        answered NOTE: zmq sockets are not thread safe, the
        control_socket should not be used anywhere else except in this
        thread! TODO: Init control socket here!
        http://blog.pythonisito.com/2012/08/using-zeromq-devices-to-support-complex.html

        """
        
        funcname = 'wait_for_request_and_reply()'
        
        poller = zmq.Poller()
        poller.register(self.zmq_socket, zmq.POLLIN)
        
        while True:
            #self.logger.debug(funcname + ': process_reply_loop')
            if poller.poll(dt_wait*1000): #
                #recv = socket.recv_multipart()
                ubjson_request = self.zmq_socket.recv() # Waiting for a request (blocking)
                request = ubjson.loadb(ubjson_request)
                if(self.do_statistic):
                    self.statistic['packets_received'] += 1
                self.logger.debug(funcname + ': got request:')
                self.logger.debug(funcname + ':' + str(request))
                self.logger.debug(funcname + ': process_reply')
                reply = self.socket_reply_function(request)
                self.logger.debug(funcname + ': Replying')
                ubjson_reply = ubjson.dumpb(reply)
                self.zmq_socket.send(ubjson_reply)
                if(self.do_statistic):
                    self.statistic['packets_sent'] += 1
                self.logger.debug(funcname + ': done replying')
                
                
            else: # Try to read every dt_wait interval from the queue
                try:
                    # If we got something, just quit!
                    data = self.thread_queue.get(block=False)
                    #data = self.thread_queue.get()
                    self.logger.debug(funcname + ': Got data:' + data)
                    poller.unregister(self.zmq_socket)
                    self.connected = False
                    self.logger.debug(funcname + ': Closing')
                    break
                except queue.Empty as e:
                    #print(funcname + ' hallo ' + str(e))                    
                    pass
                except Exception as e:
                    logger.warning(funcname + ' ' +str(e))
            
        self.logger.debug(funcname + ': Stop replying now!')
        
        
    def process_client_request_bare(self,request):
        """
        Replying with nothing!
        """
        return ''.encode('utf-8')
    
    
    def start_poll_substream_thread(self):
        """ Starts a thread which is polling the substream socket for new data
        and puts it into the given deque

        """
        funcname = 'start_poll_substream_thread()'
        self.logger.debug(funcname)
        self.thread_queue = queue.Queue()
        socket = self.zmq_socket
        self.zmq_socket = None
        self.subpoll_thread = threading.Thread(target=self.poll_substream_thread,args = (socket,))
        self.subpoll_thread.daemon = True        
        self.subpoll_thread.start()

        
    def stop_poll_thread(self):
        """
        Stops a polling thread of either a substream or a reply (control) stream
        """
        funcname = 'stop_poll_thread()'
        self.logger.debug(funcname)
        if(self.thread_queue == None):
            self.logger.debug(funcname + ': No thread queue, doing nothing')
        else:
            if(self.socket_type == 'control'):
                self.logger.debug(funcname + ': Stopping control thread')
                self.thread_queue.put('stop')
                self.reply_thread.join()
                self.reply_thread = None
                self.thread_queue = None
            elif(self.socket_type == 'substream'):
                self.logger.debug(funcname + ': Stopping substream thread')
                self.stop_poll_substream_thread()


    def stop_poll_substream_thread(self):
        funcname = 'stop_poll_substream_tread()'
        if(self.thread_queue == None):
            self.logger.debug(funcname + ': No thread queue, doing nothing')
        else:
            if(True):
                self.logger.debug(funcname + ': Stopping, sending stop')
                self.thread_queue.put('stop')
                self.subpoll_thread.join()
                self.subpoll_thread = None
                self.thread_queue = None
                self.logger.debug(funcname + ': Stopped')
            else:
                self.logger.warning(funcname + ': No thread found to stop: ' + str(e))

            
    def poll_substream_thread(self, socket, dt_wait = 0.01):
        """The polling thread
            
        An infinite loop with a zmq.POLLIN and a timeout of dt_wait
        the timeout is used to check every dt_wait if data arrived on
        self.thread_queue, if something was receveied the thread is
        simply stopped. If data from the zmq socket was received the 
        ubjson data is decoded with self.loads and put into self.deque.
        TODO: Add time information of receive?
        
        Args: 
            dt_wait (float): Polling interval in seconds 
        
        """
        
        funcname = 'poll_substream_tread()'
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        while True:
            if poller.poll(dt_wait*1000): #
                recv = socket.recv_multipart()
                # Convert from json to dicts again with self.loads
                # This is discussable, but I leave it at the moment here
                #try:
                if(True):
                    #tirecv = datetime.datetime.strftime(datetime.datetime.utcnow(),'%Y%m%d%H%M%S%f')
                    tirecv = time.time()
                    recv_dict_uuid = recv[0].decode('utf-8')
                    recv_dict_packet_info = self.loads(recv[1])
                    recv_dict_data = self.loads(recv[2])
                    recv_dict = {}
                    recv_dict['uuid'] = recv_dict_uuid
                    recv_dict['info'] = {}
                    recv_dict['info']['n'] = recv_dict_packet_info[0]
                    recv_dict['info']['ts'] = recv_dict_packet_info[1]
                    recv_dict['info']['tr'] = tirecv
                    recv_dict['data'] = recv_dict_data
                    self.deque.appendleft(recv_dict)
                    if(self.do_statistic):
                        self.statistic['bytes_received'] += len(recv[0]) + len(recv[1]) + len(recv[2])
                        self.statistic['packets_received'] += 1
                #except Exception as e:
                #    self.logger.warning(funcname + ': Exception:' + str(e))
                    

            else: # Try to read every dt_wait interval from the queue
                try:
                    # If we got something, just quit!
                    data = self.thread_queue.get(block=False)
                    poller.unregister(socket)                    
                    self.logger.debug(funcname + ': Got data:' + data)
                    break
                    
                except queue.Empty:
                    pass
                except Exception as e:
                    self.logger.warning('Exception: ' + str(e))



        self.connected = False
        self.zmq_socket = socket
        self.logger.debug(funcname + ': Closed')        

        
    def start_pub_data_thread(self):
        """
        Starting a thread to publish data via the socket
        """
        self.pub_thread_queue = queue.Queue()
        socket = self.zmq_socket
        self.zmq_socket = None
        self.pub_data_thread = threading.Thread(target=self.pub_data_thread,args = (socket,))
        self.pub_data_thread.daemon = True        
        self.pub_data_thread.start()
        
        
    def pub_data_thread(self,socket):
        """
        """
        while(True):
            data = self.pub_thread_queue.get()
            if(data == None): # To quit the thread
                socket.close()
                return
            else:
                socket.send_multipart(data)
        
                
    def pub_data(self,data):

        """ Send data via a zmq.PUB socket. 

        Here data is serialised and put into a list of the form
        [ uuid_ser, packet_info_ser, data_ser]
        packet_info_ser = [n,tistr]: n: number of packets, tistr: utcstr

        Args:
            data: List of data [uuid, data to send ]

        """
        # Serialise data into a data stream
        #tistr = datetime.datetime.strftime(datetime.datetime.utcnow(),'%Y%m%d%H%M%S%f')
        tisend = time.time()
        self.packets += 1
        uuid_ser = data[0].encode('utf-8')
        data_ser = self.dumps(data[1])
        packet_info_ser = self.dumps([self.packets,tisend])
        # This is the data packet
        data_serial = [ uuid_ser, packet_info_ser, data_ser ]
        self.pub_thread_queue.put(data_serial)
        
                    
    def get_info(self):
        """
        returns a dictionary of socket information
        """
        info_dict = {}
        info_dict['uuid'] = self.uuid
        info_dict['address'] = self.address
        info_dict['socket_type'] = self.socket_type
        info_dict['connected'] = self.connected
        
        return info_dict


    def _send_req_(self,data):
        """
        Serialising data with ubjson (dumpb) via a request socket
        Args:
           data (ubjson serialisible python object): The data to be send
        """
        
        ubjson_data = ubjson.dumpb(data)
        self.zmq_socket.send(ubjson_data)

        
    def _get_rep_(self,dt_wait = 0.1):
        """Reads data from a req/rep socket using a poller which waits
        dt_wait seconds. Returned data is deserialised with ubjson 
        Args:
           dt_wait (float): wait time for the reply 
        Returns:
           [tpong,reply]: list with tpong, the time the packet was received and the reply message

        """
        poller = zmq.Poller()
        poller.register(self.zmq_socket, zmq.POLLIN)
        
        if poller.poll(dt_wait*1000): #
            tpong = time.time()
            ubjson_reply = self.zmq_socket.recv()
            reply = ubjson.loadb(ubjson_reply)
            poller.unregister(self.zmq_socket)
            return [tpong,reply]

        else:
            poller.unregister(self.zmq_socket)            
            return [None,None]

        
    def close(self):
        """
        Stopping threads and closing the sockets
        """
        funcname = 'close()'
        self.stop_poll_thread()
        #self.zmq_socket.close()
        
    
    def __str__(self):
        ret_str = self.__class__.__name__ + ';uuid:' + self.uuid +\
                  ';address:' + str(self.address) +\
                  ';connected:' + str(self.connected) +\
                  ';socket_type:' + self.socket_type

        return ret_str


#
#
#
#
#
#
# Stream 
# object
#
#
#
#
#
#


class Stream(object):
    """ A stream of data
    
    Args: 
       address:
       socket:
       variables:
       data_format:
       queuelen: The Stream has a deque object. This deque (collections.deque(maxlen=queuelen)) is filled with data from polled thread of the zmq_socket. The queuelen gives the maximum amount of received packets before data is overwritten. A -1 creates a not unlimited length queue.
       statistics:
       remote:
       name:
       family
       data_type:
       number: The number of the Stream, defaults to -1, will be set by the Parental Datastream object
       logging_level:
       logging_level_socket: The logging level of the zmq_socket, this can give a lot of information
    Returns:
       None
    """
    def __init__(self,stream_type, address = None, socket = None, variables = None, data_format = 'py_json', queuelen = 1000,statistic = False, remote = False, name = 'Stream', family = 'NA', data_type = 'continous', number = '-1', logging_level= 'INFO', logging_level_socket= 'INFO'):
        funcname = '__init__()'

        self.number = number
        # Create a uuid for streams 
        if( (remote == False) and \
            ( (stream_type == 'control') or \
              (stream_type == 'pubstream') or \
              (stream_type == 'repstream') \
            ) ):
            self.uuid = str(uuid_module.uuid1())
            self.uuid_utf8 = self.uuid.encode('utf-8')
            self.version = __datastream_version__
        else: # substreams, reqstreams do get the uuid from the counterparts
            self.uuid = ''
            self.version = '?'

        self.logger = logging.getLogger(self.__class__.__name__ + '(' + self.uuid + ')')
        self.logging_level = logging_level
        self.logging_level_socket = logging_level_socket

        if((logging_level == 'DEBUG') | (logging_level == logging.DEBUG)):
            self.logger.setLevel(logging.DEBUG)
        elif((logging_level == 'INFO') | (logging_level == logging.INFO)):
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.CRITICAL)

        self.logger.debug(funcname)
        
        self.remote = remote
        if(stream_type == 'control'):
            stream_type_short = 'ctrl'
        elif(stream_type == 'pubstream'):
            stream_type_short = 'pubs'
        elif(stream_type == 'substream'):
            stream_type_short = 'subs'            
        elif(stream_type == 'repstream'):
            stream_type_short = 'reps'
        else:
            stream_type_short = 'Stream'
            
            
        self.name = name
        self.family = family
        self.stream_type = stream_type
        self.socket = None
        self.variables = variables
        self.data_type = data_type
        self.data_format = data_format
        if(queuelen == -1):
            self.deque = collections.deque() # An empty collections data type
        else:
            self.deque = collections.deque(maxlen=queuelen) # An empty collections data type
        if(self.stream_type == 'pubstream'):
            self.socket = [] # A list of sockets the stream data is published to
            if(isinstance(socket,zmq_socket)):
                self.socket.append(socket)

        elif(self.stream_type == 'control'): # Control stream
            self.logger.debug(funcname + ': Creating control stream' )    
            self.socket = socket

        elif(self.stream_type == 'repstream'): # reply stream
            self.logger.debug(funcname + ': Creating repstream stream' )    
            self.socket = socket            

        # Do some statistic if wished
        self.do_statistic = False
        if(statistic):
            self.do_statistic = True
            self.statistic = {}
            self.statistic['packets_sent'] = 0
            self.statistic['packets_received'] = 0            
            
        
    def publish_stream(self,socket):
        """
        Publishes the stream to the socket uuid
        Args: 
            socket: zmq_socket object
        """
        funcname = '.publish_stream()'        
        if(self.stream_type == 'substream'):
            self.socket.append(socket)
            self.logger.debug(funcname + ': created socket')
        else:
            self.logger.debug(funcname + ': ' + self.uuid + ' no type not zmq.PUB')

            
    def push_substream_data(self):
        """

        Pops one dataset stored in Stream.deque and sends it via the
        published sockets
        NOT USED ANYMORE, REMOVED SOON, replaced by pub_data
        
        Args: None
        Returns: None
        """
        if True: 
            data = self.deque.pop()
            data = [self.uuid, data] # Add the uuid
            if(self.do_statistic):
                self.statistic['packets_sent'] += 1
            for socket in self.socket:
                socket.pub_data(data)


    def pub_data(self, data):
        """ Encodes and publishes the data together with the uuid of the stream as a list: [self.uuid,data]

        Args:
            data: Data

        """
        funcname = 'pub_data()'
        # Check if its only one dataset or many
        # TODO this has to be changed
        #if(len(data) == len(self.variables)):
        #    # put it into a list
        #    data = [data,]
        if(self.stream_type == 'pubstream'):
            if(self.do_statistic):
                self.statistic['packets_sent'] += 1
            for socket in self.socket:
                data = [self.uuid, data] # Add the uuid
                socket.pub_data(data)        

            return True
        else:
            raise Exception(funcname + ": wrong stream type") 

    def pop_data(self, n=1):
        """ Pops data from the deque which is received by the 
        :func:`pymqdatastream.zmq_socket.poll_substream_thread`.

        Args:
            n: Number of packets to return (-1 for all)

        Returns:
            data: A list of received packets

        Raises:
           Exception if stream_type is not 'substream'
        """
        funcname = 'pop_data()'
        if(self.stream_type == 'substream'):
            data = []
            ndata = len(self.deque)
            if(n > ndata):
                n = ndata
            if(n == -1):
                n = ndata

            while True:
                if(n > 0):
                    n -= 1
                else:
                    break

                rawdata_recv = self.deque.pop()
                if(self.do_statistic):
                    self.statistic['packets_received'] += 1

                data.append(rawdata_recv)

            return data
        else:
            raise Exception(funcname + ": wrong stream type, cannot pop data")


    def reqrep(self,request,dt_wait=0.05):
        """ Init a request->reply pattern if this stream is a reqstream, otherwise return an error

        Args:
           request: The request to be send
           dt_wait (float): wait in seconds for the reply datastream to answer

        Returns:
           The response data to the sent request together
           with the time the response was received from 
           the zmq_socket as a list of the form [time, reply]: 
           
        """
        funcname = 'reqrep()'
        if(self.stream_type == 'reqstream'):
            self.socket.send_req(request)
            reply = self.socket.get_rep(dt_wait) # This is with a poller, so it can block depending on dt_wait
            return reply
        else:
            raise Exception(funcname + ": wrong stream type, cannot request data")            
            
    
    def connect_stream(self,stream,ind_socket = 0,statistic = False):
        """
        
        Connects a stream by creating a "fitting" zmq_socket and connecting it to the remote socket.

        fitting socket means: 
           * stream.stream_type == 'pubstream', type = substream
           * stream.stream_type == 'repstream', type = reqstream
        
        Args: 
            stream: Stream to connect to
            ind_socket: [default = 0]
            statistic: bool [default = False]
        Returns:
            nothing
        """
        funcname = '.connect_stream()'
        # connect the stream sockets if it is a substream
        self.logger.debug(funcname)
        # check for correct stream type
        if(stream.stream_type == 'pubstream'):
            if(self.stream_type == 'substream'):
                if(len(stream.socket) > ind_socket):
                    self.logger.debug(funcname + ': Connecting substream at address' + str(stream.socket[0].address))
                    self.uuid      = stream.uuid
                    self.variables = stream.variables
                    self.name      = stream.name
                    self.family    = stream.family
                    self.socket    = zmq_socket(socket_type = self.stream_type,address = stream.socket[0].address,deque = self.deque,filter_uuid = stream.uuid,statistic = statistic, logging_level = self.logging_level_socket)
                else:
                    raise Exception(funcname + "no socket available for subscription")

            else:
                self.logger.warning(funcname + \
                                    ': cannot connect, stream type is not of type substream. Type connect stream:'\
                                    + str(stream.stream_type) + ', type self:' + str(self.stream_type))

        elif(stream.stream_type == 'repstream'):
            if(self.stream_type == 'reqstream'):
                if(True):
                    self.logger.debug(funcname + ': Connecting reqstream at address' + str(stream.socket.address))
                    self.uuid      = stream.uuid
                    self.variables = stream.variables
                    self.name      = stream.name
                    self.family    = stream.family                    
                    self.socket    = zmq_socket(socket_type = self.stream_type,address = stream.socket.address,deque = self.deque,filter_uuid = stream.uuid,statistic = statistic, logging_level = self.logging_level_socket)
            else:
                self.logger.warning(funcname + \
                                    ': cannot connect, stream type is not of type reqstream. Type connect stream:'\
                                    + str(stream.stream_type) + ', type self:' + str(self.stream_type))                
        else:
            raise Exception(funcname + " stream type to connect to is of unknown type")


    def reconnect_substream(self):
        """
        Reconnects a disconnected substream socket
        """
        funcname = self.__class__.__name__ + '.reconnect_substream()'
        self.logger.debug(funcname)
        self.socket.reconnect_subsocket()


    def disconnect(self):
        """
        Disconnects this stream 
        """            

        funcname = '.disconnect_substream()'
        if(self.stream_type == 'substream'):
            self.logger.debug(funcname + ': disconnecting substream')
            self.disconnect_substream()
        elif(self.stream_type == 'reqstream'):
            self.logger.debug(funcname + ': disconnecting reqstream')
            pass
        else:
            pass

        
    def disconnect_substream(self):
        """

        Disconnects this stream if it is a substream subscribed to a remote stream

        """
        funcname = '.disconnect_substream()'
        self.logger.debug(funcname)
        if(self.stream_type == 'substream'):
            self.logger.debug(funcname + ': disconnecting socket')
            self.socket.stop_poll_substream_thread()
            self.logger.debug(funcname + ': disconnecting socket done')


    def get_name(self):
        """

        Returns the name string
        
        """
        return self.name

    def get_family(self):
        """

        Returns the family string
        
        """
        return self.family    

            
    def get_info_dict(self):
        """ A dictionary of the stream info
        """

        info_dict = {}
        info_dict['uuid'] = self.uuid
        info_dict['number'] = self.number
        info_dict['name'] = self.name
        info_dict['family'] = self.family
        info_dict['stream_type'] = self.stream_type
        info_dict['variables'] = self.variables
        info_dict['data_type'] = self.data_type
        info_dict['data_format'] = self.data_format
        info_dict['version'] = self.version
        
        if(isinstance(self.socket,list)):
            info_dict['socket'] = []
            for i,socket in enumerate(self.socket):
                info_dict['socket'].append(socket.get_info())
        else:
            info_dict['socket'] = self.socket.get_info()
            
        return info_dict
    
    
    def get_info_str(self,info_type = 'all'):
        """
        Args:
        info_type: 'all','stream','socket', 'short'
        """
        ret_str = ''
        if(info_type == 'short'):
            if(not(isinstance(self.socket,list))):
                socket_tmp = [self.socket]
            else:
                socket_tmp = self.socket

            for i,socket in enumerate(socket_tmp):
                ret_str += str(i) + ' ' + self.name + ' (' + self.stream_type + ') ' + self.uuid + '::' + socket.address
                    

            return ret_str

        if(info_type == 'address'):
            if(not(isinstance(self.socket,list))):
                socket_tmp = [self.socket]
            else:
                socket_tmp = self.socket

            for i,socket in enumerate(socket_tmp):
                ret_str += self.uuid + '::' + socket.address
                    

            return ret_str
            
        if((info_type == 'all') | (info_type == 'stream') ):
            ret_str += self.__class__.__name__ + ' uuid:' + self.uuid +\
                      ';name:' + self.name + \
                      ';family:' + self.family + \
                      ';stream_type:' + self.stream_type + \
                      ';variables:' + str(self.variables) + \
                      ';data_type:' + str(self.data_type) + \
                      ';data_format:' + str(self.data_format)
            
        if((info_type == 'all') | (info_type == 'socket')):
            if(not(self.socket == None)):
                if(isinstance(self.socket,list)):
                    for i,socket in enumerate(self.socket):
                        ret_str += ';socket ' + str(i) + ':' + str(socket)
                else:
                    ret_str += ';socket:' + str(self.socket)

        return ret_str

    
    def __str__(self):
        return self.get_info_str('all')


def create_Stream_from_info_dict(info_dict, remote = True):
    """
    Creates a remote Stream object from info_dict
    Args:
        info_dict: Information dictionary of type created by Stream.get_info_dict()
    """
    stream = Stream(stream_type = info_dict['stream_type'], \
                    variables = info_dict['variables'], \
                    data_type = info_dict['data_type'], \
                    data_format = info_dict['data_format'], \
                    number = info_dict['number'], \
                    remote = remote, name = info_dict['name'])
    stream.uuid = info_dict['uuid']
    if(isinstance(info_dict['socket'],list)):
        stream.socket = []
        socket_dicts = info_dict['socket']
    else:
        socket_dicts = [info_dict['socket']]
        
    for i,socket_dict in enumerate(socket_dicts):
        socket = zmq_socket(socket_type = socket_dict['socket_type'], address = socket_dict['address'], remote = remote, connect = False)
        socket.uuid = socket_dict['uuid']
        if(isinstance(stream.socket,list)):
            stream.socket.append(socket)
        else:
            stream.socket = socket
            
    return stream





class StreamVariable(dict):
    """
    
    """
    def __init__(self,name='',unit='',datatype=''):
        super(StreamVariable, self).__init__()
        self.__setitem__('name',name)
        self.__setitem__('unit',unit)
        self.__setitem__('datatype',datatype)      



# Standard datastream ports

__num_ports__ = 200 # The total number of ports to be used
standard_datastream_control_port    = 18055 # First port number of the req/rep port for general information
standard_stream_publish_port        = 28719 # First port number for the general use ports
standard_datastream_address         = '127.0.0.1'
standard_datastream_control_address = 'tcp://' + standard_datastream_address

standard_datastream_control_ports = [ i for i in range(standard_datastream_control_port,\
                                                   standard_datastream_control_port +__num_ports__)]

standard_stream_publish_ports = [i for i in range(standard_stream_publish_port,\
                                                   standard_stream_publish_port +__num_ports__)]

standard_datastream_control_addresses = [ 'tcp://' + standard_datastream_address + ':' + str(i)\
                                          for i in range(standard_datastream_control_port,\
                                                         standard_datastream_control_port +__num_ports__)]

standard_datastream_publish_addresses = [ 'tcp://' + standard_datastream_address + ':' + str(i)\
                                          for i in range(standard_stream_publish_port,\
                                                         standard_stream_publish_port +__num_ports__)]


def treat_address(address=None,control=True):
    """
        Args: 
            address: string or list of address e.g. tcp://127.0.0.1
            control: Use addresses/ports dedicated to control stream (True) or to data stream (False)
        Returns:
            address_list: A list of addresses
    """
    funcname = 'treat_address'
    addresses_final = []
    # Check if we have control addresses/ports or data ports
    if(control):
        base_addresses = standard_datastream_control_addresses
        base_ports     = standard_datastream_control_ports
        base_port      = standard_datastream_control_port
    else:
        base_addresses = standard_datastream_publish_addresses
        base_ports     = standard_stream_publish_ports
        base_port      = standard_stream_publish_port

    has_base_address = False
    # Create standard addresses 
    if(address == None):
        logger.debug(funcname + \
        ': Taking standard address for control datastream: '\
        + str(base_addresses[0]) + ' ... ' 
        + str(base_addresses[-1]))
        addresses_final = base_addresses
    # Take address as given
    else:
        if(not(isinstance(address,list))): # A single address
            addresses = [address]
        else:
            addresses = address

        for address in addresses:
            if(address == None and has_base_address == False):
                logger.debug(funcname + \
                ': Taking standard address for control datastream: '\
                + str(base_addresses[0]) + ' ... ' 
                + str(base_addresses[-1]))                
                addresses_final = base_addresses
                has_base_address = True
                continue
                
            # Adding protocol if not existing
            # TODO: This essentially forbids to use anything but tcp
            if(not 'tcp://' in address):
                address = 'tcp://' + address
            if(address.count(':') == 2):
                logger.debug(funcname + ': Using address ' +
                                  address + ' for control stream')
                addresses_final.append(address)
            else:
                logger.debug(funcname + ': Using address ' +
                    address + ' and trying ports ' +
                    str(base_ports[0])
                    + ' ... ' +
                    str(base_ports[-1]) + 
                    ' for control stream')                        
                addresses = [ address + ':' + str(i)
                    for i in range(base_port,
                    base_port +__num_ports__)]
                addresses_final.extend(addresses)


    logger.debug('Adresses final: ' + str(addresses_final))
    return addresses_final


def get_ip_from_address(address):
    """
    Returns the IP as a string from an address string
    e.g. 127.1.0.0 from tcp://127.1.0.0:1234
    """
    address_ret = address
    address_ret = address_ret.replace('tcp://','')
    ind = address_ret.rfind(':')
    if(ind >= 0):
        address_ret = address_ret[0:ind]

    return address_ret


def check_stream_address_str(address):
    """
    Checks for a correct stream address in given string 
    Address looks like: e47bdacc-ae34-11e6-8b71-00247ee0ea87::tcp://127.0.0.1:28733@tcp://127.0.0.1:18055
    Args:
       address: string with the address of the stream
    Returns:
       bool: True for a valid address, otherwise False
    """
    try:
        address = address.rsplit('@')
        datastream_address = address[1]
        stream_uuid_address = address[0]
        [uuid,address] = stream_uuid_address.split('::')        
        return True
    except Exception as e:
        return False
    


#
#
#
#
#
#
# DataStream object
#
#
#
#
#
#



class DataStream(object):
    """
    
    The DataStream object

    
    Args:
       address: The address the control sockets is bound to default = None: Searches for the next free sockets on predefined ports
    
       remote: If False this is a local datastream object, if True its a remote datastream object with a reduced functionality (more of informative type)
    
       name: The name of the datastream [default='datastream']
    
       logging_level: The logging level of the logger object (logging.DEBUG, logging.INFO, logging.CRITICAL)

    """
    def __init__(self,address = None, remote = False, name = 'datastream',logging_level = 'INFO', logging_level_socket= 'INFO'):
        funcname = '.__init__()'
        # Init a logger
        self.logger = logging.getLogger(self.__class__.__name__ + '(' + name + ')')
        self.logging_level = logging_level
        self.logging_level_socket = logging_level_socket
        if((logging_level == 'DEBUG') | (logging_level == logging.DEBUG)):
            self.logger.setLevel(logging.DEBUG)
        elif((logging_level == 'INFO') | (logging_level == logging.INFO)):
            self.logger.setLevel(logging.INFO)            
        else:
            self.logger.setLevel(logging.CRITICAL)

        self.logger.debug(funcname)
        
        self.sockets = [] # A list of open sockets
        self.Streams = [] # A list of Streams
        self.num_streams = 0 # An ever increasing Stream number
        self.remote = remote
        self.name = name
        self.created = time.time()
        if(remote == False):
            self.uuid = 'pymqds_' + __datastream_version__ + '_DataStream' + ':' + str(uuid_module.uuid1())
            addresses = treat_address(address)



            # Create control socket
            control_socket = zmq_socket(socket_type = 'control', address = addresses, socket_reply_function = self.control_socket_reply,logging_level = self.logging_level_socket)
            self.address = control_socket.address
            self.ip = get_ip_from_address(self.address)
            self.sockets.append(control_socket)

            # Create control stream
            self.control_stream = Stream(name = 'Control Stream',stream_type = 'control', socket = control_socket, logging_level = self.logging_level,logging_level_socket = self.logging_level_socket,number=self.num_streams)
            self.num_streams += 1
            self.Streams.append(self.control_stream)


    def get_datastream_info(self,address,dt_wait = 0.1):
        """ Connecting to a remote datastream, querying the stream and disconnect afterwards

        """
        funcname = 'get_datastream_info()'
        try:
            socket = zmq_socket(socket_type = 'remote_control', address = address,logging_level = self.logging_level_socket)
        except Exception as e :
            self.logger.debug('Datastream.get_datastream_info(): Exception:' + str(e))
            return [False,None]

        # First ping the datastream object, to get a packet speed idea
        #self.logger.debug(funcname + ': ping')
        tping = time.time()
        request = {'ping':'','uuid':self.uuid,'tping':tping}
        socket.send_req(request)
        reply = socket.get_rep() # This is with a poller, so it can block depending on dt_wait
        if(reply[0] != None): # Got a reply
            tpong = reply[0]
            reply_data = reply[1]
            reply_dict = reply_data
            self.logger.debug(funcname + ':Got data: '+ str(reply))
        else:
            #self.logger.debug(funcname + ': Timeout processing auth request to REQ at: ' + address)
            return [False,None]

        # It worked lets calculate the delay
        dt = tpong - tping
        # This has to be done more carefully, it assumes that the
        # clocks are perfectly synchronized (which is valid on one
        # computer though!)
        dt_to = reply_dict['tpong'] - tping
        dt_back = tpong - reply_dict['tpong']
        self.logger.debug(funcname + ': Request trip times [s]: dt total: ' + str(dt) + ' dt to:' + str(dt_to) + ' dt back:' + str(dt_back))

        # Now get the datastream info
        self.logger.debug(funcname + ': get info')
        request = {'get':'info'}
        socket.send_req(request)
        reply = socket.get_rep() # This is with a poller, so it can block depending on dt_wait
        if(reply[0] != None): # Got a reply
            reply_dict = reply[1]
            self.logger.debug(funcname + ': Got data:' + str(reply_data))
        else:
            self.logger.debug(funcname + ': Timeout processing auth request to REQ at: ' + address)
            return [False,None]


        socket.close()
        return [True,reply_dict]

    
    def add_pub_socket(self,address = None):
        """
        Adds a zmq connector socket
        Args:
            address: An address string compatible with zeromq or a list of addresses pymqds will try to connect the socket to
        Return:
            socket or None if not successfull
        """
        funcname = '.add_pub_socket()'
        self.logger.debug(funcname)
        if(address == None): # If no address has been defined take the address of this datastream
            #address = standard_datastream_publish_addresses
            address = treat_address(self.ip,control=False)

        #self.logger.debug(funcname + ': ' + str(address))            
        pub_socket = zmq_socket(socket_type = 'pubstream',address = address,logging_level = self.logging_level)
        if(pub_socket != None):
            self.sockets.append(pub_socket)
            
        return pub_socket

        
    def add_pub_stream(self,socket, variables = None, name = None, family = 'NA', statistic = False):
        """ Adds a new stream
        
        Args:
            socket:
            variables:
            names:
            statistic:

        Returns:
            stream: stream which has been added or None if failed

        """
        if(socket.socket_type == 'pubstream'): # Check for correct socket type
            stream = Stream(stream_type = 'pubstream',socket = socket, variables = variables, name = name, family = family, statistic = statistic, logging_level = self.logging_level,logging_level_socket = self.logging_level_socket, number = self.num_streams)
            self.num_streams += 1
            self.Streams.append(stream)
            return stream
        else:
            raise Exception("wrong socket_type:",socket.socket_type, " it should be: pubstream")

        return None

    def create_pub_stream(self,address = None, variables = None, name = None, statistic = False):
        """
        Creates a new pubstream
        This function is a combination of
        self.add_pub_socket(address = address)
        and 
        self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables, statistic=statistic)        
        """
        
        self.add_pub_socket(address = address)
        self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables, statistic=statistic)


    def create_rep_stream(self, address = None, variables = None, name = 'rep', statistic = False, socket_reply_function = None):
        """ Creates a new reply stream

        Args:
            address:

        """
        funcname = 'create_rep_stream()'
        self.logger.debug(funcname)
        if(socket_reply_function == None):
            raise Exception("Need a reply function")
        
        if(address == None): # If no address has been defined
            address = standard_datastream_publish_addresses

        #self.logger.debug(funcname + ': ' + str(address))
        
        rep_socket = zmq_socket(socket_type = 'repstream',address = address, socket_reply_function = socket_reply_function, logging_level=self.logging_level_socket)
        self.sockets.append(rep_socket)

        stream = Stream(stream_type = 'repstream',socket = rep_socket, variables = variables, name = name, statistic = statistic, logging_level = self.logging_level,logging_level_socket = self.logging_level_socket, number=self.num_streams)
        
        self.num_streams += 1
        self.Streams.append(stream)
        
        return stream
        
    
    def add_stream(self,Stream):
        """ Adds a Stream to the datastream object

        """
        self.num_streams += 1        
        self.Streams.append(Stream)
        self.sockets.append(Stream.socket)

        
    def rem_stream(self,disstream):
        """

        Disconnects and removes a Stream
        Args:
            disstream: Stream to be removed
        Returns:
            bool: True: if Stream was succesfully removed, False if Stream could not be removed


        """
        funcname = 'rem_stream()'
        for i,stream in enumerate(self.Streams):
            if(stream == disstream):
                if(disstream.stream_type == 'substream'):                        
                    self.logger.debug(funcname + ': closing and removing substream stream')
                    stream.disconnect_substream()
                    self.Streams.pop(i)
                    return True
                elif(disstream.stream_type == 'pubstream'):
                    self.Streams.pop(i)
                    return True
                    

        return False


    def subscribe_stream(self,substream = None, statistic=False):
        """ Subscribes a stream of a remote datastream, this can be either a Stream object or a valid string. Valid address strings are a full address like: 8b3ccf7a-cc79-11e7-8307-aced5c604eba::tcp://127.0.0.1:28737@tcp://127.0.0.1:18055 or the string number of the datastream: e.g. 2@tcp://127.0.0.1:18055

        Args:
            substream: either a datastream.Stream object or a valid stream address to subscribe to, a valid address 
            statistic: do statistics of stream ( i.e. bytes received, packets received)
        Returns:
            stream: A stream object of the subscribed stream or None if subscription failed
        """
        funcname = 'subscribe_stream()'

        stream = None
        # Check if we have a stream object or a address
        if(isinstance(substream,Stream)):
            stream = substream
        elif(isinstance(substream,str)):
            address = substream
        else:
            self.logger.warning('Stream is not of type datastream.stream ' \
                             + ' neither a str address')
            return None
        
        if(stream != None):
            self.logger.debug(funcname + ': subscribing to stream:' + str(stream))
            if(stream.stream_type == 'pubstream'):
                self.logger.debug(funcname + ': created a substream for subscription')
                subscribe_stream = Stream('substream',statistic=statistic, number=self.num_streams)
            elif(stream.stream_type == 'repstream'):
                self.logger.debug(funcname + ': created a reqstream for subscription')
                subscribe_stream = Stream('reqstream',statistic=statistic, number=self.num_streams)
            else:
                raise Exception('Unknown stream type:' + str(stream.stream_type) + ', dont know how to subscribe ...')

            # Connect the stream
            ret = subscribe_stream.connect_stream(stream,statistic=statistic)
            if(subscribe_stream.socket != None): # When succesfully connected, socket is not None anymore
                if(subscribe_stream.socket.connected == True):
                    self.logger.debug(funcname + ': successfully subscribed stream:\n' + str(stream))
                    self.add_stream(subscribe_stream)
                    return subscribe_stream
                else:
                    self.logger.debug(funcname + ': failed to subscribe stream:\n' + str(stream))
                    return None
            else:
                self.logger.debug(funcname + ': failed to subscribe stream:\n' + str(stream))
                return None
            
            
        # If we have a address we have to create a remote datastream
        # object and a remote stream object first
        elif(address != None):
            self.logger.debug(funcname + ': subscribing to stream:' + str(address))
            address = address.rsplit('@')
            datastream_address = address[1]
            stream_address = address[0]
            [found_datastream,info_dict] = self.get_datastream_info(datastream_address)
            if(found_datastream):
                self.logger.info('Found a datastream at: ' + datastream_address)
                DSremote = create_datastream_from_info_dict(info_dict,logging_level = self.logging_level)
                # Check if the stream address is an address or a number
                if('::' in stream_address): # We have a probably valid stream address
                    stream = DSremote.get_stream_from_uuid(stream_address)                    
                else:
                    stream = DSremote.get_stream_from_number(int(stream_address))

                self.logger.debug(funcname + ':' + str(stream))
                ret = self.subscribe_stream(substream = stream)
                return ret
            else:
                self.logger.critical('Did not find a datastream at: ' + datastream_address)
                return None
            

    def control_socket_reply(self,request):
        """
        Replies to request of the control function
        """
        funcname = 'control_socket_reply()'
        self.logger.debug(funcname + ': Got request:' + str(request))
        
        # Check the type of request
        if 'ping' in request:
            tpong = time.time()
            uuid = request['uuid']
            self.logger.debug(funcname + ': got ping from uuid: ' + uuid)
            rep = {'pong':'','uuid':self.uuid,'tpong':tpong}
            return rep

        elif 'pong' in request:
            return ''

        elif 'connected' in request:
            con_address = request['connected']
            self.logger.debug(funcname + ': connected with: ' + con_address)
            #return ''.encode('utf-8')
            return ''

        elif 'pong' in request:
            #rep_json = json.dumps('').encode('utf-8')
            #return rep_json
            return ''


        elif 'get' in request:
            if 'info' in request['get']:
                info_dict = self.get_info()
                #rep_json = json.dumps(info_dict).encode('utf-8')
                #return rep_json
                return info_dict

        else:
            self.logger.debug(funcname + ': unknown request')
            
            
    def get_stream_from_uuid(self,uuid):
        """ 
        Returns a stream object for the given uuid/address string
        Args:
            uuid: uuid string
        Returns:
            Stream object or None if nothing was found
        """
        funcname = 'get_stream_from_uuid()'
        [pure_uuid,address] = uuid.rsplit('::')
        self.logger.info(funcname + ':' + str(pure_uuid) + ' ' + str(address))
        self.logger.debug(funcname + ':' + str(pure_uuid) + ' ' + str(address))
        for i,stream in enumerate(self.Streams):
            if(stream.uuid == pure_uuid):
                self.logger.debug(funcname + ': Found stream at: ' + str(uuid))
                return stream

            
        return None


    def get_stream_from_number(self,number):
        """  Returns a stream object for the given stream number
        Args:
            number: number
        Returns:
            Stream object or None if nothing was found
        """
        funcname = 'get_stream_from_number()'
        for i,stream in enumerate(self.Streams):
            if(stream.number == number):
                self.logger.debug(funcname + ': Found stream at: ' + str(number))
                return stream

            
        return None    
    
    
    def query_datastreams(self,addresses=None,queue=None):
        """
        Queries a list of addresses and returns datastream objects
        Input:
            addresses: List of addresses to query, if not defined standard addresses will be used
        Return:
            datastreams: A list of remote datastreams found
        """
        funcname = 'query_datastreams()'
        #self.logger.debug(funcname)
        list_status = []
        datastreams_remote = []
        addresses = treat_address(addresses)

        #self.logger.debug(funcname + ': Addresses' + str(addresses))

        for address in addresses:
            if(address != self.address):
                #self.logger.debug(funcname + ': Address:' + address)
                [ret,reply_dict] = self.get_datastream_info(address,dt_wait=0.01)
                #self.logger.setLevel(logging.DEBUG)                
                #self.logger.debug(funcname + ': Reply_dict:' + str(reply_dict))
                if(ret):
                    datastream_remote = create_datastream_from_info_dict(reply_dict)
                    try:
                        list_status.append(reply_dict)
                        datastreams_remote.append(datastream_remote)
                        self.logger.debug(funcname + ": Reply:" + str(datastream_remote))
                    except Exception as e :
                        #self.logger.debug(funcname + ": Exception:" + str(e))       
                        #self.logger.debug(funcname + ": Could not decode reply:" + str(reply_dict))
                        pass


        # If we have a queue put the result to the queue, this is for the threaded query
        if(not queue == None):
            queue.put(datastreams_remote)
            
        return datastreams_remote

    
    def query_datastreams_fast(self,addresses):
        """Querying datastreams by creating several threads trying to connect
        to the list of :param addresses: The function will create a
        temporary datastream for each address and will query the given
        ports of that address

        Args:
            addresses: String or list of addresses
        Returns:
            datastreams: The found datastreams

        """

        addresses_query = treat_address(addresses)
        threads = []
        datastreams_remote = []
        # Start a thread for every address
        for addr in addresses_query:
            q = queue.Queue()
            thread = threading.Thread(target=self.query_datastreams,args = (addr,q))
            thread.daemon = True
            threads.append([thread,q])
            thread.start()

        # Wait for return of all threads
        for t in threads:
            t[0].join()

        # 
        for t in threads:
            d = t[1].get()
            datastreams_remote.extend(d)


        return datastreams_remote
    
    def get_info(self):
        """
        """
        info_dict = {}
        info_dict['uuid'] = self.uuid
        info_dict['name'] = self.name
        info_dict['address'] = self.address
        info_dict['created'] = self.created
        info_dict['remote'] = self.remote
        #sockets = []
        #for i,sock in enumerate(self.sockets):
        #    sockets.append(sock.get_info())
        #                
        #info_dict['sockets'] = sockets
        streams = []
        for i,stream in enumerate(self.Streams):
            streams.append(stream.get_info_dict())
                        
        info_dict['Streams'] = streams
        return info_dict

    def get_name_str(self,strtype='simple'):
        """
        """
        if(strtype == 'simple'):
            if(self.name != 'datastream'):
                datastream_str = self.name + '@'
            else:
                datastream_str = ''

            datastream_str += self.address
            return datastream_str

        if(strtype == 'simple_newline'):
            if(self.name != 'datastream'):
                datastream_str = self.name + '\n'
            else:
                datastream_str = ''

            datastream_str += self.address
            return datastream_str        
        
                     
    def get_info_str(self,out_format='standard'):
        """
        Gets an info string og the object
        Args:
           out_format: 'standard' or 'short'
        """

        if(out_format == 'standard'):
            ret_str = self.__class__.__name__ + ';uuid:' + self.uuid
            ret_str += ';address: ' + str(self.address)
            ret_str += ';name: ' + str(self.name)
            ret_str += ';remote: ' + str(self.remote)
            ret_str += ';created: ' + str(self.created)
            ret_str += '\n;Streams: \n'
            for i,stream in enumerate(self.Streams):
                ret_str += '    ' +str(stream.number) + ':' + stream.get_info_str('stream')
                ret_str += '\n          ' + stream.get_info_str('socket')
                ret_str += '\n'
            
            return ret_str

        if(out_format == 'short'):
            ret_str = self.uuid + '@' + str(self.address)
            ret_str += '\nStreams:\n'
            for i,stream in enumerate(self.Streams):
                ret_str += self.get_stream_address(stream,more_info=True)

                if(stream.do_statistic):
                    ret_str += 'Packets sent: ' + str(stream.statistic['packets sent'])

            ret_str += '\n\n'  
            return ret_str
        
        
    def get_stream_address(self,stream,more_info=False):
        """
        Gets an address string of the stream
        Args:
           stream: either a Stream object or an int of the stream number
           more_info: Adding more information (Stream number, name and family)
        Returns:
           Address string with some additional information of the stream
        """

        # If stream is an integer
        if(isinstance(stream, int)):
            stream = self.Streams[stream]
            
        if(more_info):
            ret_str = ''
            for i,tstream in enumerate(self.Streams):
                if(tstream == stream):
                    ret_str += '#' + str(i) + ' Name: "' + str(stream.name) + '"'\
                               + ', Family: "' + str(stream.family) + '"'\
                               + ', Address:"' + stream.get_info_str('address') + '@'\
                               + str(self.address) + '"\n'
        else:
            ret_str = stream.get_info_str('address') + '@' + str(self.address)

        return ret_str
        
            
    def __str__(self):
        return self.get_info_str()

    def close(self):
        """
        Cleanup and close of all stuff
        """
        funcname = 'close()'
        self.logger.debug(funcname)
        #self.sockets[0].stop_poll_thread()
        #self.sockets[0].zmq_socket.close()
        #self.sockets[1].stop_poll_thread()
        #self.sockets[1].zmq_socket.close()
        ## remove streams
        for stream in self.Streams:
            self.rem_stream(stream)                    
        # closing all sockets
        for sock in self.sockets:
            self.logger.debug(funcname + ' closing thread of ' + str(sock))
            sock.stop_poll_thread()
            sock.close()


            
            



def create_datastream_from_info_dict(info_dict,logging_level = logging.INFO):
    """ Populates a datastream object from info_dict
    
    """
    # Only populating if the datastream is of remote type
    datastream = DataStream(remote = True,name=info_dict['name'] + '_remote',logging_level = logging_level)
    datastream.uuid = info_dict['uuid']
    datastream.created = info_dict['created']
    try:
        datastream.address = info_dict['address']
    except:
        pass

    for i,stream_dict in enumerate(info_dict['Streams']):            
        stream = create_Stream_from_info_dict(stream_dict)
        datastream.Streams.append(stream)

    return datastream






    

        


if __name__ == '__main__':
    print('Main function')
    D = DataStream(address = 'tcp://127.0.0.1:21001')
    E = DataStream(address = 'tcp://127.0.0.1:21002') 
    print('Adding a pub stream:')
    D.get_datastream_info(address = 'tcp://127.0.0.1:21002')
    D.add_pub_socket()
    D.add_pub_stream(socket = D.sockets[-1],name='random',variables=['count','data'])
    #D.Streams[-1].publish_stream(D.sockets[-1])
    print('__main__: Got info:')
    info_dict = D.get_info()
    F = create_datastream_from_info_dict(info_dict)
    print('__main__: Datastream:')
    print(F)
    S = Stream('substream')
    S.connect_substream(D.Streams[1])
    D.Streams[-1].deque.appendleft('HALLO'.encode('utf-8'))
    D.Streams[-1].push_substream_data()
    D.Streams[-1].deque.appendleft('BALLO'.encode('utf-8'))
    D.Streams[-1].push_substream_data()    
    time.sleep(0.1)    
    print(S.deque)
    time.sleep(0.1)
    S.disconnect_substream()
    
    #print(a.status_json())
    
