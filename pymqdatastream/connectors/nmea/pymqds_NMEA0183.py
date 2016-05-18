#!/usr/bin/env python3
import sys
import os
import pymqdatastream
import logging
try:
    import queue as queue # python 3
except:
    import Queue as queue # python 2.7
import threading
import serial
import collections
import time
import json
import NMEA0183grabber

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pydatastream_NMEA0183')
logger.setLevel(logging.DEBUG)


class NMEA0183DataStream(pymqdatastream.DataStream):
    """
    """
    def __init__(self):
        """
        """
        super(NMEA0183DataStream, self).__init__()
        uuid = self.uuid
        uuid.replace('DataStream','NMEA0183DataStream')
        self.uuid = uuid
        funcname = self.__class__.__name__ + '.__init__()'
        logger.debug(funcname)
        self.name = 'NMEA0183'
        self.NMEA0183grabber = NMEA0183grabber.NMEA0183Grabber()
        self.dequelen = 10000 # Length of the deque
        self.deques = []
        self.thread = []

    def add_NMEA_device(self,device):
        """
        Adds a device (at the moment only serial devices are implemented)
        input:
        device: serial device (e.g. '/dev/ttyUSB0' for linux or 'COM1' for windows)
        """
        # Add a deque in which the NMEA0183 object is putting the data
        self.NMEA0183grabber.add_serial_device(device)

    def add_raw_NMEA_stream(self):
        self.deques.append(collections.deque(maxlen=self.dequelen))
        self.NMEA0183grabber.deques.append(self.deques[-1])
        self.add_pub_socket()
        variables = ['NMEA0183',]
        name = 'NMEA0183'
        self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables)
        NMEA_thread = threading.Thread(target=self.push_raw_NMEA_data,args = (self.Streams[-1],self.deques[-1]))
        self.thread.append(NMEA_thread)
        self.thread[-1].daemon = True
        self.thread[-1].start()

    def push_raw_NMEA_data(self,stream, deque):
        while True:
            time.sleep(0.1)
            while(len(deque) > 0):
                ti = time.time()                
                data = deque.pop()
                data_dict = {'time':ti,'data':data}
                data_json = json.dumps(data_dict).encode('utf-8')
                stream.deque.appendleft(data_json)



if __name__ == '__main__':
    s = NMEA0183DataStream()
    s.add_NMEA_device('/dev/ttyUSB0')
    s.add_raw_NMEA_stream()

    while(True):
        time.sleep(1.0)
    
