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

        self.print_serial_data = False
        self.serial_thread_queue = queue.Queue()
        self.serial_thread_queue_ans = queue.Queue()
        self.bytes_read = 0
        self.serial = None # The device to be connected to
        self.deques_raw_serial = [collections.deque(maxlen=self.dequelen)]
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

            
    def read_serial_data(self, dt = 0.005):
        """

        The serial data polling thread

        Args:
            dt: Sleeping time between polling [default 0.005]

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
        deque = self.deques_raw_serial[0]
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
        if(self.data_format == 0):
            self.convert_raw_data = self.convert_raw_data_format0

        if(self.data_format == 2):
            self.convert_raw_data = self.convert_raw_data_format2


    def init_sam4logger(self,flag_adcs):
        """
    
        Function to set specific settings on the logger
        Args:
            flag_adcs: List of the ltc2442 channels to be send back [e.g. [0,2,7]], has to be between 0 and 7
        
        """
        
        self.print_serial_data = True        
        self.send_serial_data('stop\n')
        time.sleep(0.1)
        self.flag_adcs = flag_adcs
        cmd = 'send ad'
        for ad in self.flag_adcs:
            cmd += ' %d' %ad
        self.send_serial_data(cmd + '\n')
        time.sleep(0.1)
        s.send_serial_data('format 2\n')
        time.sleep(0.1)
        self.data_format = 2
        time.sleep(5.0)        
        self.send_serial_data('start\n')
        self.print_serial_data = False

                
                
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
        
        
    def convert_raw_data_old(self, deque, streams, dt = 0.05):
        """
        Converts raw data which is popped from the deque given as argument
        """
        funcname = self.__class__.__name__ + '.convert_raw_data()'
        self.logger.debug(funcname)
        ad0_converted = 0
        data_str = ''
        while True:
            #logger.debug(funcname + ': converted: ' + str(ad0_converted))
            time.sleep(dt)
            data0 = []
            data1 = []            
            while(len(deque) > 0):
                data = deque.pop()
                #data_str += data.decode('utf8')
                data_str += data
                #logger.debug(funcname + ': str: ' + str(data_str))  
                [data_str,data_netstr] = netstring.get_netstring(data_str)
                #logger.debug(funcname + ': raw: ' + str(data_str))
                #logger.debug(funcname + ': net: ' + str(data_netstr))
                for n,d_netstr in enumerate(data_netstr):
                    # Test if netstring cont
                    d_split = d_netstr.split('>')
                    packet_format = d_split[0]
                    datasets = d_split[1].split(';')
                    timer10khz = int(datasets[0],16)
                    timer_seconds = timer10khz / 10000.0
                    ltc0 = datasets[2]
                    ltc1 = datasets[3]
                    bin_data0 = ''
                    bin_data1 = ''
                    try:
                        bin_data0 += chr(int(ltc0[0:2],16))
                        bin_data0 += chr(int(ltc0[2:4],16))
                        bin_data0 += chr(int(ltc0[4:6],16))
                        bin_data0 += chr(int('88',16))
                        bin_data1 += chr(int(ltc1[0:2],16))
                        bin_data1 += chr(int(ltc1[2:4],16))
                        bin_data1 += chr(int(ltc1[4:6],16))
                        bin_data1 += chr(int('88',16))
                        data_rec0 = ltc2442.convert_binary(bin_data0,ref_voltage=4.096)
                        data_rec1 = ltc2442.convert_binary(bin_data1,ref_voltage=4.096)                    
                        #logger.debug(funcname + ': ' + str(packet_format) + ' d:' + str(datasets))
                        #logger.debug(funcname + ': timer: ' + str(timer10khz) + ' V:' + str(data_rec0))

                        data_tmp = [timer_seconds,data_rec0['V'][0]]
                        data0.append(data_tmp)
                        data_tmp = [timer_seconds,data_rec1['V'][0]]
                        data1.append(data_tmp)
                        ad0_converted += 1
                    except Exception as e:
                        self.logger.debug(funcname + ': Exception:' + str(e))



            ti = time.time()
            
            if(len(data0)>0):
                #data_dict0 = {'time':ti,'data':data0}
                #data_json0 = json.dumps(data_dict0).encode('utf-8')
                streams[0].pub_data(data0)

            if(len(data1)>0):                
                #data_dict1 = {'time':ti,'data':data1}
                #data_json1 = json.dumps(data_dict1).encode('utf-8')            
                streams[0].pub_data(data1)                


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
                        d_split = nstr.split('\n')
                        d_split0 = d_split[0].split(';')
                        timer10khz = float(d_split0[0][2:])
                        timer_seconds = timer10khz / 10000.0
                        channel = int(d_split0[1])
                        cnv_speed = int(d_split0[2])
                        data_V = float(d_split[1].split(';')[2])
                        data_tmp = [timer_seconds,data_V]
                        data0.append(data_tmp)            
                    else:
                        self.logger.debug(funcname + ': no a valid format 0 string:')


            # Push the read data
            ti = time.time()
            
            if(len(data0)>0):
                streams[0].pub_data(data0)
                print(data0)
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
                    if(len(data_cobs) > 17):
                        try:
                            data_decobs = cobs.decode(data_cobs)
                            print(len(data_decobs))
                            packet_ident    = data_decobs[0]
                            packet_num_bin  = data_decobs[1:9]
                            packet_num      = int(packet_num_bin.encode('hex'), 16)
                            packet_time_bin  = data_decobs[9:17]
                            packet_time     = int(packet_time_bin.encode('hex'), 16)/10000.0
                            packet_flag_ltc = ord(data_decobs[17])
                            num_ltcs        = bin(packet_flag_ltc).count("1")

                            data_packet = [packet_num,packet_time]
                            print(data_decobs.encode('hex_codec'))
                            print(packet_num_bin.encode('hex_codec'))
                            print(packet_time_bin.encode('hex_codec'))
                            print(packet_flag_ltc)
                            print(num_ltcs)
                            for i in range(0,num_ltcs*3,3):
                                data_ltc = data_decobs[18+i:18+i+3]
                                print(data_ltc.encode('hex_codec'))
                                data_ltc += chr(int('88',16))
                                conv = ltc2442.convert_binary(data_ltc,ref_voltage=4.096)
                                data_packet.append(conv['V'][0])

                            data_stream.append(data_packet)
                            print(data_packet)
                        except cobs.DecodeError:
                            print('DecodeError')
                            pass
        
            if(len(data_stream)>0):
                streams[0].pub_data(data_stream)
            

                
if __name__ == '__main__':
    s = sam4logDataStream()
    s.add_serial_device('/dev/ttyUSB0')
    #s.print_serial_data = True
    s.add_raw_data_stream()
    #s.load_file('netstring_format1.log')

    # Send a format 2 command
    time.sleep(0.5)
    s.init_sam4logger(flag_adcs = [0,2,4])
    time.sleep(0.5)
    s.start_converting_raw_data()    
    print(s.get_info_str('short'))
    while(True):
        #print('Raw bytes read ' + str(s.bytes_read))
        #print(s.get_info_str('short'))
        time.sleep(5)
    
