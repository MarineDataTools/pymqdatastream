#!/usr/bin/env python3
import time
import numpy as np
#
import json
import ubjson
#
import logging
import threading
import os,sys
import argparse
import random
import string
import pymqdatastream
import datetime
try:
    import queue as queue # python 3
except:
    import Queue as queue # python 2.7

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqds_logger')
logger.setLevel(logging.DEBUG)



class LoggerDataStream(pymqdatastream.DataStream):
    """ The LoggerDataStream

    Creates a file in ubjson format:

    - fdsfsdf::

        : Hallo
        : Peter
    - fsdfs
    
    
    """
    def __init__(self, **kwargs):
        """ The __init__ function
        
        Initialises the LoggerDataStream class

        Args:
            filename (string): The file the data is written to, - for stdout

        Returns:
            bool: something
        """
        funcname = '.__init__()'
        # Get local arguments
        filename = kwargs.pop('filename', None)
        dname = kwargs.pop('name', None)
        if(dname == None):
            self.name = 'logger'
        else:
            kwargs['name'] = dname

        super(LoggerDataStream, self).__init__(**kwargs)
        uuid = self.uuid
        uuid.replace('DataStream','LoggerDataStream')
        self.uuid = uuid
        self.thread = []
        self.thread_queues = []
        self.f = None
        self.filename = None        
        self.first_free_log_number = 0 # The number a stream is logged
        self.logging = False
        self.log_streams = []

        if filename is not None:
            self.lf = LoggerFile(filename,'w')
            self.filename = filename
        else:
            raise Exception("Need a file to log to")

    def start_logging(self):
        funcname = self.__class__.__name__ + '.start_logging()'
        self.logger.debug(funcname)        
        if(self.logging == False):
            # Starts a data writing thread                
            self.start_write_data_thread()
            self.logger.debug(funcname + ': start logging thread')

    def stop_logging(self):
        funcname = self.__class__.__name__ + '.stop_logging()'
        self.logger.debug(funcname)        
        if(self.logging == True):
            self.stop_poll_data_thread()
            self.logger.debug(funcname + ': Stopped logging')
        else:
            self.logger.debug(funcname + ': not logging')


    def log_stream(self,stream):
        """ a stream to log

        Args:
            stream: Stream object or address of a stream, as for subscribe_stream, 
                    if stream has already been subscribed, the function will not make
                    a new subscription
        Returns:
            stream: stream object or None if subscription failed
        """

        funcname = self.__class__.__name__ + '.log_stream()'        
        self.logger.debug(funcname)
        new_subscription = True
        for sub_stream in self.Streams:
            if( stream == sub_stream ):
                new_subscription = False
                self.logger.debug(funcname + ': stream has already been subscribed')
                break
            
        if(new_subscription):
            self.logger.debug('log_stream(): subscribing to stream')
            stream = self.subscribe_stream(stream)
            
        if(stream != None):
            self.logger.debug(funcname + ': Writing data of stream')
            self.Streams[-1].log_stream = True
            self.Streams[-1].log_stream_number = self.first_free_log_number
            self.stream_header = self.get_stream_header()
            self.first_free_log_number += 1
            # Stops an already running data writing thread and restarts it
            if(self.logging):
                self.stop_poll_data_thread()
                # Starts a data writing thread                
                self.start_write_data_thread()


        return stream
 

    def start_write_data_thread(self):
        """
        
        Starts a write data thread
        
        """
        funcname = self.__class__.__name__ + '.start_write_data_thread()'
        self.logger.debug(funcname)
        stream_header = self.stream_header
        if(len(self.log_streams) > 0):
            # Write the stream header, TODO this should be written only if the header changed
            self.lf.write(stream_header)
            # Start the thread
            self.thread_queue = queue.Queue()
            self.thread_queue_answ = queue.Queue()            
            self.poll_data_thread = threading.Thread(target=self.poll_data)
            self.poll_data_thread.daemon = True
            self.logging = True
            self.logger.debug(funcname + ': starting thread')
            self.poll_data_thread.start()
        else:
            self.logger.warning(funcname + ': No streams to write to file')

            
    def stop_poll_data_thread(self):
        """

        Stops the poll data thread

        """
        funcname = self.__class__.__name__ + '.stop_poll_data_thread()'
        try:
            if(self.logging):
                self.thread_queue.put('stop')
                data = self.thread_queue_answ.get()
                print('Got an answer:' + data)
                self.logging = False
        except:
            self.logger.warning(funcname + ': No thread found to stop')

            
    def poll_data(self):
        """
        
        Polls the data in the self.log_streams streams and serializes them 
        
        """
        funcname = self.__class__.__name__ + '.poll_data()'
        print('data')
        while True:
            try:
                # If we got something, just quit!
                data = self.thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self.logger.debug(funcname + ': Stopping thread')
                self.lf.sync()                
                self.thread_queue_answ.put('stopped')
                break
            except queue.Empty:
                pass
            
            for s in self.log_streams:
                while(len(s.deque)>0):
                    data = s.deque.pop()
                    data = [s.log_stream_number,data]
                    self.lf.write(data)

            time.sleep(0.05)                    

            
    def get_stream_header(self):
        """ Returns a header of all streams
        
        """
        funcname = self.__class__.__name__ + '.get_stream_header()'
        stream_info = []
        self.log_streams = []
        self.logger.debug(funcname)        
        for s in self.Streams:
            try:
                log_stream = s.log_stream
                log_number = s.log_stream_number
                self.log_streams.append(s)
            except Exception as e:
                log_stream = False

            if(log_stream):
                #print('Header for stream')
                sinfo = s.get_info_dict()
                stream_info.append({'n':log_number,'info':sinfo})
            else:
                #print('no header for stream')
                pass

        # Serialise
        stream_info = {'streams':stream_info}
        return stream_info

    
    def close_file(self):
        self.stop_poll_data_thread()
        for sub_stream in self.Streams:
            try:
                if( stream.log_stream ):
                    stream.log_stream = False
            except:
                pass
            

        self.lf.close()
        self.filename = None

            


class LoggerFile(object):
    """
    """
    def __init__(self,filename,mode):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.filename = None
        try:
            self.logger.debug('Opening file with mode ' + mode)
            self.f = open(filename,mode)
            self.filename = filename
        except:
            self.logger.warning('Could not open file: ' + filename)


        # Init the file and write a file info header
        if(mode == 'w'):
            self.logger.debug('Writing header')
            header = ['Start LoggerFile']
            self.write(header)
            self.sync()

            
    def read(self,n = None):
        """
        Args:
        Returns:
            data_decode: List
        """
        print('Reading')
        data_decode_all = []
        data = ''
        for line in self.f:
            data += line
            try:
                data_decode = ubjson.loadb(data)
                data = ''
                data_decode_all.append(data_decode)
                print(data_decode)
            except:
                print('Could no decode:' + str(data))
                pass

        return data_decode_all

    def write(self,data):
        ubdata = ubjson.dumpb(data)
        ubdata = ubdata + b'\n'
        print('Writing')
        self.f.write(ubdata)

    def sync(self):
        self.f.flush()        

    def close(self):
        try:
            self.f.close()
        except:
            self.logger.warning('Could not close file: ' + self.filename)
            

# Test logger function
def test():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log_stream', '-l')
    parser.add_argument('--filename', '-f')    
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()
    
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG

    filename = args.filename
    #print('Logging to file: ' + filename)

    # Create a logger datastream
    loggerDS = LoggerDataStream(logging_level = loglevel, filename = filename)

    # Create a random datastream
    randDS = pymqdatastream.rand.RandDataStream()
    rstream = randDS.add_random_stream()


    #if(args.log_stream == None):
    #    print('No stream to add')
    #else:
    #    address = args.add_stream
    #    print('Adding stream ' + address)                

    logger.setLevel(loglevel)
    pymqdatastream.logger.setLevel(loglevel)        

    # Add stream to log and log
    logstream = loggerDS.log_stream(rstream)
    print('Writing file: ' + filename)
    loggerDS.start_write_data_thread()
    time.sleep(5)
    ret = loggerDS.stop_poll_data_thread()
    loggerDS.close_file()
    print('File written')
    print('Read file')    
    lfile = LoggerFile(filename,'r')
    lfile.read()
    
    print('Test done')


# Main function
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--log_stream', '-l')
    parser.add_argument('--filename', '-f')    
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()
    
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG

    filename = args.filename
    #print('Logging to file: ' + filename)

    # Create a logger datastream
    loggerDS = LoggerDataStream(logging_level = loglevel, filename = filename)

    # Create a random datastream
    randDS = pymqdatastream.rand.RandDataStream()
    rstream = randDS.add_random_stream()


    #if(args.log_stream == None):
    #    print('No stream to add')
    #else:
    #    address = args.add_stream
    #    print('Adding stream ' + address)                

    logger.setLevel(loglevel)
    pymqdatastream.logger.setLevel(loglevel)        

    # Add stream to log and log
    logstream = loggerDS.log_stream(rstream)
    loggerDS.start_write_data_thread()
    time.sleep(5)
    ret = loggerDS.stop_poll_data_thread()
    
    while True:
        print('Sleeping')
        print(loggerDS.get_info_str('short'))
        utc_datetime = datetime.datetime.utcnow()
        utc_str = utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
        print(utc_datetime.strftime("%Y%m%d%H%M%S%f"))
        print(len(logstream.deque))
        loggerDS.poll_data()
        time.sleep(200)
