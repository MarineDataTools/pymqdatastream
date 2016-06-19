#!/usr/bin/env python3
import sys
import os
import pymqdatastream
import pymqdatastream.connectors.nmea.NMEA0183grabber as NMEA0183grabber
import logging
try:
    import queue as queue # python 3
except:
    import Queue as queue # python 2.7
import threading
import serial
import collections
import time
import calendar
import json
import pynmea2

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

        Args:
            device: serial device (e.g. '/dev/ttyUSB0' for linux or 'COM1' for windows)
        """
        # Add a deque in which the NMEA0183 object is putting the data
        self.NMEA0183grabber.add_serial_device(device)

    def add_NMEA_stream(self,address,port):
        """
        Adds a TCP stream

        Args:
            address:
            port:
        """
        # Add a deque in which the NMEA0183 object is putting the data
        self.NMEA0183grabber.add_tcp_stream(address,port)
        

    def add_raw_NMEA_stream(self):
        """



        """
        
        self.deques.append(collections.deque(maxlen=self.dequelen))
        self.NMEA0183grabber.deques.append(self.deques[-1])
        self.add_pub_socket()
        nmeavar = pymqdatastream.StreamVariable(name = 'NMEA0183',unit = '',datatype = 'pymqds_NMEA0183 raw data dict')
        variables = [nmeavar,]
        name = 'raw NMEA0183'
        stream = self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables)
        NMEA_thread = threading.Thread(target=self.push_raw_NMEA_data,args = (stream,self.deques[-1]))
        self.thread.append(NMEA_thread)
        self.thread[-1].daemon = True
        self.thread[-1].start()


    def push_raw_NMEA_data(self,stream, deque):
        """

        Function that pushes NMEA data to pymqdatastream stream, used
        in a thread

        """
        while True:
            time.sleep(0.1)
            while(len(deque) > 0):
                data = deque.pop()
                #data_json = json.dumps(data).encode('utf-8')
                stream.pub_data([[data,],])


    def add_latlon_NMEA_stream(self):
        """ 

        Addings an interpreted stream which is grabbing GPGLL and time strings
        to get a time,lat,lon information

        Return:
            stream: pymdatastream stream

        """

        self.deques.append(collections.deque(maxlen=self.dequelen))
        self.NMEA0183grabber.deques.append(self.deques[-1])

        # Create a pymqdatastream stream
        nmea_time = pymqdatastream.StreamVariable(name = 'NMEA0183 time',unit = 'HHMMSS',datatype = 'str')
        nmea_utime = pymqdatastream.StreamVariable(name = 'NMEA0183 unix time',unit = 's',datatype = 'float')        
        nmea_lat = pymqdatastream.StreamVariable(name = 'NMEA0183 lat',unit = 'deg N',datatype = 'float')
        nmea_lon = pymqdatastream.StreamVariable(name = 'NMEA0183 lon',unit = 'deg E',datatype = 'float')        
        variables = [nmea_time, nmea_utime, nmea_lon, nmea_lat]
        name = 'NMEA0183 time,lon,lat'
        stream = self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables)

        # Start a thread to read the data
        NMEA_latlon_thread = threading.Thread(target=self.push_latlon_NMEA_data,args = (stream,self.deques[-1]))
        self.thread.append(NMEA_latlon_thread)
        self.thread[-1].daemon = True
        self.thread[-1].start()
        
        return stream

        
    def push_latlon_NMEA_data(self,stream, deque):
        """
        """

        while True:
            time.sleep(0.1)
            while(len(deque) > 0):
                data = deque.pop()
                #print data                
                # Interprete the data
                try:
                    data_nmea = pynmea2.parse(data['nmea'])
                    data_time = data['time']
                    # Merge the date of the unix time sent and the
                    # HHMMSS of the GPGGA string together
                    ts = time.gmtime(data_time)
                    tstr = time.strftime("%Y%m%d",ts)
                    #
                    if(data_nmea.identifier().rfind('GPGGA')>=0):
                        #print('lat/lon!')
                        nmea_time = data_nmea.timestamp.strftime("%H%M%S")
                        tstr_unix = tstr + nmea_time
                        #print('unix time',tstr_unix)
                        tfloat_unix = calendar.timegm(time.strptime(tstr_unix,"%Y%m%d%H%M%S"))
                        lat = data_nmea.latitude
                        lon = data_nmea.longitude
                        #print(nmea_time)
                        #print(tfloat_unix,time.gmtime(tfloat_unix))
                        #print(data_nmea.latitude)
                        #print(data_nmea.longitude)
                        stream.pub_data([[nmea_time,tfloat_unix,lon,lat],])

                except Exception as e:
                    print(str(e) + ' Bad data ')




if __name__ == '__main__':
    s = NMEA0183DataStream()
    #s.add_NMEA_device('/dev/ttyUSB0')

    s.add_NMEA_stream("192.168.236.72",10007)
    
    s.add_raw_NMEA_stream()
    s.add_latlon_NMEA_stream()    

    while(True):
        time.sleep(1.0)
    
