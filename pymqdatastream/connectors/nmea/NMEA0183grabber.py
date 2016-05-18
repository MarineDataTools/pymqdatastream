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
import datetime
import collections
import time

logger = logging.getLogger('NMEA0183_service')
logger.setLevel(logging.DEBUG)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


class NMEA0183Grabber(object):
    """
    """
    def __init__(self):
        """
        """
        funcname = self.__class__.__name__ + '.__init__()'
        self.dequelen = 10000
        logger.debug(funcname)
        self.serial      = []
        self.datafiles   = []        
        self.deques      = []

        
    def add_serial_device(self,port,baud=4800):
        """
        """
        funcname = self.__class__.__name__ + '.add_serial_device()'
        try:
            logger.debug(funcname + ': Opening: ' + port)            
            serial_dict = {}
            serial_dict['sentences_read'] = 0
            serial_dict['device']       = serial.Serial(port,baud)
            serial_dict['thread_queue'] = queue.Queue()
            serial_dict['thread']       = threading.Thread(target=self.read_nmea_sentences,args = (serial_dict,))
            serial_dict['thread'].daemon = True
            serial_dict['thread'].start()
            self.serial.append(serial_dict)
        except Exception as e:
            logger.debug(funcname + ': Exception: ' + str(e))            
            logger.debug(funcname + ': Could not open device at: ' + str(port))


    def read_nmea_sentences(self, serial_dict):
        """
        The polling thread
        input:
        serial_device: 
        thread_queue: For stopping the thread
        """
        
        funcname = self.__class__.__name__ + '.read_nmea_sentences()'
        serial_device = serial_dict['device']
        thread_queue = serial_dict['thread_queue']
        nmea_sentence = ''
        got_dollar = False                            
        while True:
            time.sleep(0.05)
            while(serial_device.inWaiting()):
                try:
                    value = serial_device.read(1).decode('utf-8')
                    nmea_sentence += value
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
                        for deque in self.deques:
                            deque.appendleft(nmea_data)
                            
                        nmea_sentence = ''
                        serial_dict['sentences_read'] += 1

                except Exception as e:
                    logger.debug(funcname + ':Exception:' + str(e))

                    
            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                logger.debug(funcname + ': Got data:' + data)
                break
            except queue.Empty:
                pass
                    
        return True


    def add_file_to_save(self,filename, style = 'all'):
        """
        Adds a file to save the data to
        """
        
        funcname = self.__class__.__name__ + '.add_file_to_save()'
        
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
            logger.debug(funcname + ': opened file: ' + filename)
            return datafile_dict['datafile']
        except Exception as e:
            logger.warning(funcname + ': Excpetion: ' + str(e))
            return None

            
    def close_file_to_save(self,datafile):
        """
        Closes the thread and the file to save data to
        input: datafile: can be either an integer or a file object 
        """
        funcname = self.__class__.__name__ + '.close_file_to_save()'
        if(isinstance(datafile,int)):
            ind_datafile = datafile
            logger.debug(funcname + ': got ind, thats easy' )
            found_file = True
        elif(isinstance(datafile,file)):
            logger.debug(funcname + ': File object, searching for the file' )
            found_file = False
            for ind_datafile,dfile in enumerate(self.datafiles):
                if(dfile['datafile'] == datafile):
                    logger.debug(funcname + ': Found file object at index:' + str(ind_datafile))
                    found_file = True
                    break

        if(found_file):
            # Closing thread by sending something to it
            self.datafiles[ind_datafile]['thread_queue'].put('stop')
            # Waiting for closing
            time.sleep(0.05)
        

    def save_nmea_sentences(self,datafile, deque, thread_queue, style):
        """
        Saves the nmea into a file
        """
        funcname = self.__class__.__name__ + '.save_nmea_sentences()'
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
            if(ct >= 10): # Sync the file every now and then
                ct = 0
                logger.debug(funcname + ': flushing')
                datafile.flush()
            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                logger.debug(funcname + ': Got data:' + data)
                datafile.close()
                break
            except queue.Empty:
                pass

    def log_data_in_files(self, filename, time_interval):
        """
        Creates every time_interval a new file and logs the data to it
        input:
        filename: 
        time_interval: datetime.timedelta object, default: datetime.timedelta(hours=1)
        """
        funcname = self.__class__.__name__ + '.log_data_in_files()'
        logger.debug(funcname)
        thread_queue = queue.Queue()
        self.time_thread = threading.Thread(target=self.time_interval_thread, args = (filename,time_interval,thread_queue))
        self.time_thread.daemon = True
        self.time_thread.start()

    def time_interval_thread(self,filename,time_interval,thread_queue):
        """
        """
        funcname = self.__class__.__name__ + '.time_interval_thread()'
        dt = 0.05
        logger.debug(funcname)
        now = datetime.datetime.now()
        filename_time = now.strftime(filename + '%Y.%m.%d__%H.%M.%S.log')
        datafile = self.add_file_to_save(filename_time)
        tstart = now
    
        while True:
            now = datetime.datetime.now()                        
            if((now - tstart) > time_interval):
                tstart = now            
                logger.debug(funcname + ': Creating new file')
                self.close_file_to_save(datafile)
                filename_time = now.strftime(filename + '%Y.%m.%d__%H.%M.%S.log')
                datafile = self.add_file_to_save(filename_time)
                time.sleep(dt)

            # Try to read from the queue, if something was read, quit
            try:
                data = thread_queue.get(block=False)
                logger.debug(funcname + ': Got data:' + data)
                datafile.close()
                break
            except queue.Empty:
                pass
        
        
def main():
    s = NMEA0183Grabber()
    s.add_serial_device('/dev/ttyUSB0')
    s.log_data_in_files('nmea_test__',datetime.timedelta(seconds=10))
    while(True):
        time.sleep(1.0)


if __name__ == "__main__":
    main()


