#!/usr/bin/env python3
import sys
import os
import logging
try:
    import queue as queue # python 3
except:
    import Queue as queue # python 2.7
import threading
import serial
import socket
import datetime
import pytz
import collections
import time
import numpy as np
import argparse
import pynmea2
try:
    import pymqdatastream
except ImportError:
    print('Could not import pymqdatastream, this is not dramatic but some fuctionality is missing (network publishing)')
    pymqdatastream = None

logger = logging.getLogger('pymqds_nmea0183logger.py')
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


    


# TODO: This should be somewhere else
def parse(msg):
    """
    Function to parse a nmeadataset
    Input:
       msg: NMEA data str
    """
    ind = msg.find('$')
    #print(msg[ind:])
    # There is data before, lets test if its some sort of date/device string
    if(ind > 0):
        pass
    
    try:
        data = pynmea2.parse(msg[ind:])
        #
        return data


    except ValueError:
        print('Could not parse data: ' + str(msg))
        return None


def sort_parsed_data_in_dict(data,data_dict):
    """
    Sorts data parsed with pynmea2 into a dictionary
    """
    
    #data_dict['time'] = None
    data_dict['timestamp'] = None
    if(not(data == None)):
        if('GGA' in data.identifier()):
            data_dict['id'] = 'GGA'
            if(not(data.timestamp == None)):
                data_dict['time'] = data.timestamp
            if(len(data.lat) > 0):
                data_dict['lat'] = data.lat
            if(len(data.lon) > 0):
                data_dict['lon'] = data.lon
            if(len(data.num_sats) > 0):
                data_dict['num_sat'] = data.num_sats
            if(len(data.horizontal_dil) > 0):
                data_dict['horizontal_dil'] = data.horizontal_dil
                
        elif('RMC' in data.identifier()):
            data_dict['id'] = 'RMC'
            print(type(data.datestamp),type(data.timestamp))
            #https://stackoverflow.com/questions/7065164/how-to-make-an-unaware-datetime-timezone-aware-in-python
            data_dict['datetime'] = data.datetime.replace(tzinfo=pytz.UTC)
            #datetime.datetime.combine(data.datestamp,data.timestamp)
            data_dict['timestamp'] = datetime.datetime.timestamp(data_dict['datetime'])
            
    

class nmea0183logger(object):
    """A flexibel class for interfacing and distributing several
    different NMEA streams like serial, tcp or datastreams The main
    part of the object is the serial list. This list contains
    dictionaries with open devices, may them be serial, tcp or
    datastream objects.

    """
    def __init__(self,loglevel=logging.INFO,print_raw_data=False):
        """
        """
        funcname =  '__init__()'
        loglevel = logging.DEBUG
        self.logger = logging.getLogger(self.__class__.__name__ + 'fdsfds')
        self.logger.setLevel(loglevel)
        self.loglevel = loglevel
        self.logger.debug(funcname)                    
        self.dequelen          = 10000
        self.serial            = []
        self.serial_number     = 0 # An increasing number used to identify a device
        self.datafiles         = []        
        self.deques            = []
        self.signal_functions  = [] # Functions that are called at different actions
        self.pymqdatastream    = None
        self.pymqdatastream_pub= None # pymqdatastream for publishing
                                      # the data, TODO this could be a
                                      # list with several datastream
                                      # having different addresses
        self.name             = 'nmea0183logger' # This is mainly used as a datastream identifier
        self.print_raw_data = print_raw_data

        
    def add_serial_device(self,port,baud=4800):
        """
        """
        funcname = 'add_serial_device()'
        try:
            self.logger.debug(funcname + ': Opening: ' + port)            
            serial_dict = {}
            serial_dict['number']         = self.serial_number
            self.serial_number += 1
            serial_dict['sentences_read'] = 0
            serial_dict['bytes_read']     = 0
            serial_dict['device_name']    = port            
            serial_dict['port']           = port
            serial_dict['device']         = serial.Serial(port,baud)
            serial_dict['thread_queue']   = queue.Queue()
            serial_dict['parsed_data']    = {} # Dict of parsed data
            serial_dict['data_queues']    = []
            serial_dict['data_signals']   = []
            serial_dict['streams']        = [] # pymqdatastream Streams
            serial_dict['thread']         = threading.Thread(target=self.read_nmea_sentences_serial,args = (serial_dict,))
            serial_dict['thread'].daemon = True
            serial_dict['thread'].start()
            self.serial.append(serial_dict)
            if(self.pymqdatastream_pub != None):
                self.add_stream(serial_dict)
                

            # Call the signal functions
            for s in self.signal_functions:
                s(funcname)
                
            return True
        except Exception as e:
            self.logger.debug(funcname + ': Exception: ' + str(e))            
            self.logger.debug(funcname + ': Could not open device at: ' + str(port))
            return False


    def read_nmea_sentences_serial(self, serial_dict):
        """
        The polling thread
        input:
            serial_dict: 
            thread_queue: For stopping the thread
        """
        
        funcname = 'read_nmea_sentences()'
        serial_device = serial_dict['device']
        thread_queue = serial_dict['thread_queue']
        nmea_sentence = ''
        got_dollar = False                            
        while True:
            time.sleep(0.02)
            while(serial_device.inWaiting()):
                # TODO, this could be made much faster ... 
                try:
                    value = serial_device.read(1).decode('utf-8')
                    nmea_sentence += value
                    serial_dict['bytes_read'] += 1
                    if(value == '$'):
                        got_dollar = True
                        # Get the time
                        ti = time.time()

                    elif((value == '\n') and (got_dollar)):
                        got_dollar = False                    
                        nmea_data = {}
                        nmea_data['time'] = ti
                        nmea_data['device'] = serial_device.name
                        nmea_data['nmea'] = nmea_sentence
                        
                        if(self.print_raw_data):
                            write_str = ''
                            write_str += nmea_data['device'] + ' ' 
                            time_str = datetime.datetime.fromtimestamp(nmea_data['time']).strftime('%Y-%m-%d %H:%M:%S')
                            write_str +=  time_str + ' '
                            write_str += nmea_data['nmea']
                            print(write_str)
                            
                        for deque in self.deques:
                            deque.appendleft(nmea_data)

                        # Send into specialised data queues as e.g. for the gui
                        for deque in serial_dict['data_queues']:
                            deque.appendleft(nmea_data)

                        # Send into pymqdatastream streams
                        for stream in serial_dict['streams']:
                            stream.pub_data([[ti,nmea_sentence]])

                        # Parse the data
                        parsed_data = parse(nmea_sentence)
                        sort_parsed_data_in_dict(parsed_data,serial_dict['parsed_data'])
                        
                        # TODO 

                        # Call signal functions for new data
                        for s in serial_dict['data_signals']:
                            s()
                            
                        nmea_sentence = ''
                        serial_dict['sentences_read'] += 1

                except Exception as e:
                    self.logger.debug(funcname + ':Exception:' + str(e))

                    
            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                break
            except queue.Empty:
                pass

        
        return True


    def add_tcp_stream(self,address,port):
        """
        Returns:
        bool: True if successful, False otherwise
        """
        funcname = 'add_tcp_stream()'
        # Create a TCP/IP socket

        try:
            self.logger.debug(funcname + ': Opening TCP socket: ' + address + ' ' + str(port))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((address, port))
            sock.setblocking(0) # Nonblocking
            serial_dict = {}
            serial_dict['number']         = self.serial_number
            self.serial_number += 1            
            serial_dict['sentences_read'] = 0
            serial_dict['bytes_read'] = 0            
            serial_dict['device']         = sock
            serial_dict['address']        = address
            serial_dict['port']           = port
            serial_dict['device_name']    = address + ':' + str(port)
            serial_dict['parsed_data']    = {} # Dict of parsed data
            serial_dict['time_info']      = {} # Dict of information about the time, difference to the local clock and jitter
            serial_dict['time_info']['dt_mean']     = np.NaN
            serial_dict['time_info']['dt_std']      = np.NaN            
            serial_dict['time_info']['ind']         = 0
            serial_dict['time_info']['len_t_array'] = 100
            serial_dict['time_info']['data']        = np.zeros((serial_dict['time_info']['len_t_array'],2))            
            serial_dict['data_queues']    = []
            serial_dict['data_signals']   = []            
            serial_dict['streams']        = [] # pymqdatastream Streams
            serial_dict['thread_queue']   = queue.Queue()
            serial_dict['thread']         = threading.Thread(target=self.read_nmea_sentences_tcp,args = (serial_dict,))
            serial_dict['thread'].daemon  = True
            serial_dict['thread'].start()
            if(self.pymqdatastream_pub != None):
                self.add_stream(serial_dict)
                
            self.serial.append(serial_dict)
            # Call the signal functions
            for s in self.signal_functions:
                s(funcname)


            return True
        except Exception as e:
            self.logger.debug(funcname + ': Exception: ' + str(e))
            return False


    def read_nmea_sentences_tcp(self, serial_dict):
        """
        The tcp polling thread
        Args:
            serial_device: 

        """
        
        funcname = 'read_nmea_sentences_tcp()'
        serial_device = serial_dict['device']
        thread_queue = serial_dict['thread_queue']
        nmea_sentence = ''
        raw_data = ''
        got_dollar = False                   
        while True:
            time.sleep(0.05)
            try:
                data,address = serial_dict['device'].recvfrom(10000)
                #print('data',data)
            except socket.error:
                pass
            else:
                #print("recv:", data,"times",len(data), 'address',address)
                serial_dict['bytes_read'] += len(data)
                raw_data += raw_data + data.decode('utf-8')

                for i,value in enumerate(raw_data):
                    nmea_sentence += value
                    if(value == '$'):
                        got_dollar = True
                        # Get the time
                        ti = time.time()

                    elif((value == '\n') and (got_dollar)):
                        got_dollar = False                    
                        nmea_data = {}
                        nmea_data['time'] = ti
                        nmea_data['device'] = serial_dict['address'] + ':' + str(serial_dict['port'])
                        nmea_data['nmea'] = nmea_sentence
                        #self.logger.debug(funcname + ':Read sentence:' + nmea_sentence)
                        for deque in self.deques:
                            deque.appendleft(nmea_data)
                            

                        serial_dict['sentences_read'] += 1
                        raw_data = raw_data[i+1:]


                        if(self.print_raw_data):
                            write_str = ''
                            write_str += nmea_data['device'] + ' ' 
                            time_str = datetime.datetime.fromtimestamp(nmea_data['time']).strftime('%Y-%m-%d %H:%M:%S')
                            write_str +=  time_str + ' '
                            write_str += nmea_data['nmea']
                            print(write_str)
                            
                        for deque in self.deques:
                            deque.appendleft(nmea_data)

                        # Send into specialised data queues as e.g. for the gui
                        for deque in serial_dict['data_queues']:
                            deque.appendleft(nmea_data)

                        # Send into pymqdatastream streams
                        for stream in serial_dict['streams']:
                            stream.pub_data([[ti,nmea_sentence]])


                        # Parse the data
                        parsed_data = parse(nmea_sentence)
                        sort_parsed_data_in_dict(parsed_data,serial_dict['parsed_data'])

                        # Make statistics of time difference between nmea and local clock
                        if(serial_dict['parsed_data']['timestamp'] is not None):
                            print(serial_dict['parsed_data']['id'])
                            print(serial_dict['parsed_data']['datetime'])
                            print('Time:' + str(serial_dict['parsed_data']['timestamp']) + ' ' +  str(ti))
                            dt = serial_dict['parsed_data']['timestamp'] - ti
                            ind_tmp = serial_dict['time_info']['ind']
                            if(ind_tmp < serial_dict['time_info']['len_t_array']):
                                pass
                            else:
                                serial_dict['time_info']['ind'] = 0

                            serial_dict['time_info']['ind'] += 1
                            serial_dict['time_info']['data'][ind_tmp,0] = ti
                            serial_dict['time_info']['data'][ind_tmp,1] = serial_dict['parsed_data']['timestamp']                            
                            ind_tmp += 1
                            serial_dict['time_info']['dt_mean'] = np.mean(np.diff(serial_dict['time_info']['data'][0:ind_tmp,:],1))
                            serial_dict['time_info']['dt_std'] = np.std(np.diff(serial_dict['time_info']['data'][0:ind_tmp,:],1))                            

                            if(ind_tmp > 0):
                                print('diff:' + str(dt))
                                print(datetime.datetime.utcfromtimestamp(ti))
                                print(np.diff(serial_dict['time_info']['data'][0:ind_tmp,:],1))
                                print(serial_dict['time_info']['dt_mean'])
                                print(serial_dict['time_info']['dt_std'])
                                #serial_dict['time_info']


                        # Call signal functions for new data
                        for s in serial_dict['data_signals']:
                            s()

                        nmea_sentence = ''

            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                break
            except queue.Empty:
                pass
                    
        return True



    def add_datastream(self,address=None):
        """Adds a nmea0183 a remote logger datastream

        """
        funcname = 'add_datastream()'
        self.logger.debug(funcname)
        # Create a pymqdatastream if neccessary
        if(self.pymqdatastream == None):
            self.create_pymqdatastream()

        # Query remote datastreams
        self.logger.debug(funcname + ': querying')
        remote_datastreams = self.pymqdatastream.query_datastreams(address)
        self.logger.debug(funcname + ':' + str(remote_datastreams))
        for s in remote_datastreams:
            print(s.name)
            if(self.name in s.name): # Do we have a nmealogger?
                print('Found a logger!')
                print(s)
                for stream in s.Streams:
                    self.add_pymqdsStream(stream)



    def add_pymqdsStream(self,stream):
        funcname = 'add_pymqdsStream()'        
        if('nmea' in stream.name):
            if(stream.stream_type == 'pubstream'): # Do we have to subscribe?
                self.logger.debug(funcname + ': Found nmea stream, will subscribe')
                recvstream = self.pymqdatastream.subscribe_stream(stream,statistic=True)
            elif(stream.stream_type == 'substream'): # Already subscribed
                self.logger.debug(funcname + ': Found an already subscribed nmea stream')
                recvstream = stream
            else:
                self.logger.warning(funcname + ': Dont know what to do with stream:' + str(stream))
            serial_dict = {}
            serial_dict['number']         = self.serial_number
            self.serial_number += 1            
            serial_dict['sentences_read'] = 0
            serial_dict['bytes_read']     = 0
            serial_dict['device_name']    = recvstream.name
            serial_dict['address']        = recvstream.socket.address
            serial_dict['port']           = ''
            serial_dict['device']         = recvstream
            serial_dict['thread_queue']   = queue.Queue()
            serial_dict['parsed_data']    = {} # Dict of parsed data            
            serial_dict['data_queues']    = []
            serial_dict['data_signals']   = []
            serial_dict['streams']        = [] # pymqdatastream publication streams
            serial_dict['thread']         = threading.Thread(target=self.read_nmea_sentences_datastream,args = (serial_dict,))
            serial_dict['thread'].daemon  = True
            serial_dict['thread'].start()
            self.serial.append(serial_dict)
            # Call the signal functions
            for s in self.signal_functions:
                s(funcname)                                
        else:
            self.logger.info(funcname + 'given stream is not a nmea stream')


    def read_nmea_sentences_datastream(self,serial_dict):
        """
        The datastream polling thread
        Args:
            serial_dict: 
        """
        thread_queue = serial_dict['thread_queue']
        recvstream = serial_dict['device']
        while True:
            time.sleep(0.02)
            ndata = len(recvstream.deque)
            if(ndata > 0):
                data = serial_dict['device'].pop_data(n=1)
                for d in data:
                    print('Data received',data)
                    #bytes_recv = 0
                    bytes_recv = serial_dict['device'].socket.statistic['bytes_received']
                    serial_dict['bytes_read'] = bytes_recv                    
                    nmea_data = {}
                    nmea_data['time'] = d['data'][0][0]
                    nmea_data['device'] = serial_dict['address'] + '/' + serial_dict['device_name']
                    nmea_data['nmea'] =  d['data'][0][1]

                    for deque in self.deques:
                        deque.appendleft(nmea_data)

                    # Send into specialised data queues as e.g. for the gui
                    for deque in serial_dict['data_queues']:
                        deque.appendleft(nmea_data)

                    # Send into pymqdatastream streams
                    for stream in serial_dict['streams']:
                        stream.pub_data([[ti,nmea_sentence]])

                    # Call signal functions for new data
                    for s in serial_dict['data_signals']:
                        s()

                    serial_dict['sentences_read'] += 1                      
                
                
            # Try to read from the queue, if something was read, quit
            # the thread
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                break
            except queue.Empty:
                pass                
            
            
    def add_file_to_save(self,filename, style = 'all'):
        """
        Adds a file to save the data to
        """
        
        funcname = 'add_file_to_save()'
        
        try:
            datafile_dict = {}
            datafile_dict['datafile'] = open(filename,'w')
            datafile_dict['thread_queue'] = queue.Queue()        
            self.deques.append(collections.deque(maxlen=self.dequelen))
            datafile_dict['file_thread'] = \
                        threading.Thread(target=self.save_nmea_sentences,\
                        args = (datafile_dict['datafile'],self.deques[-1],\
                                datafile_dict['thread_queue'],style))
            datafile_dict['file_thread'].daemon = True
            datafile_dict['file_thread'].start()
            self.datafiles.append(datafile_dict)
            self.logger.debug(funcname + ': opened file: ' + filename)
            return datafile_dict['datafile']
        except Exception as e:
            self.logger.warning(funcname + ': Exception: ' + str(e))
            return None

            
    def close_file_to_save(self,datafile):
        """
        Closes the thread and the file to save data to
        input: 
            datafile: can be either an integer or a file object 
        """
        funcname = 'close_file_to_save()'
        if(isinstance(datafile,int)):
            ind_datafile = datafile
            self.logger.debug(funcname + ': got ind, thats easy' )
            found_file = True
        else:
            self.logger.debug(funcname + ': File object, searching for the file' )
            found_file = False
            for ind_datafile,dfile in enumerate(self.datafiles):
                if(dfile['datafile'] == datafile):
                    self.logger.debug(funcname + ': Found file object at index:' + str(ind_datafile))
                    found_file = True
                    break

        if(found_file):
            # Closing thread by sending something to it
            self.datafiles[ind_datafile]['thread_queue'].put('stop')
            # Waiting for closing
            time.sleep(0.05)
        else:
            self.logger.warning(funcname + ': Could not close file: '+str(datafile) )
            print(self.datafiles)
            

    def save_nmea_sentences(self,datafile, deque, thread_queue, style):
        """
        Saves the nmea into a file
        """
        funcname = 'save_nmea_sentences()'
        ct = 0
        dt = 0.05
        while True:
            time.sleep(dt)
            ct += dt
            while(len(deque)):
                data = deque.pop()
                write_str = ''
                if(style == 'all'):
                    write_str += data['device'] + ' ' 
                    time_str = datetime.datetime.fromtimestamp(data['time']).strftime('%Y-%m-%d %H:%M:%S')
                    write_str +=  time_str + ' '
                    write_str += data['nmea']

                elif(style == 'raw'):
                    write_str += data['nmea']

                datafile.write(write_str)                    
            if(ct >= 10): # Sync the file every now and then and show some information
                ct = 0
                self.logger.debug(funcname + ': flushing')
                datafile.flush()                
                info_str = self.serial_info()
                self.logger.info(funcname + ':' + info_str)

            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                datafile.close()
                break
            except queue.Empty:
                pass
            
            
    def serial_info(self):
        """
        Creates an information string of the serial devices, the bytes and NMEA sentences read 
        Returns:
           info_str
        """
        info_str = ''
        for s in self.serial:
            info_str += s['port'] + ' ' + str(s['bytes_read']) + ' bytes '
            info_str += str(s['sentences_read']) + ' NMEA sentences' + '\n'

        return info_str
    
    
    def log_data_in_files(self, filename, time_interval):
        """
        Creates every time_interval a new file and logs the data to it
        input:
        filename: 
        time_interval: datetime.timedelta object, default: datetime.timedelta(hours=1)
        """
        funcname = 'log_data_in_files()'
        self.logger.debug(funcname)
        thread_queue = queue.Queue()
        # If time interval is larger than 10 seconds, create with time interval new files, otherwise only one file
        if(time_interval > datetime.timedelta(seconds=9.9999)):
            self.logger.debug(funcname + ': Starting thread to create every ' +str(time_interval) + ' a new file')
            self.time_thread = threading.Thread(target=self.time_interval_thread, args = (filename,time_interval,thread_queue))
            self.time_thread.daemon = True
            self.time_thread.start()
        else:
            self.logger.debug(funcname + ': Creating file and logging data to ' + filename)            
            datafile = self.add_file_to_save(filename)
            
            
    def time_interval_thread(self,filename,time_interval,thread_queue):
        """

        

        """
        funcname = 'time_interval_thread()'
        dt = .1
        self.logger.debug(funcname)
        now = datetime.datetime.now()
        filename_time = now.strftime(filename + '__%Y%m%d_%H%M%S.log')
        datafile = self.add_file_to_save(filename_time)
        tstart = now
        
        while True:
            time.sleep(dt)            
            now = datetime.datetime.now()
            if((now - tstart) > time_interval):
                self.logger.debug(funcname + ': Time interval thread:' + str(now) +' ' + str(tstart) + ' ' + str(time_interval))
                tstart = now
                self.logger.debug(funcname + ': Creating new file')
                self.close_file_to_save(datafile)
                time.sleep(0.01)
                filename_time = now.strftime(filename + '__%Y%m%d_%H%M%S.log')
                datafile = self.add_file_to_save(filename_time)
                time.sleep(0.01)                
                
            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                datafile.close()
                break
            except queue.Empty:
                pass
            
            
    def create_pymqdatastream(self, address=None):
        """Creates pymqdatastream to stream the read data and to comminucate
        with a remote logger object
        Input:
           address: The address of the datastream, default; pymqdatastream will take care
        """
        funcname = 'create_pymqdatastream()'
        # Import pymqdatastream here
        self.logger.debug(funcname + ': Creating DataStream')
        #self.loglevel = logging.DEBUG
        if(self.pymqdatastream is None):
            datastream = pymqdatastream.DataStream(address=address, name=self.name,logging_level=self.loglevel)
            self.pymqdatastream = datastream
        else:
            self.logger.debug(funcname + ': DataStream is already existing, doing nothing ...')


    def create_pymqdatastream_publish(self, address=None):
        """Creates pymqdatastream to stream the publish the data, this is
        separated from the read pymqdatastream, as it allows to
        publish with several addresses

        Input: address: The address of
        the datastream, default; pymqdatastream will take care

        """
        funcname = 'create_pymqdatastream()'
        # Import pymqdatastream here
        self.logger.debug(funcname + ': Creating DataStream')
        #self.loglevel = logging.DEBUG
        if(self.pymqdatastream_pub is None):
            datastream = pymqdatastream.DataStream(address=address, name=self.name,logging_level=self.loglevel)
            self.pymqdatastream_pub = datastream
        else:
            self.logger.debug(funcname + ': DataStream is already existing, doing nothing ...')            
            
            
    def add_stream(self,serial):
        """
        Adds a pymqdatastream Stream for a serial device.
        Input:
           serial: The serial device to be transmitted
        """
        funcname = 'add_stream()'
        self.logger.debug(funcname)
        datastream = self.pymqdatastream_pub
        # Create variables
        timevar = pymqdatastream.StreamVariable(name = 'unix time',\
                                                unit = 'seconds',\
                                                datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'NMEA data',\
                                                datatype = 'str',\
                                                unit = 'NMEA')
        variables = [timevar,datavar]
        name = 'nmea;' + serial['device_name']
        # Adding publisher sockets and add variables
        pub_socket = datastream.add_pub_socket()
        
        sendstream =  datastream.add_pub_stream(
            socket = pub_socket,
            name   = name,variables = variables)

        #print('Hallo',serial)        
        serial['streams'].append(sendstream)


    def publish_devices(self):
        """
        Publishes all devices as pymqdatastreams
        """
        funcname = 'publish_devices()'
        self.logger.debug(funcname)
        for s in self.serial:
            self.logger.debug(funcname + ': Adding stream for' + str(s))
            print('Stream:',s)
            self.add_stream(s)
            
            
    def rem_serial_device(self,index = None, number = None):
        """Removes a serial device, either by an index or the number field

        """
        funcname = 'rem_serial_device()'
        self.logger.debug(funcname)                
        if(number != None):
            for i,s in enumerate(self.serial):
                if(s['number'] == number):
                    serialdevice = s
                    ind = i
                    break
        else:
            serialdevice = self.serial[ind]
            
        if(self.pymqdatastream != None):
            self.logger.debug(funcname + ': Removing datastreams')
            for s in serialdevice['streams']:
                self.pymqdatastream.rem_stream(s)        
        serialdevice['thread_queue'].put('stop')
        time.sleep(0.2) # Wait for the thread to read the 'stop' signal

        if(type(serialdevice['device']) == serial.Serial):
            self.logger.debug(funcname + ': Stopping a serial device')
            serialdevice['device'].close()
            # Remove the entry from the serial devices list
            self.serial.pop(ind)            
            # Call the signal functions
            for s in self.signal_functions:
                s(funcname)

        elif(type(serialdevice['device']) == socket.socket):
            self.logger.debug(funcname + ': Stopping a TCP socket-device')
            serialdevice['device'].close()
            # Remove the entry from the serial devices list
            self.serial.pop(ind)            
            # Call the signal functions
            for s in self.signal_functions:
                s(funcname)                
        else:
            self.logger.debug(funcname + ': Unknown device type')


        
        
            
def main():
    """

    Main routine

    """
    usage_str = 'pynmeatools_nmea0183logger --serial_device /dev/ttyACM0 -f test_log -v -v -v'
    desc = 'A python NMEA logger. Example usage: ' + usage_str
    serial_help = 'Serial device to read data from in unixoid OSes e.g. /dev/ttyACM0'
    interval_help = 'Time interval at which new files are created (in seconds)'
    datastream_help = 'Connect to a nmea0183logger published with pymqdatastream'
    publish_datastream_help = 'Create a pymqdatastream Datastream to publish the data over a network, no argument take standard address, otherwise specify zeromq compatible address e.g. tcp://192.168.178.10'
    raw_data_datastream_help = 'Print raw NMEA data of all devices to the console'                                
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--log_stream', '-l')
    parser.add_argument('--filename', '-f')
    parser.add_argument('--serial_device', '-s', nargs='+', action='append', help=serial_help)
    parser.add_argument('--address', '-a')
    parser.add_argument('--port', '-p')
    parser.add_argument('--interval', '-i', default=0, type=int, help=interval_help)        
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--publish_datastream', '-pd', nargs = '?', default = False, help=publish_datastream_help)
    parser.add_argument('--datastream', '-d', nargs = '?', default = False, help=datastream_help)
    parser.add_argument('--print_raw_data', '-r', action='store_true', help=raw_data_datastream_help)                                

    args = parser.parse_args()
    # Print help and exit when no arguments are given
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)
    
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG
        
    logger.setLevel(loglevel)
    
    time_interval = args.interval
    # Create a nmeaGrabber
    print('hallo Creating a logger')
    s = nmea0183logger(loglevel=logging.DEBUG,print_raw_data = args.print_raw_data)
    try:
        filename = args.filename
        print(filename)
        s.log_data_in_files(filename,datetime.timedelta(seconds=time_interval))
    except Exception as e:
        logger.debug('main(): ' + str(e))
    
    logger.debug('main(): ' + str(args.serial_device))
    #serial_device = args.serial_device
    if(args.serial_device != None):
        for serial_device in args.serial_device:
            logger.debug('Adding serial device ' + str(serial_device))
            serial_device = serial_device[0]
            if(serial_device != None):
                try:
                    s.add_serial_device(serial_device)
                except Exception as e:
                    logger.debug('main():',e)
                    
    
    if(args.address != None and args.port != None):
        addr = args.address
        port = int(args.port)
        s.add_tcp_stream(addr,port)



    
    print('Args publish_datastream:',args.publish_datastream)
    # Create datastream? 
    if(args.publish_datastream != False):
        if(args.publish_datastream == None):        
            logger.debug('Creating a pymqdatastream at standard address')
            s.create_pymqdatastream()
            s.publish_devices()
        else:
            logger.debug('Creating a pymqdatastream at address: ' + str(args.publish_datastream))
            s.create_pymqdatastream(address = args.publish_datastream)
            s.publish_devices()            
            


    # Connect to datastream?
    # False if not specified, None if no argument was given, otherwise address
    print('Args datastream:',args.datastream)
    if(args.datastream != False):    
        if(args.datastream == None):
            logger.debug('Connecting to  pymqdatastream Datastream logger')
            s.add_datastream()
        else:
            logger.debug('Connecting to pymqdatastream at address: ' + str(args.datastream))
            s.add_datastream(args.datastream)            

        

    while(True):
        time.sleep(1.0)


if __name__ == "__main__":
    main()
    #pynmea0183logger --address 192.168.236.72 -p 10007 -f test_peter -v -v -v
    #pynmea0183logger --serial_device /dev/ttyACM0 -f test_peter -v -v -v
    #pynmeatools_nmea0183logger --address 192.168.151.214 --port 4008 -v -v -v

