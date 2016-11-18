#!/usr/bin/env python3
import sys
import os
import pymqdatastream
import pymqdatastream.connectors.sam4log.netstring as netstring
import pymqdatastream.connectors.sam4log.ltc2442 as ltc2442
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
import re
from cobs import cobs

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqds_sam4log')
logger.setLevel(logging.DEBUG)


class sam4logDataStream(pymqdatastream.DataStream):
    """

    
    
    """
    def __init__(self, **kwargs):
        """
        """
        super(sam4logDataStream, self).__init__(**kwargs)
        uuid = self.uuid
        uuid.replace('DataStream','sam4logDataStream')
        self.name = 'sam4log'
        self.uuid = uuid
        self.status = -1 # -1 init, 0 opened serial port, 1 converting
        self.init_notification_functions = [] # A list of functions to be called after the logger has been initialized/reinitialized
        funcname = self.__class__.__name__ + '.__init__()'
        self.logger.debug(funcname)
        self.dequelen = 10000 # Length of the deque used to store data
        self.flag_adcs = [] # List of adcs to be send by the logger hardware
        self.device_info = None
        self.print_serial_data = False
        self.serial_thread_queue = queue.Queue()
        self.serial_thread_queue_ans = queue.Queue()

        self.bytes_read = 0
        self.serial = None # The device to be connected to
        # Two initial queues, the first is for internal use (init logger, query_sam4log), the second is for the raw stream
        self.deques_raw_serial = [collections.deque(maxlen=self.dequelen),collections.deque(maxlen=self.dequelen)]
        self.intraqueue = collections.deque(maxlen=self.dequelen) # Queue for for internal processing, e.g. printing of processed data
        # Two queues to start/stop the raw_data conversion threads
        self.conversion_thread_queue = queue.Queue()
        self.conversion_thread_queue_ans = queue.Queue()

        # Two queues to start/stop the raw_data datastream thread
        self._raw_data_thread_queue = queue.Queue()
        self._raw_data_thread_queue_ans = queue.Queue()        
        # List of conversion streams
        self.conv_streams = []
        # A list with Nones or the streams dedicated for the channels
        self.channel_streams = None
        self.commands = []

        # The data format
        self.data_format = 0


    def load_file(self,filename):
        """
        loads a file and reads it chunk by chunk
        """
        funcname = self.__class__.__name__ + '.load_file()'
        self.bytes_read = 0
        self.data_file = file(filename)
        self.logger.debug(funcname + ': Starting thread')            
        self.file_thread = threading.Thread(target=self.read_file_data)
        self.file_thread.daemon = True
        self.file_thread.start()            
        self.logger.debug(funcname + ': Starting thread done')

        
    def read_file_data(self, dt = 0.01, num_bytes = 200):
        """

        The function which reads the file

        """
        funcname = self.__class__.__name__ + '.read_serial_data()'
        self.logger.debug(funcname)
        while True:
            time.sleep(dt)
            if(True):
                try:
                    data = self.data_file.read(num_bytes)
                    if(data == ''):
                        self.logger.debug(funcname + ': EOF')
                        return True
                    
                    self.bytes_read += num_bytes
                    for n,deque in enumerate(self.deques_raw_serial):
                        deque.appendleft(data)

                except Exception as e:
                    self.logger.debug(funcname + ':Exception:' + str(e))

                    
            # Try to read from the queue, if something was read, quit
            try:
                data = self.serial_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                break
            except queue.Empty:
                pass
                    
        return True                    

        
    def add_serial_device(self,port,baud=921600):
        """
        """
        funcname = self.__class__.__name__ + '.add_serial_device()'
        #try:
        if(True):
            self.logger.debug(funcname + ': Opening: ' + port)            
            self.bytes_read = 0
            self.serial = serial.Serial(port,baud)
            self.logger.debug(funcname + ': Starting thread')            
            self.serial_thread = threading.Thread(target=self.read_serial_data)
            self.serial_thread.daemon = True
            self.serial_thread.start()            
            self.logger.debug(funcname + ': Starting thread done')
            self.status = 0
        else:
        #except Exception as e:
            self.logger.debug(funcname + ': Exception: ' + str(e))            
            self.logger.debug(funcname + ': Could not open device at: ' + str(port))

            
    def read_serial_data(self, dt = 0.003):
        """

        The serial data polling thread

        Args:
            dt: Sleeping time between polling [default 0.003]

        """
        funcname = self.__class__.__name__ + '.read_serial_data()'
        self.logger.debug(funcname)
        while True:
            time.sleep(dt)
            num_bytes = self.serial.inWaiting()
            if(num_bytes > 0):
                try:
                    data = self.serial.read(num_bytes)
                    if(self.print_serial_data):
                        print(data)
                        
                    self.bytes_read += num_bytes
                    for n,deque in enumerate(self.deques_raw_serial):
                        deque.appendleft(data)
                except Exception as e:
                    logger.debug(funcname + ':Exception:' + str(e))

                    
            # Try to read from the queue, if something was read, quit
            try:
                data = self.serial_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self.serial_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass
                    
        return True


    def send_serial_data(self,data):
        """
        
        Sends data to serial device
        
        """
        funcname = self.__class__.__name__ + '.send_serial_data()'
        if(self.serial != None):
            self.logger.debug(funcname + ': Sending to device:' + str(data))
            # Python2 work with that
            self.serial.write(str(data).encode('utf-8'))
            self.logger.debug(funcname + ': Sending done')
        else:
            self.logger.warning(funcname + ':Serial port is not open.')


    def stop_serial_data(self):
        """

        Closes the serial port and does a cleanup of running threads etc.

        """
        funcname = self.__class__.__name__ + '.stop_serial_data()'
        self.logger.debug(funcname + ': Stopping')
        self.serial_thread_queue.put('stop')
        data = self.serial_thread_queue_ans.get()
        self.logger.debug(funcname + ': Got data, thread stopped')
        self._rem_raw_data_stream()
        self.serial.close()
        self.status = -1

        
    def log_serial_data(self,filename):
        """
        Saves the raw serial data into filename
        """
        funcname = self.__class__.__name__ + '._log_serial_data()'        
        deque = collections.deque(maxlen=self.dequelen)
        self.deques_raw_serial.append(deque)
        self._log_thread_queue = queue.Queue()
        self._log_thread_queue_ans = queue.Queue()
        self.logfile = open(filename,'wb')
        self._logfile_thread = threading.Thread(target=self._logging_thread,args=(deque,self.logfile))
        self._logfile_thread.daemon = True
        self._logfile_thread.start()

        
    def stop_log_serial_data(self):
        """
        """
        self._log_thread_queue.put('stop')
        data = self._log_thread_queue_ans.get()
        self.logger.debug('Got data from conversion thread; thread stopped.')
        self.logfile.close()

        
    def _logging_thread(self,deque,logfile,dt = 0.2):
        funcname = self.__class__.__name__ + '._logging_thread()'        
        while True:
            logfile.flush()                            
            time.sleep(dt)
            # Try to read from the queue, if something was read, quit
            while(len(deque) > 0):
                data = deque.pop()
                logfile.write(data)
            try:
                data = self._log_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self._log_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass                                        

        
    def add_raw_data_stream(self):
        """
        
        Adds a stream containing the raw data read from sam4log. 

        Args: None
            
        Returns:
            raw_stream: the raw data stream 
        
        """
        
        funcname = self.__class__.__name__ + '.add_raw_data_stream()'
        logger.debug(funcname)
        self.add_pub_socket()
        rawvar = pymqdatastream.StreamVariable(name = 'serial binary',unit = '',datatype = 'b')
        variables = ['serial binary',]
        name = 'serial binary'

        stream = self.add_pub_stream(socket = self.sockets[-1],name=name,variables=[rawvar])
        self.raw_stream = stream
        self.raw_stream_thread = threading.Thread(target=self.push_raw_stream_data,args = (self.Streams[-1],))
        self.raw_stream_thread.daemon = True
        self.raw_stream_thread.start()
        return stream

    def _rem_raw_data_stream(self):
        """
        Stops the raw_data thread and removes self.raw_data
        """

        funcname = self.__class__.__name__ + '.rem_raw_data_stream()'
        self.logger.debug(funcname + ': Stopping conversion thread')
        self._raw_data_thread_queue.put('stop')
        data = self._raw_data_thread_queue_ans.get()
        self.logger.debug(funcname + ': Got data from conversion thread, thread stopped')
        self.rem_stream(self.raw_stream)
        
        
    def push_raw_stream_data(self,stream,dt = 0.1):
        """
        
        Pushes the raw serial data into the raw datastream
        
        """
        
        funcname = self.__class__.__name__ + '.push_raw_stream_data()'
        logger.debug(funcname)        
        deque = self.deques_raw_serial[1]
        while True:
            time.sleep(dt)
            data_all = []
            while(len(deque) > 0):
                data = deque.pop()
                data_all.append(data)
                stream.pub_data(data_all)

            # Try to read from the queue, if something was read, quit
            try:
                data = self._raw_data_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self._raw_data_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass                                

                
    def init_data_format_functions(self):
        """
        
        
        """
        funcname = self.__class__.__name__ + '.init_data_format_functions()'
        self.logger.debug(funcname)                
        if(self.data_format == 0):
            self.convert_raw_data = self.convert_raw_data_format0

        if(self.data_format == 2):
            self.convert_raw_data = self.convert_raw_data_format2

        if(self.data_format == 3):
            self.convert_raw_data = self.convert_raw_data_format3


    def init_sam4logger(self,adcs,data_format=3,channels=[0],speed=30):
        """
    
        Function to set specific settings on the logger
        Args:
            flag_adcs: List of the ltc2442 channels to be send back [e.g. [0,2,7]], has to be between 0 and 7
            format: Output format of the logger
        
        """
        funcname = self.__class__.__name__ + '.init_sam4logger()'

        self.logger.debug(funcname)
        if(self.status >= 0):
            if(self.status >= 1): # Already converting
                self.logger.debug(funcname + ': Stop converting raw data')
                self.stop_converting_raw_data()
                
            self.print_serial_data = True        
            self.send_serial_data('stop\n')
            time.sleep(0.1)
            # Which ADCS?
            self.flag_adcs = adcs
            cmd = 'send ad'
            for ad in self.flag_adcs:
                cmd += ' %d' %ad
            self.send_serial_data(cmd + '\n')
            self.logger.debug(funcname + ' sending:' + cmd)
            time.sleep(0.1)
            # Due to a bug speed has to be send before data format if speed is 30, check firmware!
            # Speed
            cmd = 'speed ' + str(speed)
            self.send_serial_data(cmd + '\n')
            self.logger.debug(funcname + ' sending:' + cmd)
            
            # Data format
            self.data_format = data_format
            self.init_data_format_functions()
            cmd = 'format ' + str(data_format) + '\n'
            self.send_serial_data(cmd)
            self.logger.debug(funcname + ' sending:' + cmd)
            time.sleep(0.1)
            # Channel sequence
            cmd = 'channels '
            for ch in channels:
                cmd += ' %d' %ch
            self.send_serial_data(cmd + '\n')
            self.logger.debug(funcname + ' sending:' + cmd)
            time.sleep(0.1)        


            self.print_serial_data = False            
            # Update the device_info struct etc.
            self.query_sam4logger()
            self.send_serial_data('start\n')
            for fun in self.init_notification_functions:
                fun()
        else:
            self.logger.debug(funcname + ': No serial port opened')

    def query_sam4logger(self):
        """
        
        Queries the logger and sets the important parameters to the values read
        TODO: Do something if query fails

        Returns:
            bool: True if we found a sam4logger, False otherwise

        
        """
        
        funcname = self.__class__.__name__ + '.query_sam4logger()'
        self.logger.debug(funcname)        
        self.print_serial_data = False
        self.send_serial_data('stop\n')
        time.sleep(0.1)
        # Flush the serial queue now
        deque = self.deques_raw_serial[0]
        while(len(deque) > 0):
            data = deque.pop()


        #
        # Send stop and info to check if we got some data which is a sam4log
        #
        FLAG_IS_SAM4LOG = False
        self.send_serial_data('stop\n')
        time.sleep(0.1)        
        self.send_serial_data('info\n')
        time.sleep(0.1)        
        data_str = ''        
        while(len(deque) > 0):
            data = deque.pop()
            try:
                data_str += data.decode(encoding='utf-8')
            except Exception as e:
                self.logger.debug(funcname + ': Exception:' + e)
                return False

        return_str = data_str
        # Parse the received data for a valid reply
        if( '>>>stop' in data_str ):
            FLAG_IS_SAM4LOG=True
            self.logger.debug(funcname + ': Found a valid stop reply')
            for line in data_str.split('\n'):
                print(line)
                if( ' board version:' in line ):
                    # Expecting a string like this:
                    # >>> --  board version: 9.00 --
                    boardversion = line.rsplit(': ')
                    try:
                        boardversion = boardversion[1].split(' --')[0]
                    except:                    
                        self.logger.debug(funcname + ': No valid version string')
                    print('Board version:',boardversion)           
                elif( 'firmware version:' in line ):
                    # Expecting a string like this:
                    # >>> --  firmware version: 0.30 --
                    firmwareversion = line.rsplit(': ')
                    try:
                        firmwareversion = firmwareversion[1].split(' --')[0]
                    except:
                        self.logger.debug(funcname + ': No valid version string')
                    print('Firmware version:',firmwareversion)
                
            
        if(FLAG_IS_SAM4LOG==False):
            self.logger.warning(funcname + ': Device does not seem to be a sam4log')
            return False
        else:
            self.device_info = {}
            self.device_info['board'] = boardversion
            self.device_info['firmware'] = firmwareversion            
            
        self.send_serial_data('format\n')
        time.sleep(0.1)
        self.send_serial_data('ad\n')
        time.sleep(0.1)
        self.send_serial_data('channels\n')
        time.sleep(0.1)        
        self.print_serial_data = False                
        self.send_serial_data('start\n')

        # Get the fresh data
        data_str = ''
        while(len(deque) > 0):
            data = deque.pop()
            data_str += data.decode(encoding='utf-8')
            #data_str += data

        print(data_str)
        #print('Data str:' + data_str)
        # Parse the data
        print('Info is')
        #data_str= ">>>format\n>>> is a command with length 7\n>>>format is 2\n>>>ad\n>>> is a command with length 3\n>>>adcs: 0 2 4\n"
        # Look for a format string ala ">>>format is 2"
        data_format = None
        format_str = ''
        for i,me in enumerate(re.finditer(r'>>>format:.*\n',data_str)):
            format_str = me.group()

        adc_str = ''
        for i,me in enumerate(re.finditer(r'>>>adcs:.*\n',data_str)):
            adc_str = me.group()

        channel_str = ''
        for i,me in enumerate(re.finditer(r'>>>channel sequence:.*\n',data_str)):
            channel_str = me.group()                        

        print('Channel str:' + channel_str)
        data_format = [int(s) for s in re.findall(r'\b\d+\b', format_str)][-1]
        data_adcs = [int(s) for s in re.findall(r'\b\d+\b', adc_str)]
        data_channel_seq = [int(s) for s in re.findall(r'\b\d+\b', channel_str)]

        self.device_info['counterfreq'] = 10000.0 # TODO, this should come frome the firmware
        self.device_info['format'] = data_format
        self.device_info['adcs'] = data_adcs
        self.device_info['channel_seq'] = data_channel_seq
        # Create a list for each channel and fill it later with streams
        self.channel_streams = [None] * (max(data_channel_seq) + 1)
        
        # Update the local parameters
        self.logger.debug(funcname + ': format:' + str(data_format) + ' adcs:' + str(data_adcs) + ' channel sequence:' + str(data_channel_seq))
        # TODO, replace by device_info dict
        self.data_format = data_format
        self.init_data_format_functions()
        self.flag_adcs = data_adcs
        return True
        
        
    def start_converting_raw_data(self):
        """


        Starting a thread to convert the raw data

        Args:
        Returns:
            stream: A stream of the converted data


        """
        
        funcname = self.__class__.__name__ + '.start_converting_raw_data()'
        self.logger.debug(funcname)

        if(self.device_info != None):
            deque = collections.deque(maxlen=self.dequelen)
            self.deques_raw_serial.append(deque)
            for ch in self.device_info['channel_seq']:
                self.logger.debug(funcname + ': Adding pub stream for channel:' + str(ch))
                # Adding a stream with all ltcs for each channel
                timevar = pymqdatastream.StreamVariable('time','seconds','float')
                packetvar = pymqdatastream.StreamVariable('packet','number','int')
                variables = [packetvar,timevar]

                for ad in self.flag_adcs:
                    datavar = pymqdatastream.StreamVariable('ad ' + str(ad) + ' ch ' + str(ch),'V','float')
                    variables.append(datavar)

                name = 'sam4log ad ch' + str(ch)
                self.conv_streams.append(self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables))
                self.channel_streams[ch] = self.conv_streams[-1]
                
            self.logger.debug(funcname + ': Starting thread')
            # Analyse data format, choose the right conversion functions and start a conversion thread
            self.init_data_format_functions()
            self.packets_converted = 0

            self.convert_thread = threading.Thread(target=self.convert_raw_data,args = (deque,))
            self.convert_thread.daemon = True
            self.convert_thread.start()            
            self.logger.debug(funcname + ': Starting thread done')
            self.status = 1
            return self.conv_streams
    

    def stop_converting_raw_data(self):
        """

        Stops a raw data conversion thread and removes all streams

        """
        funcname = self.__class__.__name__ + '.stop_converting_raw_data()'
        self.logger.debug(funcname + ': Stopping conversion thread')
        self.conversion_thread_queue.put('stop')
        data = self.conversion_thread_queue_ans.get()
        self.logger.debug(funcname + ': Got data from conversion thread, thread stopped')

        self.channel_streams = None        
        for stream in self.conv_streams:
            self.rem_stream(stream)
            
        self.conv_streams = []
        # A list with Nones or the streams dedicated for the channels
        self.packets_converted = 0
        self.status = 0


    # Warning, this does not work anymore (at the moment) due to new streams!
    def convert_raw_data_format0(self, deque, dt = 0.5):
        """
        Converts raw data of the format 0, which is popped from the deque given as argument
        036:0>450003;16;30
        0;1345e3;+3.67705640
        ,
        """
        funcname = self.__class__.__name__ + '.convert_raw_data_format0()'
        self.logger.debug(funcname)
        ad0_converted = 0
        data_str = ''
        while True:
            #logger.debug(funcname + ': converted: ' + str(ad0_converted))
            time.sleep(dt)
            data0 = []
            while(len(deque) > 0):
                data = deque.pop()
                data_str += data
                # Get commands first
                for i,me in enumerate(re.finditer(r'[><][><][><].*\n',data_str)):
                    #print('COMMAND!',i)
                    #print(me)
                    #print(me.group(0))
                    #print(me.span(0))
                    self.commands.append(me.group(0))

                #logger.debug(funcname + ': str: ' + str(data_str))  
                [data_str,data_netstr] = netstring.get_netstring(data_str)
                #logger.debug(funcname + ': raw: ' + str(data_str))
                #logger.debug(funcname + ': net: ' + str(data_netstr))
                for nstr in data_netstr:
                    if(nstr[0:2] == '0>'):
                        print(nstr)
                        d_split = nstr.split('\n')
                        # Remove empty last packet
                        if(len(d_split[-1]) == 0):
                            d_split.pop(-1)
                            
                        d_split0 = d_split[0].split(';')
                        timer10khz = float(d_split0[0][2:])
                        timer_seconds = timer10khz / 10000.0
                        channel = int(d_split0[1])
                        cnv_speed = int(d_split0[2])                        
                        num_ltcs = len(d_split) - 1
                        self.logger.debug(funcname + ': num_ltcs:' + str(num_ltcs)) 
                        data_tmp = [timer_seconds]
                        for nltc in range(num_ltcs):
                            d_split_ltc = d_split[1+nltc].split(';')
                            print('Hallo',d_split_ltc)
                            data_num_ltc = int(d_split_ltc[0])
                            data_V = float(d_split_ltc[2])
                            data_tmp.append(data_V)
                            
                        data0.append(data_tmp)
                        self.packets_converted += 1
                    else:
                        self.logger.debug(funcname + ': no a valid format 0 string:')


            # Push the read data
            ti = time.time()
            
            if(len(data0)>0):
                streams[0].pub_data(data0)
                self.intraqueue.appendleft(data0)
                #self.channel_streams[ch]

            # Try to read from the queue, if something was read, quit
            try:
                data = self.conversion_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self.conversion_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass                


    def convert_raw_data_format2(self, deque, dt = 0.1):
        """

        Converts raw data of the format 2, which is popped from the deque
        given as argument 
        The data is sends in binary packages using the the consistent overhead
        byte stuffing (`COBS
        <https://en.wikipedia.org/wiki/Consistent_Overhead_Byte_Stuffing>`_)
        algorithm.
        After decoding cobs the binary data has the following content

        ==== ====
        Byte Usage
        ==== ====
        0    0xAD (Packet type)
        1    FLAG LTC (see comment)
        2    LTC COMMAND 0 (as send to the AD Converter)
        3    LTC COMMAND 1
        5    LTC COMMAND 2
        6    counter msb
        ...   
        13   counter lsb
        14   clock 50 khz msb
        ...    
        21   clock 50 khz lsb
        22   LTC2442 0 msb
        23   LTC2442 1 
        24   LTC2442 2 lsb 
        .    3 bytes per activated LTC2442

        ==== ====

        FLAG LTC: Every bit is dedicted to one of the eight physically
        available LTC2442 and is set to one if activated

        Args:
            deque:
            stream:
            dt: Time interval for polling [s]
        Returns:
            []: List of data

        """
        funcname = self.__class__.__name__ + '.convert_raw_data_format2()'
        self.logger.debug(funcname)
        ad0_converted = 0
        data_str = b''
        ind_ltcs = [0,0,0,0,0,0,0,0]
        while True:
            #logger.debug(funcname + ': converted: ' + str(ad0_converted))
            # Create an empty list for every channel
            #http://stackoverflow.com/questions/8713620/appending-items-to-a-list-of-lists-in-python
            nstreams = (max(self.device_info['channel_seq']) + 1)
            data_stream = [[] for _ in range(nstreams) ]
            time.sleep(dt)
            while(len(deque) > 0):
                data = deque.pop()
                data_str += data
                # Get commands first
                # 
                #for i,me in enumerate(re.finditer(b'[><][><][><].*\n',data_str)):
                #    print('COMMAND!',i)
                #    print(me)
                #    print(me.group(0))
                #    print(me.span(0))
                #    self.commands.append(me.group(0))
                    
            #print('data_str')
            #print(data_str)
            #print(type(data_str))
            #print('Hallo!!! ENDE')            
            data_split = data_str.split(b'\x00')
            if(len(data_split) > 0):
                if(len(data_split[-1]) == 0): # The last byte was a 0x00
                   data_str = b''
                else:
                   data_str = data_split[-1]

                for data_cobs in data_split:
                    #print('Cobs data:')
                    #print(data_cobs)
                    try:
                        #self.logger.debug(funcname + ': ' + data_decobs.encode('hex_codec'))
                        if(len(data_cobs) > 3):
                            data_decobs = cobs.decode(data_cobs)
                            #print('decobs data:')
                            #print(data_decobs)
                            #print(data_decobs[0],type(data_decobs[0]))                            
                            packet_ident    = data_decobs[0]
                            #self.logger.debug(funcname + ': packet_ident ' + str(packet_ident))
                            if(packet_ident == 0xad):
                                #print('JA')
                                #packet_flag_ltc = ord(data_decobs[1]) # python2
                                packet_flag_ltc = data_decobs[1]
                                num_ltcs        = bin(packet_flag_ltc).count("1")
                                # Convert ltc flat bits into indices
                                # If this is slow, this is a hot cython candidate
                                for i in range(8):
                                    ind_ltcs[i] = (packet_flag_ltc >> i) & 1
                                    
                                ind_ltc = ind_ltcs
                                packet_size = 5 + 8 + 8 + num_ltcs * 3
                                packet_com_ltc0 = data_decobs[2]
                                packet_com_ltc1 = data_decobs[3]
                                packet_com_ltc2 = data_decobs[4]
                                # Decode the command
                                speed,channel = ltc2442.interprete_ltc2442_command([packet_com_ltc0,packet_com_ltc1,packet_com_ltc2],channel_naming=1)
                                ind = 5
                                #self.logger.debug(funcname + ': ltc flag ' + str(packet_flag_ltc))
                                #self.logger.debug(funcname + ': Num ltcs ' + str(num_ltcs))
                                #self.logger.debug(funcname + ': Ind ltc '  + str(ind_ltc))
                                #self.logger.debug(funcname + ': channel '  + str(channel))                                
                                #self.logger.debug(funcname + ': packet_size ' + str(packet_size))
                                #self.logger.debug(funcname + ': len(data_cobs) ' + str(len(data_cobs)))
                                if(len(data_decobs) == packet_size):
                                    packet_num_bin  = data_decobs[ind:ind+8]
                                    packet_num      = int(packet_num_bin.hex(), 16) # python3
                                    ind += 8
                                    packet_time_bin  = data_decobs[ind:ind+8]
                                    packet_time     = int(packet_time_bin.hex(), 16)/self.device_info['counterfreq']
                                    data_list = [packet_num,packet_time]
                                    data_packet = {'num':packet_num,'50khz':packet_time}
                                    data_packet['spd'] = speed
                                    data_packet['ch'] = channel
                                    data_packet['ind'] = ind_ltcs
                                    data_packet['V'] = [9999.99] * num_ltcs
                                    ind += 8
                                    #self.logger.debug(funcname + ': Packet number: ' + packet_num_bin.hex())
                                    #self.logger.debug(funcname + ': Packet 10khz time ' + packet_time_bin.hex())
                                    for n,i in enumerate(range(0,num_ltcs*3,3)):
                                        data_ltc = data_decobs[ind+i:ind+i+3]
                                        data_ltc += 0x88.to_bytes(1,'big') # python3
                                        if(len(data_ltc) == 4):
                                            conv = ltc2442.convert_binary(data_ltc,ref_voltage=4.096,Voff = 2.048)
                                            #print(conv)
                                            data_packet['V'][n] = conv['V'][0]
                                            # This could make trouble if the list is too short ...
                                            data_list.append(conv['V'][0])
                                            self.packets_converted += 1
                                        #else:
                                        #    data_packet.append(9999.99)
                                    data_stream[channel].append(data_list)

                                        
                    except cobs.DecodeError:
                        self.logger.debug(funcname + ': COBS DecodeError')
                        pass

            # Lets publish the converted data!
            for i in range(len(self.channel_streams)):
                if(len(data_stream[i])>0):
                    self.channel_streams[i].pub_data(data_stream[i])
                    # Put a different format into the intraqueue,
                    # since the channels are seperate datastreams
                    # TODO, this is only the last, have to create a list!
                    self.intraqueue.appendleft(data_packet)

            # Try to read from the queue, if something was read, quit
            try:
                data = self.conversion_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self.conversion_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass


    def convert_raw_data_format3(self, deque, dt = 0.05):
        """
        Converts raw data of the format 3, which is popped from the deque given as argument
        Example:
        00000000692003;00000000000342;2;0;+2.04882227;4;-9.99999999
        10 khz counter; num package;channel;num ad;Volt ad; ...

        """
        funcname = self.__class__.__name__ + '.convert_raw_data_format3()'
        self.logger.debug(funcname)
        ad0_converted = 0
        data_packets = []
        while True:
            #logger.debug(funcname + ': converted: ' + str(ad0_converted))
            nstreams = (max(self.device_info['channel_seq']) + 1)
            # Create a list of data to be submitted for each stream
            data_stream = [[] for _ in range(nstreams) ] 
            data_str = ''
            time.sleep(dt)
            while(len(deque) > 0):
                data = deque.pop()
                data_str += data.decode(encoding='utf-8')
                #data_list = [packet_num,packet_time]
                data_packets = []
                #for line in data_str.splitlines():
                data_str_split = data_str.split('\n')
                if(len(data_str_split[-1]) == 0): # We have a complete last line
                    data_str = ''
                else:
                    data_str = data_str_split[-1]
                for line in data_str_split:
                    if(len(line)>0):
                        data_split = line.split(';')
                        packet_time = int(data_split[0])/self.device_info['counterfreq']
                        packet_num = int(data_split[1])
                        channel = int(data_split[2])
                        ad_data = data_split[3:]
                        # Fill the data list
                        data_list = [packet_num,packet_time]                    
                        # Fill the data packet dictionary
                        data_packet = {}
                        data_packet = {'num':packet_num,'50khz':packet_time}
                        data_packet['ch'] = channel
                        data_packet['V'] = [9999.99] * len(self.device_info['adcs'])
                        # Test if the lengths are same
                        if(len(ad_data) == len(self.device_info['adcs'] * 2)):
                            for n,i in enumerate(range(0,len(ad_data)-1,2)):
                                V = float(ad_data[i+1])
                                data_packet['V'][n] = V
                                data_list.append(V)
                        else:
                           logger.debug(funcname + ': List lengths do not match: ' + str(ad_data) + ' and with num of adcs: ' + str(len(self.device_info['adcs'])))


                        data_packets.append(data_packet)
                        data_stream[channel].append(data_list)
            # Push the read data
            ti = time.time()
            
            #if(len(data0)>0):
            #    streams[0].pub_data(data0)

            for i in range(len(self.channel_streams)):
                if(len(data_stream[i])>0):
                    self.channel_streams[i].pub_data(data_stream[i])            

            for data_packet in data_packets:
                self.intraqueue.appendleft(data_packet)
                #self.channel_streams[ch]

            # Try to read from the queue, if something was read, quit
            try:
                data = self.conversion_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self.conversion_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass                            
            

                
if __name__ == '__main__':
    s = sam4logDataStream(logging_level='DEBUG')
    s.add_serial_device('/dev/ttyUSB0')
    
    s.add_raw_data_stream()
    #s.load_file('netstring_format1.log')

    # Send a format 2 command
    time.sleep(0.5)
    s.init_sam4logger(flag_adcs = [0],data_format=2)
    s.query_sam4logger()
    time.sleep(0.5)
    #s.print_serial_data = True    
    s.start_converting_raw_data()    
    print(s.get_info_str('short'))
    while(True):
        #print('Raw bytes read ' + str(s.bytes_read))
        #print(s.get_info_str('short'))
        time.sleep(5)
    
