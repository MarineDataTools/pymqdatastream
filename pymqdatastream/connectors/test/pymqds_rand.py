#!/usr/bin/env python3
import time
import numpy as np
import json
import logging
import threading
import os,sys
import argparse
import pymqdatastream
import random
import string

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqdatastream_rand')
logger.setLevel(logging.INFO)
# TODO: http://stackoverflow.com/questions/367586/generating-random-text-strings-of-a-given-pattern
famstr = 'pymqds_rand'

class RandDataStream(pymqdatastream.DataStream):
    def __init__(self, **kwargs):
        """
        """
        super(RandDataStream, self).__init__(**kwargs)
        logger.debug('RandDatastream.__init__()')
        uuid = self.uuid
        uuid.replace('DataStream','RandDataStream')
        self.name = 'rand'
        self.uuid = uuid
        self.thread = []


    def add_sine_stream(self,dt = 1.0,f = 1.0,num_elements = 1):
        """
        """
        self.add_pub_socket()
        timevar = pymqdatastream.StreamVariable(name = 'unix time',unit = 'seconds',datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'data',datatype = 'float')        
        variables = [timevar,datavar]
        name = 'sine ' + str(dt) + ' ' + str(num_elements)
        stream = self.add_pub_stream(socket = self.sockets[-1], name=name, variables=variables, family = famstr)
        self.thread.append(threading.Thread(target=self.do_sine,args = (self.Streams[-1],dt,f,num_elements)))
        self.thread[-1].daemon = True
        self.thread[-1].start()
        return stream

        
        
    def add_random_stream(self,dt = 1.0,num_elements = 1):
        """
        Args:
            dt:
            num_elements:
        Returns:
            stream:
        """
        self.add_pub_socket()
        timevar = pymqdatastream.StreamVariable(name = 'unix time', unit = 'seconds', datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'data', datatype = 'float')        
        variables = [timevar,datavar]        
        name = 'random ' + str(dt) + ' ' + str(num_elements)
        stream = self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables, family = famstr)
        self.thread.append(threading.Thread(target=self.do_random,args = (self.Streams[-1],dt,num_elements)))
        self.thread[-1].daemon = True
        self.thread[-1].start()
        return stream


    def add_random_str_stream(self,dt = 1.0,num_elements = 1):
        """ adds a random stream

        Args:
            dt: time interval in seconds [default = 1.0]
            num_elements: number of elements generated every dt
        """
        self.add_pub_socket()
        timevar = pymqdatastream.StreamVariable(name = 'unix time',unit = 'seconds', datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'data',datatype = 'str')
        variables = [timevar,datavar]

        name = 'random str ' + str(dt) + ' ' + str(num_elements)
        stream = self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables, family = famstr)
        self.thread.append(threading.Thread(target=self.do_random_str,args = (self.Streams[-1],dt,num_elements)))
        self.thread[-1].daemon = True
        self.thread[-1].start()
        return stream
        
        
    def do_random(self,stream,dt,num_elements):
        """ 
        """
        c = 0
        npack = 0
        while True:
            #logger.debug('Sleeping')
            data_all = []
            for n in range(num_elements):
                ti = time.time()
                data = [ti, np.random.rand(1)[0]]
                data_all.append(data)
                c += 1
                time.sleep(dt/num_elements)

            stream.pub_data(data_all)
            #print('Hallo dt:' + str(dt) + ' len deque:' + str(len(stream.deque)) + ' data:' + str(stream.deque))            


    def do_random_str(self,stream,dt,num_elements):
        """
        """
        c = 0
        npack = 0
        Nchars = 60
        while True:
            data_all = []
            for n in range(num_elements):
                ti = time.time()
                chars = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(Nchars))
                data = [ti, chars]
                data_all.append(data)
                c += 1
                time.sleep(dt/num_elements)

            stream.pub_data(data_all)                


    def do_sine(self,stream,dt,f , num_elements):
        """
        """
        c = 0
        npack = 0
        while True:
            #logger.debug('Sleeping')
            data_all = []
            for n in range(num_elements):
                ti = time.time()
                data = [ti, np.sin(2 * np.pi * f * ti)]
                data_all.append(data)
                c += 1
                time.sleep(dt/num_elements)

            stream.pub_data(data_all)                                

                

def main():
    # For different loggers see also:
    # http://stackoverflow.com/questions/8837615/different-levels-of-logging-in-python
    publish_datastream_help = 'Create a pymqdatastream Datastream to publish the data over a network, no argument take standard address, otherwise specify zeromq compatible address e.g. tcp://192.168.178.10'            
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--publish_datastream', '-pd', nargs = '?', default = False, help=publish_datastream_help)    
    args = parser.parse_args()
    if(args.verbose == None):
        logger.info('logging level: CRITICAL')
        logging_level = logging.CRITICAL
    elif(args.verbose == 1):
        logger.info('logging level: INFO ')        
        logging_level = logging.INFO
    elif(args.verbose >= 2):
        logger.info('logging level: DEBUG ')
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO


    logger.setLevel(logging_level)
    pymqdatastream.logger.setLevel(logging_level)

    address = None    
    print('Args publish_datastream:',args.publish_datastream)
    # Create datastream? 
    if(args.publish_datastream != False):
        if(args.publish_datastream == None):        
            logger.debug('Creating a pymqdatastream at standard address')
        else:
            logger.debug('Creating a pymqdatastream at address: ' + str(args.publish_datastream))
            address = args.publish_datastream

    RDS = RandDataStream(address = address, name = 'random',logging_level = logging_level)
    RDS.add_random_stream()
    
    for i in range(16):
        RDS.add_random_stream(dt = 0.2,num_elements = 40)

    for i in range(1):
        RDS.add_sine_stream(dt = 0.2, f = 2, num_elements = 20)


    for i in range(1):
        RDS.add_sine_stream(dt = 0.1, f = 0.05, num_elements = 2)        

    for i in range(1):
        RDS.add_random_str_stream(dt = 0.5, num_elements = 5)

    print(RDS.get_info_str('short'))
    while True:
        time.sleep(5)
        print('Schnarch')


if __name__ == '__main__':
    main()


