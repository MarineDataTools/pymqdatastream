#!/usr/bin/env python
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
logger = logging.getLogger('pydatastream_sam4log')
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
        funcname = self.__class__.__name__ + '.__init__()'
        self.logger.debug(funcname)
        self.dequelen = 10000 # Length of the deque used to store data
        self.flag_adcs = [] # List of adcs to be send by the logger hardware
        self.print_serial_data = False
        self.serial_thread_queue = queue.Queue()
        self.serial_thread_queue_ans = queue.Queue()

        self.bytes_read = 0
        self.serial = None # The device to be connected to
        # Two initial queues, the first is for internal use (init logger), the second is for the raw stream
        self.deques_raw_serial = [collections.deque(maxlen=self.dequelen),collections.deque(maxlen=self.dequelen)]
        self.intraqueue = collections.deque(maxlen=self.dequelen) # Queue for for internal processing, e.g. printing of processed data
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
            print('Sending:' + str(data))
            self.serial.write(str(data))
            print('done')
        else:
            self.logger.debug(funcname + ':Serial port is not open.')


    def stop_serial_data(self):
        """

        Closes the serial port and does a cleanup of running threads etc.

        """
        self.logger.debug('Stopping')
        self.serial_thread_queue.put('stop')
        data = self.serial_thread_queue_ans.get()
        self.logger.debug('Got data, thread stopped')
        self.serial.close()
        
    
    def add_raw_data_stream(self):
        """
        
        
        """
        funcname = self.__class__.__name__ + '.add_raw_data_stream()'
        logger.debug(funcname)
        self.add_pub_socket()
        rawvar = pymqdatastream.StreamVariable(name = 'raw',unit = '',datatype = 'str')
        variables = ['raw',]
        name = 'raw'

        #timevar = pymqdatastream.StreamVariable('time','seconds','float')
        #datavar = pymqdatastream.StreamVariable('data_ad0','V','float')        
        #variables = [timevar,datavar]
        
        #name = 'sam4log_ad0'
        #self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables)
        
        #self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables)
        self.add_pub_stream(socket = self.sockets[-1],name=name,variables=[rawvar])
        self.raw_stream_thread = threading.Thread(target=self.push_raw_stream_data,args = (self.Streams[-1],))
        self.raw_stream_thread.daemon = True
        self.raw_stream_thread.start()

        
    def push_raw_stream_data(self,stream,dt = 0.1):
        """
        
        
        
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

                
    def init_data_format_functions(self):
        """
        
        
        """
        funcname = self.__class__.__name__ + '.init_data_format_functions()'
        self.logger.debug(funcname)                
        if(self.data_format == 0):
            self.convert_raw_data = self.convert_raw_data_format0

        if(self.data_format == 2):
            self.convert_raw_data = self.convert_raw_data_format2


    def init_sam4logger(self,flag_adcs,data_format=2):
        """
    
        Function to set specific settings on the logger
        Args:
            flag_adcs: List of the ltc2442 channels to be send back [e.g. [0,2,7]], has to be between 0 and 7
            format: Output format of the logger
        
        """
        funcname = self.__class__.__name__ + '.init_sam4logger()'
        self.logger.debug(funcname)        
        self.print_serial_data = True        
        self.send_serial_data('stop\n')
        time.sleep(0.1)
        self.flag_adcs = flag_adcs
        cmd = 'send ad'
        for ad in self.flag_adcs:
            cmd += ' %d' %ad
        self.send_serial_data(cmd + '\n')
        time.sleep(0.1)
        self.data_format = data_format
        self.init_data_format_functions()
        self.send_serial_data('format ' + str(data_format) + '\n')
        time.sleep(0.1)
        self.print_serial_data = False
        self.send_serial_data('start\n')


    def query_sam4logger(self):
        """
        
        Queries the logger and sets the importent parameters to the values read

        Args:
        
        Returns:
            something useful
        
        """
        
        funcname = self.__class__.__name__ + '.query_sam4logger()'
        self.logger.debug(funcname)        
        self.send_serial_data('stop\n')


        self.print_serial_data = False
        self.send_serial_data('stop\n')
        time.sleep(0.1)
        # Flush the serial queue now
        deque = self.deques_raw_serial[0]
        while(len(deque) > 0):
            data = deque.pop()                
        self.send_serial_data('format\n')
        time.sleep(0.1)
        self.send_serial_data('ad\n')
        time.sleep(0.1)
        self.print_serial_data = False                
        self.send_serial_data('start\n')

        # Get the fresh data
        data_str = ''
        while(len(deque) > 0):
            data = deque.pop()
            data_str += data


        # Parse the data
        print('Info is')
        #data_str= ">>>format\n>>> is a command with length 7\n>>>format is 2\n>>>ad\n>>> is a command with length 3\n>>>adcs: 0 2 4\n"
        # Look for a format string ala ">>>format is 2"
        data_format = None
        format_str = ''
        for i,me in enumerate(re.finditer(r'>>>format is.*\n',data_str)):
            format_str = me.group()

        adc_str = ''
        for i,me in enumerate(re.finditer(r'>>>adcs:.*\n',data_str)):
            adc_str = me.group()            

        data_format = [int(s) for s in re.findall(r'\b\d+\b', format_str)][-1]
        data_adcs = [int(s) for s in re.findall(r'\b\d+\b', adc_str)]
        
        # Update the local parameters
        self.logger.debug(funcname + ': format:' + str(data_format) + ' adcs:' + str(data_adcs))
        self.data_format = data_format
        self.init_data_format_functions()
        self.flag_adcs = data_adcs
        
        
    def start_converting_raw_data(self):
        """


        Starting a thread to convert the raw data


        """
        funcname = self.__class__.__name__ + '.start_converting_raw_data()'
        self.logger.debug(funcname)
        deque = collections.deque(maxlen=self.dequelen)
        self.deques_raw_serial.append(deque)
        # Adding a stream with all ltcs
        timevar = pymqdatastream.StreamVariable('time','seconds','float')
        packetvar = pymqdatastream.StreamVariable('packet','number','int')
        variables = [packetvar,timevar]
        
        for ad in self.flag_adcs:
            datavar = pymqdatastream.StreamVariable('ad ' + str(ad),'V','float')
            variables.append(datavar)

        name = 'sam4log'
        self.add_pub_stream(socket = self.sockets[-1],name=name,variables=variables)
        self.logger.debug(funcname + ': Starting thread')
        streams = self.Streams[-1:]
        # Analyse data format, choose the right conversion functions and start a conversion thread
        self.init_data_format_functions()

        self.convert_thread = threading.Thread(target=self.convert_raw_data,args = (deque,streams))
        self.convert_thread.daemon = True
        self.convert_thread.start()            
        self.logger.debug(funcname + ': Starting thread done')

        
    def convert_raw_data_format0(self, deque, streams, dt = 0.5):
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
                    else:
                        self.logger.debug(funcname + ': no a valid format 0 string:')


            # Push the read data
            ti = time.time()
            
            if(len(data0)>0):
                streams[0].pub_data(data0)
                self.intraqueue.appendleft(data0)
                #data_dict0 = {'time':ti,'data':data0}
                #data_json0 = json.dumps(data_dict0).encode('utf-8')
                #streams[0].deque.appendleft(data_json0)
                #streams[0].push_substream_data()


    def convert_raw_data_format2(self, deque, streams, dt = 0.5):
        """

        Converts raw data of the format 2, which is popped from the deque
        given as argument 

        """
        funcname = self.__class__.__name__ + '.convert_raw_data_format2()'
        self.logger.debug(funcname)
        ad0_converted = 0
        data_str = ''
        while True:
            #logger.debug(funcname + ': converted: ' + str(ad0_converted))
            time.sleep(dt)
            data_stream = []
            while(len(deque) > 0):
                data = deque.pop()
                data_str += data
                # Get commands first
                for i,me in enumerate(re.finditer(r'[><][><][><].*\n',data_str)):
                    print('COMMAND!',i)
                    print(me)
                    print(me.group(0))
                    print(me.span(0))
                    self.commands.append(me.group(0))
                    
            data_split = data_str.rsplit(b'\x00')
            if(len(data_split) > 0):
                if(len(data_split[-1]) == 0): # The last byte was a 0x00
                   data_str = ''
                else:
                   data_str = data_split[-1]

                for data_cobs in data_split:
                    #print('Cobs data:')
                    #print(data_cobs)
                    try:
                        data_decobs = cobs.decode(data_cobs)
                        #self.logger.debug(funcname + ': ' + data_decobs.encode('hex_codec'))
                        if(len(data_cobs) > 3):
                            packet_ident    = ord(data_decobs[0])
                            #self.logger.debug(funcname + ': packet_ident ' + str(packet_ident))
                            if(packet_ident == 0xad):
                                packet_flag_ltc = ord(data_decobs[1])
                                num_ltcs        = bin(packet_flag_ltc).count("1")
                                packet_size = 5 + 8 + 8 + num_ltcs * 3
                                packet_com_ltc0 = ord(data_decobs[2])
                                packet_com_ltc1 = ord(data_decobs[3])
                                packet_com_ltc2 = ord(data_decobs[4])
                                ind = 5
                                #self.logger.debug(funcname + ': ltc flag ' + str(packet_flag_ltc))
                                #self.logger.debug(funcname + ': Num ltcs ' + str(num_ltcs))
                                #self.logger.debug(funcname + ': packet_size ' + str(packet_size))
                                #self.logger.debug(funcname + ': len(data_cobs) ' + str(len(data_cobs)))
                                if(len(data_cobs) >= packet_size):
                                        packet_num_bin  = data_decobs[ind:ind+8]
                                        packet_num      = int(packet_num_bin.encode('hex'), 16)
                                        ind += 8
                                        packet_time_bin  = data_decobs[ind:ind+8]
                                        packet_time     = int(packet_time_bin.encode('hex'), 16)/10000.0
                                        data_packet = [packet_num,packet_time]
                                        ind += 8
                                        #self.logger.debug(funcname + ': Packet number: ' + packet_num_bin.encode('hex_codec'))
                                        #self.logger.debug(funcname + ': Packet 10khz time ' + packet_time_bin.encode('hex_codec'))                                        
                                        for i in range(0,num_ltcs*3,3):
                                            data_ltc = data_decobs[ind+i:ind+i+3]
                                            data_ltc += chr(int('88',16))
                                            if(len(data_ltc) == 4):
                                                conv = ltc2442.convert_binary(data_ltc,ref_voltage=4.096)
                                                data_packet.append(conv['V'][0])
                                            else:
                                                data_packet.append(9999.99)

                                        data_stream.append(data_packet)
                                        
                    except cobs.DecodeError:
                        self.logger.debug(funcname + ': COBS DecodeError')
                        pass
        
            if(len(data_stream)>0):
                streams[0].pub_data(data_stream)
                self.intraqueue.appendleft(data_stream)
                #print(data_stream)
            

                
if __name__ == '__main__':
    s = sam4logDataStream(logging_level='DEBUG')
    s.add_serial_device('/dev/ttyUSB0')
    
    s.add_raw_data_stream()
    #s.load_file('netstring_format1.log')

    # Send a format 2 command
    time.sleep(0.5)
    s.init_sam4logger(flag_adcs = [0,2,4],data_format=2)
    s.query_sam4logger()
    time.sleep(0.5)
    #s.print_serial_data = True    
    s.start_converting_raw_data()    
    print(s.get_info_str('short'))
    while(True):
        #print('Raw bytes read ' + str(s.bytes_read))
        #print(s.get_info_str('short'))
        time.sleep(5)
    
