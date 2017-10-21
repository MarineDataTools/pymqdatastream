#!/usr/bin/env python3
import sys
import os
import pymqdatastream
import pymqdatastream.connectors.todl.netstring as netstring
import pymqdatastream.connectors.todl.ltc2442 as ltc2442
import pymqdatastream.connectors.todl.data_packages as data_packages
from pymqdatastream.utils.utils_serial import serial_ports, test_serial_lock_file, serial_lock_file
import logging
try:
    import queue as queue # python 3
except:
    import Queue as queue # python 2.7
import threading
import serial
import socket
import collections
import time
import json
import re
from cobs import cobs
import numpy as np
import datetime
import netCDF4 # For loading and saving files
import argparse
import traceback # For debugging purposes
import sys

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqds_todl')
logger.setLevel(logging.DEBUG)


# TODL speeds for version 0.4
s4lv0_4_speeds        = [30   ,12 ,10 ,8  ,6  ,4   ,2   ]
s4lv0_4_speeds_hz_adc = [6.875,110,220,439,879,1760,3520]
s4lv0_4_speeds_td     = [2000 ,100,25 ,50 ,20 ,16  ,16  ]
s4lv0_4_speeds_hz     = []
s4lv0_4_tfreq         = 10000.0
for i,speed in enumerate(s4lv0_4_speeds):
    s4lv0_4_speeds_hz.append(s4lv0_4_tfreq/s4lv0_4_speeds_td[i])



s4lv0_45_speeds_hz    = [10, 25, 50, 100, 200, 400, 715, 1250, 2000, 3300]
s4lv0_46_speeds_hz    = [2, 5, 10, 25, 50, 100, 200, 250, 333, 400, 500, 625, 1000, 1250, 2000]
s4lv0_75_speeds_hz    = [2, 5, 10, 25, 50, 100, 200, 400, 500, 625, 1000, 1250, 2000]

file_header_valid = b'\n>>>'
file_header_start_todl = b'>>> -- HELLO! This is the Turbulent Ocean Data Logger (TODL) -- <<<'
file_header_start_sam4log = b'>>> -- HELLO! This is SAM4LOG -- <<<' # Before 13.08.2017 the TODL project name was SAM4LOG
file_header_valid_dos = b'\r\n>>>'


file_header_end = b'# File Header End\n'

def parse_device_info(data_str):
    """

    Parses a device info string and returns an dictionary with todl device configuration
    Args:
    data_str: String with the device information
    Returns: device_info

    """
    funcname = __name__ + '.parse_device_info()'
    logger.debug(funcname)
    device_info = {}
    # Pre-initialise some things
    device_info['adcs'] = None
    
    boardversion = '??'
    firmwareversion = '??'
    print(data_str)
    for line in data_str.split('\n'):
        if( ' board version:' in line ):
            # Expecting a string like this:
            # >>> --  board version: 9.00 --
            boardversion = line.rsplit(': ')
            try:
                boardversion = boardversion[1].split(' --')[0]
            except:                    
                logger.debug(funcname + ': No valid version string')

        elif( 'firmware version:' in line ):
            # Expecting a string like this:
            # >>> --  firmware version: 0.30 --
            firmwareversion = line.rsplit(': ')
            try:
                firmwareversion = firmwareversion[1].split(' --')[0]
            except:
                logger.debug(funcname + ': No valid version string')
            logger.debug('Firmware version:' + str(firmwareversion))


    device_info['board'] = boardversion
    device_info['firmware'] = firmwareversion                            
    #print(data_str)
    #print('Data str:' + data_str)
    # Parse the data
    #print('Info is')
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

    #
    #
    # Get the RTC time
    #
    #
    # >>>Time: 2017.09.11 10:06:44
    device_info['time_str']   = ''
    device_info['time']   = None
    for i,me in enumerate(re.finditer(r'>>>Time:.*\n',data_str)):
        time_str = me.group()        

    if(len(time_str) > 0):
        time_str = time_str.replace('\n','')  
        print('Time string:',time_str)
        device_info['time_str']   = time_str
        
    try:
        device_info['time']   = datetime.datetime.strptime(time_str, '>>>Time: %Y.%m.%d %H:%M:%S')
    except Exception as e:
        logger.debug(funcname + ':' + str(e))
        device_info['time'] = None
        
    freq_str = ''
    for i,me in enumerate(re.finditer(r'>>>Freqs:.*\n',data_str)):
        freq_str = me.group()

    #
    # Get the counters
    #
    # >>>10kHz cnt: 149347
    # >>>32kHz cnt: 489396
    device_info['cnt10k_str']   = ''
    device_info['cnt10k']       = None
    device_info['cnt32k_str']   = ''
    device_info['cnt32k']       = None
    
    for i,me in enumerate(re.finditer(r'>>>10kHz cnt:.*\n',data_str)):
        cnt10k_str = me.group()

    for i,me in enumerate(re.finditer(r'>>>32kHz cnt:.*\n',data_str)):
        cnt32k_str = me.group()

    device_info['cnt10k_str'] = cnt10k_str
    cnt10k = [int(s) for s in re.findall(r'\b\d+\b', cnt10k_str)][-1]
    device_info['cnt10k'] = cnt10k
    device_info['cnt32k_str'] = cnt32k_str
    cnt32k = [int(s) for s in re.findall(r'\b\d+\b', cnt32k_str)][-1]
    device_info['cnt32k'] = cnt32k    

    #
    # Get the sampling frequencies
    #
    #>>>Freqs:ADCs: 100, IMU: 5
    if(len(freq_str) > 0):
        freq_str = freq_str.replace('>>>Freqs:','')
        freq_str = freq_str.replace('\n','')
        # Check for frequencies (ADC)
        if('ADCs' in freq_str):
            ind1 = freq_str.find('ADCs:')
            ind2 = freq_str[ind1:].find(',')
            adcs_freq = float(freq_str[ind1 + 5 : ind2+ind1])
        else:
            adcs_freq = np.NaN
        # Check for frequencies (IMU)
        if('IMU' in freq_str):
            ind1 = freq_str.find('IMU:')
            ind2 = freq_str[ind1:].find(',')
            if(ind2 == -1): # End of line
                ind2 = len(freq_str[ind1:])
                
            imu_freq = float(freq_str[ind1 + 4 : ind2+ind1])
        else:
            imu_freq = np.NaN

        # Check for frequencies (PYRO)
        if('PYRO' in freq_str):
            ind1 = freq_str.find('PYRO:')
            ind2 = freq_str[ind1:].find(',')
            if(ind2 == -1): # End of line
                ind2 = len(freq_str[ind1:])            
            pyro_freq = float(freq_str[ind1 + 5 : ind2+ind1])
        else:
            pyro_freq = np.NaN            
            
            

    #print('Channel str:' + channel_str)
    speed_str = ''
    for i,me in enumerate(re.finditer(r'>>>speed:.*\n',data_str)):
        speed_str = me.group()                                            


    data_format = [int(s) for s in re.findall(r'\b\d+\b', format_str)][-1]
    data_adcs = [int(s) for s in re.findall(r'\b\d+\b', adc_str)]
    data_channel_seq = [int(s) for s in re.findall(r'\b\d+\b', channel_str)]
    speed_data = [float(s) for s in re.findall(r'\d+\.\d+', speed_str)]


    #print('Speed str:' + speed_str)
    #print('Speed data:' + str(speed_data))
    if(len(speed_data) == 0):
        speed_data = [-9999]
        
    device_info['info_str'] = data_str
    device_info['counterfreq'] = s4lv0_4_tfreq # TODO, this should come from the firmware
    device_info['format'] = data_format
    device_info['adcs'] = data_adcs
    device_info['adcs_freq'] = adcs_freq
    device_info['channel_seq'] = data_channel_seq
    device_info['speed_str'] = speed_str
    device_info['freq'] = speed_data[-1]
    device_info['freq_str'] = freq_str
    device_info['imu_freq'] = imu_freq
    device_info['pyro_freq'] = pyro_freq    
    # Create a list for each channel and fill it later with streams

    # Update the local parameters
    logger.debug(funcname + ': format:' + str(data_format) + ' adcs:' + str(data_adcs) + ' channel sequence:' + str(data_channel_seq))
    return device_info


def find_todl_header(data_file):
    """
    Reading the first part of the file and searching for a known pattern
    """
    funcname = __name__ + '.find_todl_header()'
    VALID_HEADER = False
    # Reading the first part of the file and looking for known patterns
    maxbytes = 10000 # should be larger as len(file_header_len)
    bytes_read = 0
    data = b''
    header = b'' # The header information data
    while True:
        bytes_read += 1
        if(bytes_read >= maxbytes):
            logger.warning(funcname + ': Could not read file')
            break

        b = data_file.read(1)
        data += b
        if(VALID_HEADER):
            header += b            
            # Check if we have a \n, if yes check the next three bytes for >>>
            if(b == b'\n'):
                d = data_file.read(3)
                data += d
                if(d != b'>>>'):
                    logger.debug(funcname + ': Stop of header')
                    break
                else:
                    header += d

        if(len(data) > len(file_header_start_sam4log)):
            if( data[-len(file_header_start_sam4log):] == file_header_start_sam4log ):
                logger.debug(funcname + ': Found a valid start header')
                header += data[-len(file_header_start_sam4log):]
                VALID_HEADER=True
        if(len(data) > len(file_header_start_todl)):                
            if (data[-len(file_header_start_todl):] == file_header_start_todl):
                logger.debug(funcname + ': Found a valid start header')
                header += data[-len(file_header_start_todl):]
                VALID_HEADER=True


    print('header',header)
    return [VALID_HEADER,header]


#
#
#
#
#
class todlnetCDF4File():
    """ A turbulent ocean data logger (TODL) netCDF4 file object. This object can open, read and convert files. TOD: In the bright future it should also stream data to a todl datastream ... 
    """

    def __init__(self,fname):
        funcname = self.__class__.__name__ + '.__init__()'
        self.logger = logger
        self.todl = todlDataStream()
        # This can also 
        self.todl.load_file(fname,start_read = False)
        # We have a device info now, lets create the netCDF4 groups
        print(self.todl.device_info)

        
    def create_ncfile(self,fname):
        """Creates a new netCDF4 File based on the device_info information of
        the available data

        Args:
           fname: Filename of the netcdffile to be created

        """
        funcname = self.__class__.__name__ + '.create_ncfile()'
        rootgrp = netCDF4.Dataset(fname, "w", format="NETCDF4")
        # Add the device information as an attribute
        rootgrp.device_info = self.todl.device_info['info_str']
        rootgrp.version  = pymqdatastream.__version__
        # Creating group for status information
        sgrp             = rootgrp.createGroup('stat')
        dimname          = 't'
        t_dim            = sgrp.createDimension(dimname, None)
        self.stat_tvar        = sgrp.createVariable(dimname, "f8", (dimname,))
        self.stat_tvar_tmp    = []
        self.stat_tvar.units  = 'time in seconds since device power on'
        self.stat_timevar     = sgrp.createVariable("time", "f8", (dimname,))
        self.stat_timevar_tmp = []
        
        if(self.todl.device_info['time'] == None):
            time_unit    = "0000.01.01 00:00:00"
        else:
            time_unit    = self.todl.device_info['time'].strftime('%Y-%m-%d 00:00:00')
            
        self.time_base = datetime.datetime.strptime(time_unit,"%Y-%m-%d %H:%M:%S")
        self.stat_timevar.units = 'time in seconds since ' + time_unit
        
        # Test if we have adcs
        if(self.todl.device_info['adcs'] is not None):
            self.logger.debug(funcname + ': Creating adc group')
            self.ncfile = rootgrp
            adcgrp     = rootgrp.createGroup('adc')
            ch_dims    = []
            self.adc_vars   = []
            self.adc_tvars  = []
            # For temporary storage of data, this is faster as a direct write to the ncfile
            self.adc_vars_tmp   = []
            self.adc_tvars_tmp  = []            
            # Creating up to four different time dimensions, to cover
            # all channels
            ch_seq = np.unique(np.asarray(self.todl.device_info['channel_seq']))
            self.ch_seq = ch_seq
            for nch,ch in enumerate(ch_seq):
                dimname = 't_ch' + str(ch)
                print(dimname)
                ch_dim = adcgrp.createDimension(dimname, None)
                ch_dim
                ch_dims.append(ch_dim)
                adc_tvar = adcgrp.createVariable(dimname, "f8", (dimname,))
                adc_tvar.units = 'time in seconds since device power on'
                self.adc_tvars.append(adc_tvar)
                self.adc_vars.append([])

                self.adc_tvars_tmp.append([])
                self.adc_vars_tmp.append([])
                
                # Creating variables
                for adc in self.todl.device_info['adcs']:
                    varname = 'V_adc' + str(adc) + '_ch' + str(ch)
                    adc_var = adcgrp.createVariable(varname, "f4", (dimname,))
                    self.adc_vars[nch].append(adc_var)
                    self.adc_vars_tmp[nch].append([])

        # Check if we have an IMU
        #if(self.todl.device_info['imu_freq'] > 0):
        if True:
            self.logger.debug(funcname + ': Creating imu group')
            imugrp     = rootgrp.createGroup('imu')
            dimname = 't_imu'
            imu_dim = imugrp.createDimension(dimname, None)
            self.imu_t    = imugrp.createVariable('t_imu', "f8", (dimname,))
            self.imu_t.units = 'time in seconds since device power on'
            self.imu_temp = imugrp.createVariable('temp', "f8", (dimname,))            
            self.imu_accx = imugrp.createVariable('accx', "f8", (dimname,))
            self.imu_accy = imugrp.createVariable('accy', "f8", (dimname,))
            self.imu_accz = imugrp.createVariable('accz', "f8", (dimname,))
            self.imu_gyrox = imugrp.createVariable('gyrox', "f8", (dimname,))
            self.imu_gyroy = imugrp.createVariable('gyroy', "f8", (dimname,))
            self.imu_gyroz = imugrp.createVariable('gyroz', "f8", (dimname,))
            self.imu_magx = imugrp.createVariable('magx', "f8", (dimname,))
            self.imu_magy = imugrp.createVariable('magy', "f8", (dimname,))
            self.imu_magz = imugrp.createVariable('magz', "f8", (dimname,))
            self.imu_t_tmp     = []
            self.imu_temp_tmp  = []            
            self.imu_accx_tmp  = []
            self.imu_accy_tmp  = []
            self.imu_accz_tmp  = []
            self.imu_gyrox_tmp = []
            self.imu_gyroy_tmp = []
            self.imu_gyroz_tmp = []
            self.imu_magx_tmp = []
            self.imu_magy_tmp = []
            self.imu_magz_tmp = []


        # Or a Pyroscience Firesting?
        if(self.todl.device_info['pyro_freq'] > 0):
            self.logger.debug(funcname + ': Creating pyro group')
            pyrogrp     = rootgrp.createGroup('pyro')
            self.pyrogrp = pyrogrp
            dimname = 't_pyro'
            pyro_dim = pyrogrp.createDimension(dimname, None)
            self.pyro_t        =  pyrogrp.createVariable('t_pyro', "f8", (dimname,))
            self.pyro_t.units = 'time in seconds since device power on'            
            self.pyro_t_tmp    = []
            self.pyro_phi      =  pyrogrp.createVariable('phi',    "f8", (dimname,))
            self.pyro_phi_tmp  = []
            self.pyro_umol     =  pyrogrp.createVariable('umol',   "f8", (dimname,))
            self.pyro_umol_tmp = []
            
            
    def to_ncfile_fast(self,fname, num_bytes = 1000000):
        """ Reads the data in fname, converts and puts it into a ncfile

        Args:
           fname: Filename
           num_bytes: num_bytes to read per conversion step
        """
        funcname = 'to_ncfile_fast()'
        # First create a netCDF4 File
        num_good = 0
        num_err = 0
        self.create_ncfile(fname)
        self.todl.device_info['format']
        bytes_read = 0
        cnt = 0
        data_str = b''
        tmpcnt = 1
        #while(tmpcnt):        
        while(True):
            tmpcnt -= 1
            raw_data = self.todl.data_file.read(num_bytes)
            bytes_read += len(raw_data)
            # If we have the end of file
            if(len(raw_data) == 0):
                self.file_status = 2
                # create interpolated time variables using Stat
                if(len(self.stat_tvar) > 0):
                    t    = self.stat_tvar[:]
                    time = self.stat_timevar[:]
                    if(self.todl.device_info['pyro_freq'] > 0):
                        self.pyro_time        = self.pyrogrp.createVariable('time', "f8", ('t_pyro',))
                        self.pyro_time.units  = self.stat_timevar.units
                        self.pyro_time[:]     = np.interp(self.pyro_t[:],t,time)

                # TODO: make it proper
                if(self.todl.device_info['adcs'] is not None):
                    for nch,ch in enumerate(self.ch_seq):
                        self.adc_tvars[nch] = self.adc_tvars_tmp[nch][:]


                # DONE!
                self.logger.debug(funcname + ': EOF')
                return True            

            # This is the only crucial part where we should check what format we have
            data_str += raw_data
            if(len(data_str) > 17):
                print('len',len(data_str))
                [data_packets,data_str] = data_packages.decode_format4(data_str,self.todl.device_info)
                err_packet = data_packets[-1]
                num_good += err_packet['num_good']
                num_err += err_packet['num_err']                

            # Read the data into temporary buffer
            for data in data_packets:
                cnt += 1
                if(np.mod(cnt,1000) == 0):
                    print(str(cnt) + ' data packages converted and ' + str(bytes_read) + ' bytes read',num_good,num_err,err_packet)

                if(data['type'] == 'Stat'): # Status packet
                    self.stat_tvar_tmp.append(data['t'])
                    dt = data['date'] - self.time_base
                    self.stat_timevar_tmp.append(dt.total_seconds())

                elif(data['type'] == 'L'): # ADC data
                    try:
                        ind = np.squeeze(np.where(self.ch_seq == data['ch'])[0])
                        self.adc_tvars_tmp[ind].append(data['t'])
                        # Put the voltage data into the variable
                        for nadc,adc in enumerate(self.todl.device_info['adcs']):
                            self.adc_vars_tmp[ind][nadc].append(data['V'][nadc])

                    except Exception as e:
                        self.logger.debug(funcname + ':Exception:' + str(e))                            
                        
                elif(data['type'] == 'A'): # IMU data
                    self.imu_t_tmp.append(data['t'])
                    self.imu_temp_tmp.append(data['T'])                    
                    self.imu_accx_tmp.append(data['acc'][0])
                    self.imu_accy_tmp.append(data['acc'][1])
                    self.imu_accz_tmp.append(data['acc'][2])
                    self.imu_gyrox_tmp.append(data['gyro'][0])
                    self.imu_gyroy_tmp.append(data['gyro'][1])
                    self.imu_gyroz_tmp.append(data['gyro'][2])
                    self.imu_magx_tmp.append(data['mag'][0])
                    self.imu_magy_tmp.append(data['mag'][1])
                    self.imu_magz_tmp.append(data['mag'][2])

                elif(data['type'] == 'O'): # Pyro Firesting data
                    self.pyro_t_tmp.append(data['t'])
                    self.pyro_phi_tmp.append(data['phi'])
                    self.pyro_umol_tmp.append(data['umol'])       
                    

            # Writing data to ncfile
            print('Writing to netCDF')
            # Status information
            n = len(self.stat_tvar)
            m = len(self.stat_tvar_tmp)
            self.stat_tvar[n:n+m] = self.stat_tvar_tmp[:]
            self.stat_tvar_tmp = []
            self.stat_timevar[n:n+m] = self.stat_timevar_tmp[:]
            self.stat_timevar_tmp = []
            # ADCS
            for nch,ch in enumerate(self.ch_seq):
                n = len(self.adc_tvars[nch])
                m = len(self.adc_tvars_tmp[nch][:])
                self.adc_tvars[nch][n:n+m] = self.adc_tvars_tmp[nch][:]
                self.adc_tvars_tmp[nch] = [] # Clear again
                for nadc,adc in enumerate(self.todl.device_info['adcs']):
                    self.adc_vars[nch][nadc][n:n+m] = self.adc_vars_tmp[nch][nadc][:]
                    self.adc_vars_tmp[nch][nadc] = [] # Clear again

                    
            if(self.todl.device_info['imu_freq'] > 0):
                m = len(self.imu_t_tmp)                
                n = len(self.imu_t)
                print(self.imu_accx_tmp[:])
                self.imu_t[n:n+m]     = self.imu_t_tmp[:]
                self.imu_temp[n:n+m]  = self.imu_temp_tmp[:]
                self.imu_accx[n:n+m]  = self.imu_accx_tmp[:]
                self.imu_accy[n:n+m]  = self.imu_accy_tmp[:]
                self.imu_accz[n:n+m]  = self.imu_accz_tmp[:]
                self.imu_gyrox[n:n+m] = self.imu_gyrox_tmp[:]
                self.imu_gyroy[n:n+m] = self.imu_gyroy_tmp[:]
                self.imu_gyroz[n:n+m] = self.imu_gyroz_tmp[:]
                self.imu_magx[n:n+m] = self.imu_magx_tmp[:]
                self.imu_magy[n:n+m] = self.imu_magy_tmp[:]
                self.imu_magz[n:n+m] = self.imu_magz_tmp[:]
                # Clear the lists                
                self.imu_t_tmp = []
                self.imu_temp_tmp = []
                self.imu_accx_tmp = []
                self.imu_accy_tmp = []
                self.imu_accz_tmp = []
                self.imu_gyrox_tmp = []
                self.imu_gyroy_tmp = []
                self.imu_gyroz_tmp = []
                self.imu_magx_tmp = []
                self.imu_magy_tmp = []
                self.imu_magz_tmp = []

            if(self.todl.device_info['pyro_freq'] > 0):
                m = len(self.pyro_t_tmp)                
                n = len(self.pyro_t)                
                self.pyro_t[n:n+m]        = self.pyro_t_tmp[:]
                self.pyro_phi[n:n+m]      = self.pyro_phi_tmp[:]
                self.pyro_umol[n:n+m]     = self.pyro_umol_tmp[:]
                # Clear the lists
                self.pyro_t_tmp    = [] 
                self.pyro_phi_tmp  = []
                self.pyro_umol_tmp = []
                
            
            
        
    def close(self):
        self.ncfile.close()        
        
        
#       
#
#
# The datastream
#
#
#
class todlDataStream(pymqdatastream.DataStream):
    """The Turbulent Ocean Data Logger (TODL) object.

    """
    def __init__(self, **kwargs):
        """
        """
        super(todlDataStream, self).__init__(**kwargs)
        uuid = self.uuid
        uuid.replace('DataStream','todlDataStream')
        self.name = 'todl'
        self.uuid = uuid
        self.status = -1 # -1 init, 0 opened serial port, 1 converting
        self.file_status = -1 # -1 not opened, 0 = open, 1 = reading, 2 = end of file
        self.init_notification_functions = [] # A list of functions to be called after the logger has been initialized/reinitialized
        funcname = self.__class__.__name__ + '.__init__()'
        self.logger.debug(funcname)
        self.dequelen = 10000 # Length of the deque used to store data
        self.flag_adcs = [] # List of adcs to be send by the logger hardware
        self.device_info = {}
        self.print_serial_data = False
        self.raw_data_ondemand_queue = queue.Queue() # Queue used for on-demand raw_data, used at the moment for read_file_data
        self.serial_thread_queue = queue.Queue()
        self.serial_thread_queue_ans = queue.Queue()

        self.bytes_read = 0
        self.bytes_read_avg = 0 # Average bytes received per time interval of 10 seconds
        self.bytes_read_avg_dt = 2 # Average bytes received per time interval of 10 seconds
        self.serial = None # The device to be connected to
        # Two initial queues, the first is for internal use (init logger, query_todl), the second is for the raw stream
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
        # A list for other channels (TODO make this clean)
        self.aux_streams = None        
        self.commands = []

        # The data format
        self.device_info['format'] = 0

        # Adding a publish socket
        self.add_pub_socket()


    def load_file(self,filename,dt=0.01,num_bytes=200,start_read=True):
        """Loads a file and reads it chunk by chunk

        """
        VALID_HEADER=False        
        funcname = self.__class__.__name__ + '.load_file()'
        self.bytes_read = 0
        self.data_file = open(filename,'rb')
        [VALID_HEADER,data] = find_todl_header(self.data_file)


        if(VALID_HEADER):
            data_str = data.decode('utf-8')
            self.device_info = parse_device_info(data_str)
            self.channel_streams = [None] * (max(self.device_info['channel_seq']) + 1)
            self.init_data_format_functions()
            self.flag_adcs = self.device_info['adcs']
            self.file_status = 0 # File open
        else:
            return False

        self.logger.debug(funcname + ': Starting thread')
        if(start_read):
            self.start_read_file(dt,num_bytes)

        return True
    
    
    def start_read_file(self,dt=0.01,num_bytes=200, ondemand=False):
        funcname = self.__class__.__name__ + '.start_read_file()'
        if(self.file_status == 0):
            self.file_thread = threading.Thread(target=self.read_file_data,kwargs={'dt':dt,'num_bytes':num_bytes,'ondemand':ondemand})
            self.file_thread.daemon = True
            self.file_thread.start()            
            self.logger.debug(funcname + ': Starting thread done')
            self.file_status = 1 # Reading
        else:
            self.logger.warning(funcname + ': Either file not open or file is already reading')


    def stop_read_file(self):
        funcname = self.__class__.__name__ + '.stop_read_file()'        
        self.serial_thread_queue.put('stop')
        self.file_status = 0 # File open
        

    def close_file(self):
        funcname = self.__class__.__name__ + '.close_file()'
        self.stop_read_file()
        self.file_status = -1 # File closed
        
        
    def read_file_data(self, dt = 0.01, num_bytes = 200, ondemand=False):
        """

        The function which reads the file
        Args:
            dt: wait [s] between consecutive reads
            num_bytes: read num bytes per dt
            ondemand: waits for a piece of data at the self.raw_data_ondemand_queue queue, if got something continues sending data, convert data functions can put data on the self.raw_data_ondemand_queue queue to ask for new data

        """
        funcname = self.__class__.__name__ + '.read_serial_data()'
        self.logger.debug(funcname)
        while True:
            if(dt > 0):
                time.sleep(dt)

            if(ondemand):
                response = self.raw_data_ondemand_queue.get()

            if True:
                try:
                    data = self.data_file.read(num_bytes)
                    # If we have the end of file
                    if(len(data) == 0):
                        self.file_status = 2
                        self.logger.debug(funcname + ': EOF')
                        return True
                    
                    #self.bytes_read += num_bytes
                    self.bytes_read += len(data)
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
                    
        self.logger.debug(funcname + ': done_exiting')
        return True                    

        
    def add_serial_device(self,port,baud=921600):
        """
        """
        funcname = self.__class__.__name__ + '.add_serial_device()'
        try:
            self.logger.debug(funcname + ': Opening: ' + port)
            self.bytes_read = 0
            self.serial = serial.Serial(port,baud)
            self.serial_type = ['serial',0]
            num_bytes = self.serial.inWaiting()
            serial_lock_file(port)            
            self.logger.debug(funcname + ': Starting thread')            
            self.serial_thread = threading.Thread(target=self.read_serial_data)
            self.serial_thread.daemon = True
            self.serial_thread.start()            
            self.logger.debug(funcname + ': Starting thread done')
            self.status = 0
        except Exception as e:
            self.logger.debug(funcname + ': Exception: ' + str(e))            
            self.logger.debug(funcname + ': Could not open device at: ' + str(port))


    def add_socket(self,address,port):
        """
        Adds a socket for communication with the TODL
        """
        funcname = self.__class__.__name__ + '.add_socket()'
        self.logger.debug(funcname + ': Opening: ' + address + ':' + str(port))        
        try:
            self.bytes_read = 0
            # Make two sockets for the same connection, one received, one send
            self.serial = []
            print('One')
            self.serial_block = False
            self.serial = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serial.connect((address, port))
            self.serial_type = ['socket',1]
            self.serial.setblocking(0) # Nonblocking

            self.logger.debug(funcname + ': Starting thread')            
            self.serial_thread = threading.Thread(target=self.read_serial_data)
            self.serial_thread.daemon = True
            self.serial_thread.start()            
            self.logger.debug(funcname + ': Starting thread done')
            self.status = 0
        except Exception as e:
            self.logger.debug(funcname + ': Exception: ' + str(e))            
            self.logger.debug(funcname + ': Could not open device at: ' + str(port))            
            

    #def read_serial_data(self, dt = 0.003):
    def read_serial_data(self, dt = 0.01):
        """

        The serial data polling thread

        Args:
            dt: Sleeping time between polling [default 0.01]

        """
        funcname = self.__class__.__name__ + '.read_serial_data()'
        self.logger.debug(funcname)
        # Calculate average bytes per time interval
        tstart = time.time()
        bytes_read = 0
        while True:
            time.sleep(dt)
            tstop = time.time()
            if((tstop-tstart) > self.bytes_read_avg_dt):
                tstart = time.time()
                self.bytes_read_avg = bytes_read*8/self.bytes_read_avg_dt
                bytes_read = 0
                
            # Distingiush here between serial data and socket data
            if(self.serial_type[1] == 0): # Serial device
                num_bytes = self.serial.inWaiting()
                if(num_bytes > 0):
                    try:
                        data = self.serial.read(num_bytes)
                        if(self.print_serial_data):
                            print(data)

                        self.bytes_read += num_bytes
                        bytes_read += num_bytes
                        for n,deque in enumerate(self.deques_raw_serial):
                            deque.appendleft(data)
                    except Exception as e:
                        pass
                        #logger.debug(funcname + ':Exception:' + str(e) + ' num_bytes: ' + str(num_bytes))

            elif(self.serial_type[1] == 1): # Socket device
                num_bytes = 0
                # Check if we are free
                try:
                    if(not(self.serial_block)):
                        data,address = self.serial.recvfrom(10000)
                        num_bytes = len(data)
                        if(self.print_serial_data):
                            print(data)

                        self.bytes_read += num_bytes
                        bytes_read += num_bytes                        
                        for n,deque in enumerate(self.deques_raw_serial):
                            deque.appendleft(data)
                    else:
                        print('block!')
                except Exception as e:
                    #logger.debug(funcname + ':Exception:' + str(e) + ' num_bytes: ' + str(num_bytes))
                    pass
                        
                    
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
        # Distingiush here between serial data and socket data

        if(self.serial != None):
            if(self.serial_type[1] == 0): # Serial device                    
                self.logger.debug(funcname + ': Sending to device:' + str(data))
                # Python2 work with that
                self.serial.write(str(data).encode('utf-8'))
                self.logger.debug(funcname + ': Sending done')
            elif(self.serial_type[1] == 1): # Socket
                self.serial_block = True # Block the reading (thread safe ...)
                self.logger.debug(funcname + ': Sending to socket (device):' + str(data))
                self.serial.send(str(data).encode('utf-8'))
                self.logger.debug(funcname + ': Sending done')
                self.serial_block = False                
        else:
            self.logger.warning(funcname + ':Serial port/socket is not open.')


    def stop_serial_data(self):
        """Closes the serial port and does a cleanup of running threads etc.

        """
        funcname = self.__class__.__name__ + '.stop_serial_data()'
        self.logger.debug(funcname + ': Stopping')
        self.serial_thread_queue.put('stop')
        data = self.serial_thread_queue_ans.get()
        self.logger.debug(funcname + ': Got data, thread stopped')
        self._rem_raw_data_stream()
        port = self.serial.name
        # Distingiush here between serial data and socket data
        if(self.serial_type[1] == 0): # Serial device                            
            self.serial.close()
            serial_lock_file(port,remove=True)
        elif(self.serial_type[1] == 1): # Socket
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
        self.logfile_bytes_wrote = 0
        # Writing the start header
        tstartstr='# TODL file, pymqdatastream_version:' + pymqdatastream.version + '\n'
        self.logfile.write(tstartstr.encode('utf-8'))
        self.logfile_bytes_wrote += len(tstartstr)                
        # Writing local PC Time
        tlocalstr = time.strftime('# PC Time (GMT): %Y-%m-%d %H:%M:%S\n',time.gmtime())
        self.logfile.write(tlocalstr.encode('utf-8'))
        self.logfile_bytes_wrote += len(tlocalstr)        
        # Writing the info header
        info_str = self.device_info['info_str'].encode('utf-8')
        info_str += file_header_end
        self.logfile.write(info_str)
        self.logfile_bytes_wrote += len(info_str)
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
        self.logfile_bytes_wrote = 0

        
    def _logging_thread(self,deque,logfile,dt = 0.2):
        funcname = self.__class__.__name__ + '._logging_thread()'        
        while True:
            logfile.flush()                            
            time.sleep(dt)
            # Try to read from the queue, if something was read, quit
            while(len(deque) > 0):
                data = deque.pop()
                logfile.write(data)
                self.logfile_bytes_wrote += len(data)
            try:
                data = self._log_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self._log_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass                                        

        
    def add_raw_data_stream(self):
        """
        
        Adds a stream containing the raw data read from todl. 

        Args: None
            
        Returns:
            raw_stream: the raw data stream 
        
        """
        
        funcname = self.__class__.__name__ + '.add_raw_data_stream()'
        logger.debug(funcname)
        rawvar = pymqdatastream.StreamVariable(name = 'serial binary',unit = '',datatype = 'b')
        variables = ['serial binary',]
        name = 'serial binary'
        famstr = 'todl raw'
        stream = self.add_pub_stream(socket = self.sockets[-1], name=name, variables=[rawvar], family = famstr)
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
        """Pushes the raw serial data into the raw datastream

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

            
    def init_data_format(self,data_format):
        """Sets the data format of the input data

        """
        funcname = self.__class__.__name__ + '.init_data_format()'
        self.logger.debug(funcname)
        if(data_format == 0):
            self.device_info['format'] = 0
            self.init_data_format_functions()


        if(data_format == 2):
            self.device_info['format'] = 2
            self.init_data_format_functions()            


        # CSV style
        if((data_format == 3) or (data_format == 'csv')):
            self.device_info['format'] = 3
            self.init_data_format_functions()
            

        # CSV style
        if((data_format == 31) or (data_format == 'csv31')):
            self.device_info['format'] = 31
            self.init_data_format_functions() 

        
    def init_data_format_functions(self):
        """The TODL output can have different data formats (human readable csv
        format or cobs encoded binary format).  This function chooses the
        appropriate decoding fucntion

        """
        funcname = self.__class__.__name__ + '.init_data_format_functions()'
        self.logger.debug(funcname)                
        if(self.device_info['format'] == 0):
            self.logger.debug(funcname + ': Setting format to 0')              
            self.convert_raw_data = self.convert_raw_data_format0

        if(self.device_info['format'] == 2):
            self.logger.debug(funcname + ': Setting format to 2')
            self.convert_raw_data = self.convert_raw_data_format2

        if(self.device_info['format'] == 3):
            self.logger.debug(funcname + ': Setting format to 3')
            self.convert_raw_data = self.convert_raw_data_format3

        if(self.device_info['format'] == 31):
            self.logger.debug(funcname + ': Setting format to 31')
            self.convert_raw_data = self.convert_raw_data_format31

        if(self.device_info['format'] == 4):
            self.logger.debug(funcname + ': Setting format to 4')
            self.convert_raw_data = self.convert_raw_data_format4


    def init_todllogger(self,adcs=None,data_format=None,channels=None,freq=None):
        """Function to set specific settings on the logger, all arguments
default to None, only with a valid argument that setting will be sent to the device

        Args:
            flag_adcs: List of the ltc2442 channels to be send back [e.g. [0,2,7]], has to be between 0 and 7
            format: Output format of the logger
            channels: channel sequence, a list with a channel sequence [e.g. [0,1,2,3,0,0]]
            freq: conversion frequency

        """
        funcname = self.__class__.__name__ + '.init_todllogger()'

        dt_wait = 0.1
        self.logger.debug(funcname)
        if(self.status >= 0):
            if(self.status >= 1): # Already converting
                self.logger.debug(funcname + ': Stop converting raw data')
                self.stop_converting_raw_data()
                
            self.print_serial_data = True        
            self.send_serial_data('stop\n')
            time.sleep(dt_wait)
            self.send_serial_data('showdata off\n')
            time.sleep(dt_wait)
            if(adcs is not None):
                # Which ADCS?
                self.flag_adcs = adcs
                cmd = 'send ad'
                for ad in self.flag_adcs:
                    cmd += ' %d' %ad
                self.send_serial_data(cmd + '\n')
                self.logger.debug(funcname + ' sending:' + cmd)
                time.sleep(dt_wait)

            if(freq is not None):                
                # Due to a bug freq has to be send before data format if freq is 30, check firmware! (old, check if still true)
                # Freq
                cmd = 'freq ' + str(freq)
                self.send_serial_data(cmd + '\n')
                self.logger.debug(funcname + ' sending:' + cmd)

            if(data_format is not None):                
                # Data format
                self.device_info['format'] = data_format
                self.init_data_format_functions()
                cmd = 'format ' + str(data_format) + '\n'
                self.send_serial_data(cmd)
                self.logger.debug(funcname + ' sending:' + cmd)
                time.sleep(dt_wait)

            if(channels is not None):
                # Channel sequence
                cmd = 'channels '
                for ch in channels:
                    cmd += ' %d' %ch
                    self.send_serial_data(cmd + '\n')
                    self.logger.debug(funcname + ' sending:' + cmd)
                time.sleep(dt_wait)


            self.print_serial_data = False            
            # Update the device_info struct etc.
            self.query_todllogger()
            time.sleep(dt_wait)
            self.send_serial_data('showdata on\n')
            time.sleep(dt_wait)            
            self.send_serial_data('start\n')
            for fun in self.init_notification_functions:
                fun()
        else:
            self.logger.debug(funcname + ': No serial port opened')


    def set_time(self,timeset):
        """ Sets the time of the TODL
        """
        funcname = self.__class__.__name__ + '.set_time()'
        timeset = timeset + datetime.timedelta(milliseconds=1500) # Add 0.1 seconds because of the stop command
        tstr = timeset.strftime('%Y-%m-%d %H:%M:%S')
        print('setting time to:' + tstr)
        cmd = 'set time ' + tstr
        self.send_serial_data('stop\n')
        time.sleep(0.1)                
        self.send_serial_data(cmd)
        self.send_serial_data('start\n')
        time.sleep(0.1)                        

            
    def query_todllogger(self):
        """Queries the logger and sets the important parameters to the values read
        TODO: Do something if query fails, check if the extra commands are needed

        Returns:
            bool: True if we found a todllogger, False otherwise

        """
        dt = 0.2 # Additional wait between commands
        funcname = self.__class__.__name__ + '.query_todllogger()'
        self.logger.debug(funcname)        
        self.print_serial_data = True
        self.send_serial_data('stop\n')
        time.sleep(0.1+dt)
        # Flush the serial queue now
        deque = self.deques_raw_serial[0]
        while(len(deque) > 0):
            data = deque.pop()


        #
        # Send stop and info to check if we got some data which is a todl
        #
        FLAG_IS_TODL = False
        self.send_serial_data('stop\n')
        time.sleep(0.1+dt)

        self.send_serial_data('info\n')
        time.sleep(0.1+dt)        
        data_str = ''
        while(len(deque) > 0):
            data = deque.pop()
            print('data:',data)
            try:
                data_str += data.decode(encoding='utf-8')
            except Exception as e:
                self.logger.debug(funcname + ': Exception:' + str(e))
                return False

        return_str = data_str
        # Parse the received data for a valid reply
        if( ('>>>stop' in data_str) or ('><<stop' in data_str) ):
            FLAG_IS_TODL=True
            boardversion = '??'
            firmwareversion = '??'
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
                
            
        if(FLAG_IS_TODL==False):
            self.logger.warning(funcname + ': Device does not seem to be a todl')
            return False
        else:
            self.device_info = {}
            self.device_info['board'] = boardversion
            self.device_info['firmware'] = firmwareversion            
            
        self.send_serial_data('format\n')
        time.sleep(0.1+dt)
        self.send_serial_data('ad\n')
        time.sleep(0.1+dt)
        self.send_serial_data('channels\n')
        time.sleep(0.1+dt)
        tlocalstr = time.strftime('# PC Time just before info command (GMT): %Y-%m-%d %H:%M:%S\n',time.gmtime())
        self.send_serial_data('info\n')
        time.sleep(0.1+dt)
        # Hack, cleaner or just leave it as it does not hurt if S4L does not know it?
        self.send_serial_data('o2info\n')
        time.sleep(0.4+dt)

        # Get the fresh data
        data_str = tlocalstr
        while(len(deque) > 0):
            data = deque.pop()
            data_str += data.decode(encoding='utf-8')
            #data_str += data

        print(data_str)
        self.device_info = parse_device_info(data_str)
        self.channel_streams = [None] * (max(self.device_info['channel_seq']) + 1)        

        # TODO, replace by device_info dict
        self.init_data_format_functions()
        self.flag_adcs = self.device_info['adcs']

        self.print_serial_data = False                
        self.send_serial_data('start\n')
        
        return True

           
    def start_converting_raw_data(self, dt = None, ondemand = False):
        """


        Starting a thread to convert the raw data
        Creating datastreams for all the channels

        Args:
            ondemand: Option enables an blocking mode, the conversion functions will send with send self.raw_data_ondemand_queue.put('ready') the notification that new data can be processed, 'ready' is only sent, with an empty intraqueue.
        Returns:
            stream: A stream of the converted data
        
            


        """
        
        funcname = self.__class__.__name__ + '.start_converting_raw_data()'
        self.logger.debug(funcname)

        if(self.device_info != None):
            deque = collections.deque(maxlen=self.dequelen)
            # Add a overflow check flag to the deque
            # This will be used by the raw_data read functions (at the moment read_file_data only)
            self.deques_raw_serial.append(deque)
            # Add datastreams for all LTC channels and devices
            for ch in self.device_info['channel_seq']:
                self.logger.debug(funcname + ': Adding pub stream for channel:' + str(ch))
                # Adding a stream with all ltcs for each channel
                timevar = pymqdatastream.StreamVariable('time','seconds','float')
                packetvar = pymqdatastream.StreamVariable('packet','number','int')
                variables = [packetvar,timevar]

                for ad in self.flag_adcs:
                    datavar = pymqdatastream.StreamVariable('ad ' + str(ad) + ' ch ' + str(ch),'V','float')
                    variables.append(datavar)

                name = 'todl ad ch' + str(ch)
                famstr = 'todl adc'
                self.conv_streams.append(self.add_pub_stream(socket = self.sockets[-1], name=name, variables=variables, family = famstr))
                self.channel_streams[ch] = self.conv_streams[-1]

            # Add datastreams for IMU
            # TODO, this is a hack for the version 0.46! Make it more clean later!
            self.aux_streams = [None] * ( 1 + 1 )
            self.logger.debug(funcname + ': Adding pub stream for IMU ACC, Gyro x,y,z:')
            variables_IMU = [packetvar,timevar]
            datavarT     = pymqdatastream.StreamVariable('temp','degC','float')            
            datavarx_ACC = pymqdatastream.StreamVariable('ACC x','m/s','float')
            datavary_ACC = pymqdatastream.StreamVariable('ACC y','m/s','float')
            datavarz_ACC = pymqdatastream.StreamVariable('ACC z','m/s','float')
            datavarx_GYR = pymqdatastream.StreamVariable('GYR x','?','float')
            datavary_GYR = pymqdatastream.StreamVariable('GYR y','?','float')
            datavarz_GYR = pymqdatastream.StreamVariable('GYR z','?','float')
            variables_IMU.append(datavarT)
            variables_IMU.append(datavarx_ACC)
            variables_IMU.append(datavary_ACC)
            variables_IMU.append(datavarz_ACC)
            variables_IMU.append(datavarx_GYR)
            variables_IMU.append(datavary_GYR)
            variables_IMU.append(datavarz_GYR)
            name = 'todl IMU'
            famstr = 'todl IMU'
            self.conv_streams.append(self.add_pub_stream(socket = self.sockets[-1], name=name, variables=variables_IMU, family = famstr))
            #self.channel_streams[ch] = self.conv_streams[-1]
            self.aux_streams[0] = self.conv_streams[-1]
            # Pyro science oxygen fields
            self.logger.debug(funcname + ': Adding pub stream for Pyroscience')
            variables_O2 = [packetvar,timevar]
            for field in data_packages.pyro_science_format1_fields:
                datavar_O2_dphi = pymqdatastream.StreamVariable(field['name'],field['unit'],field['datatype'])
                variables_O2.append(datavar_O2_dphi)
                
            name = 'todl O2 (PyroScience)'
            famstr = 'todl O2'            
            self.conv_streams.append(self.add_pub_stream(socket = self.sockets[-1], name=name, variables=variables_O2, family = famstr))
            self.aux_streams[1] = self.conv_streams[-1]            
            # TODO, make this clean!
            
            self.logger.debug(funcname + ': Starting thread')
            # Analyse data format, choose the right conversion functions and start a conversion thread
            self.init_data_format_functions()
            self.packets_converted = 0
            kw = {'ondemand':ondemand}
            if(dt is not None):
                kw['dt'] = dt

            self.convert_thread = threading.Thread(target=self.convert_raw_data, args = (deque,), kwargs = kw)
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
    def convert_raw_data_format0(self, deque, dt = 0.5, ondemand = False):
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


    def convert_raw_data_format2(self, deque, dt = 0.1, ondemand = False):
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
        4    LTC COMMAND 2
        5    counter msb
        ...   
        12   counter lsb
        13   clock 50 khz msb
        ...    
        20   clock 50 khz lsb
        21   LTC2442 0 msb
        22   LTC2442 1 
        23   LTC2442 2 lsb 
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
                                    data_packet = {'num':packet_num,'t':packet_time}
                                    data_packet['type'] = 'L'                                    
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


    def convert_raw_data_format3(self, deque, dt = 0.05, ondemand = False):
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
        data_str = ''
        while True:
            #logger.debug(funcname + ': converted: ' + str(ad0_converted))
            nstreams = (max(self.device_info['channel_seq']) + 1)
            # Create a list of data to be submitted for each stream
            data_stream = [[] for _ in range(nstreams) ] 
            time.sleep(dt)
            while(len(deque) > 0):
                data = deque.pop()
                try:
                    data_str += data.decode(encoding='utf-8')
                except Exception as e:
                    logger.debug('Problems decoding data string:' + str(data) + '( Exception:' + str(e) + ' )')

                #data_list = [packet_num,packet_time]
                data_packets = []
                #for line in data_str.splitlines():
                data_str_split = data_str.split('\n')
                if(len(data_str_split[-1]) == 0): # We have a complete last line
                    data_str = ''
                else:
                    data_str = data_str_split[-1]
                    data_str_split.pop()

                for line in data_str_split:
                    if(len(line)>3):
                        try:
                            data_split = line.split(';')
                            packet_time = int(data_split[0])/self.device_info['counterfreq']
                            packet_num = int(data_split[1])
                            channel = int(data_split[2])
                            ad_data = data_split[3:]
                            # Fill the data list
                            data_list = [packet_num,packet_time]                    
                            # Fill the data packet dictionary
                            data_packet = {'num':packet_num,'t':packet_time}
                            data_packet['type'] = 'L'                            
                            data_packet['ch'] = channel
                            data_packet['V'] = [9999.99] * len(self.device_info['adcs'])
                            # Test if the lengths are same
                            if(len(ad_data) == len(self.device_info['adcs'] * 2)):
                                for n,i in enumerate(range(0,len(ad_data)-1,2)):
                                    V = float(ad_data[i+1])
                                    data_packet['V'][n] = V
                                    data_list.append(V)
                            else:
                               logger.debug( funcname + ': List lengths do not match: ' + str(ad_data) + ' and with num of adcs: ' + str(len(self.device_info['adcs'])) + ' str:' +  data_str_split)


                            data_packets.append(data_packet)
                            data_stream[channel].append(data_list)
                        except Exception as e:
                            pass
                            #logger.debug(funcname + ':' + str(e))
                            
            # Push the read data
            ti = time.time()
            
            #if(len(data0)>0):
            #    streams[0].pub_data(data0)

            for data_packet in data_packets:
                self.intraqueue.appendleft(data_packet)
                #self.channel_streams[ch]
                # Fill the data_stream list


            for i in range(len(self.channel_streams)):
                if(len(data_stream[i])>0):
                    self.channel_streams[i].pub_data(data_stream[i])                            

            # Try to read from the queue, if something was read, quit
            try:
                data = self.conversion_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self.conversion_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass

            
    def convert_raw_data_format31(self, deque, dt = 0.05, ondemand = False):
        """
        Converts raw data of the format 31, which is popped from the deque given as argument
        Example:
        L;00000000692003;00000000000342;2;+2.04882227;-9.99999999
        10 khz counter; num package;channel;Volt ad; ...
        Args:
            deque:
            dt:
            ondemand: Option is used to send self.raw_data_ondemand_queue.put('ready') to notify the raw_data routine that new data can be processed, 'ready' is only sent, with an empty intraqueue.

        HACK: This is also converting pyro science O2 data and IMU data, this should be cleaned up 

        """
        funcname = self.__class__.__name__ + '.convert_raw_data_format31()'
        self.logger.debug(funcname)
        ad0_converted = 0
        data_packets = []
        data_str = ''

        # Arrays for frequency calculation
        dt_freq = 0.5
        len_t_array = 1000
        Lpacket_t = np.zeros((len_t_array,2)) # For LTC2442 packets
        Lpacket_t_ind = 0
        while True:
            #logger.debug(funcname + ': converted: ' + str(ad0_converted))
            nstreams = (max(self.device_info['channel_seq']) + 1)
            # Create a list of data to be submitted for each stream
            data_stream = [[] for _ in range(nstreams) ]
            # PH: Another hack for the v046, make clear 
            aux_data_stream = [[],[]]
            data_packets = []
            ts = time.time()
            time.sleep(dt)
            while(len(deque) > 0):
                data = deque.pop()
                try:
                    data_str += data.decode(encoding='utf-8')
                except Exception as e:
                    logger.debug('Problems decoding data string:' + str(data) + '( Exception:' + str(e) + ' )')

                #data_list = [packet_num,packet_time]
                #for line in data_str.splitlines():
                data_str_split = data_str.split('\n')
                if(len(data_str_split[-1]) == 0): # We have a complete last line
                    data_str = ''
                else:
                    data_str = data_str_split[-1]
                    data_str_split.pop()

                data_packets.extend(data_packages.decode_format31(data_str_split,self.device_info))
                            
            # Push the read data
            ti = time.time()

            # Sort the data and put into lists for datastream
            # distribution as well as frequency calculations
            for data_packet in data_packets:
                if(data_packet['type'] == 'L'): # LTC2442 packet
                    data_list = [data_packet['num'],data_packet['t']] + data_packet['V']
                    data_stream[data_packet['ch']].append(data_list)
                    # Packet for frequency calculation
                    if(Lpacket_t_ind < len_t_array):
                        Lpacket_t[Lpacket_t_ind,0] = ts
                        Lpacket_t[Lpacket_t_ind,1] = data_packet['t']
                        Lpacket_t_ind += 1

                elif(data_packet['type'] == 'A'): # IMU packet
                    #data_packet['mag']
                    aux_data_stream[0].append([data_packet['num'],data_packet['t'],data_packet['T'],data_packet['acc'][0],data_packet['acc'][1],data_packet['acc'][2],data_packet['gyro'][0],data_packet['gyro'][1],data_packet['gyro'][2]])
                elif(data_packet['type'] == 'O'): # Firesting packet         
                    aux_data_stream[1].append([data_packet['num'],data_packet['t'],data_packet['phi'],data_packet['umol']])


            
            # Frequency packets
            if(Lpacket_t_ind > 0):
                dtL = Lpacket_t[:Lpacket_t_ind,0].max() - Lpacket_t[:Lpacket_t_ind,0].min()
                if((Lpacket_t_ind >= len_t_array) or (dtL > dt_freq)):
                    data_packet = {'type':'Lfr'} # Type L freq
                    data_packet['dt'] = dtL
                    dtLt = Lpacket_t[Lpacket_t_ind-1,1] - Lpacket_t[0,1]
                    #print(dtLt)
                    data_packet['f'] = (Lpacket_t_ind-1)/(dtLt)
                    Lpacket_t[:,:] = 0
                    Lpacket_t_ind = 0                    
                    #print(data_packet)
                    data_packets.append(data_packet)


            # This data is first put into the local intraque for data distribution (mainly the gui up to now)
            for data_packet in data_packets:
                self.intraqueue.appendleft(data_packet)


            # This data is for the remote datastreams ( LTC data ) 
            for i in range(len(self.channel_streams)):
                if(len(data_stream[i])>0):
                    self.channel_streams[i].pub_data(data_stream[i])

            # These are the aux streams (IMU stream [0], firesting stream [1], TODO, unify!)
            for i in range(len(self.aux_streams)):
                if(len(aux_data_stream[i])>0):
                    self.aux_streams[i].pub_data(aux_data_stream[i])

            # Try to read from the queue, if something was read, quit
            try:
                data = self.conversion_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self.conversion_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass

            # Check if ondemand mode, if yes send ready and wait for new data
            if(ondemand):
                if(len(self.intraqueue) == 0): # Check if intraqueue is empty, meaning that the data has been processed
                    # Send ready to the ondemand queue                
                    self.raw_data_ondemand_queue.put('ready')

            
    def convert_raw_data_format4(self, deque, dt = 0.02, ondemand = False):
        """

        Converts raw data of the format 4, which is popped from the deque
        given as argument 
        The data is sends in binary packages using the the consistent overhead
        byte stuffing (`COBS
        <https://en.wikipedia.org/wiki/Consistent_Overhead_Byte_Stuffing>`_)
        algorithm.
        After decoding cobs the binary data has the following content

        ==== ====
        Byte Usage
        ==== ====
        0    0xAE (Packet type)
        1    FLAG LTC (see comment)
        2    LTC COMMAND 0 (as send to the AD Converter)
        3    LTC COMMAND 1
        4    LTC COMMAND 2
        5    packet counter msb
        ...   
        9    packet counter lsb
        10   clock 10 khz msb
        ...    
        14   clock 10 khz lsb
        15   LTC2442 0 msb
        16   LTC2442 1 
        17   LTC2442 2 lsb 
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
        funcname = self.__class__.__name__ + '.convert_raw_data_format4()'
        self.logger.debug(funcname)
        ad0_converted = 0
        data_str = b''
        cnt = 0
        cto = 0 # Get frequency (hack)
        ct = cto
        while True:
            cnt += 1
            aux_data_stream = [[],[]]
            nstreams = (max(self.device_info['channel_seq']) + 1)            
            data_stream = [[] for _ in range(nstreams) ]
            ta = []
            time.sleep(dt)
            ta.append(time.time())
            while(len(deque) > 0):
                data = deque.pop()
                data_str += data

            if(len(data_str) > 17):
                ta.append( time.time() )
                #print('len',len(data_str))                
                [data_packets,data_str] = data_packages.decode_format4(data_str,self.device_info)
                self.packets_converted += len(data_packets)

                # Sort the data and put into lists for datastream
                # distribution as well as frequency calculations
                for data_packet in data_packets:
                    if(data_packet['type'] == 'L'): # LTC2442 packet
                        data_list = [data_packet['num'],data_packet['t']] + data_packet['V']
                        data_stream[data_packet['ch']].append(data_list)
                        # Packet for frequency calculation
                        #if(Lpacket_t_ind < len_t_array):
                        #    Lpacket_t[Lpacket_t_ind,0] = ts
                        #    Lpacket_t[Lpacket_t_ind,1] = data_packet['t']
                        #    Lpacket_t_ind += 1

                    elif(data_packet['type'] == 'A'): # IMU packet
                        aux_data_stream[0].append([data_packet['num'],data_packet['t'],data_packet['T'],data_packet['acc'][0],data_packet['acc'][1],data_packet['acc'][2],data_packet['gyro'][0],data_packet['gyro'][1],data_packet['gyro'][2]])
                    elif(data_packet['type'] == 'O'): # Firesting packet         
                        aux_data_stream[1].append([data_packet['num'],data_packet['t'],data_packet['phi'],data_packet['umol']])

                    
                if(False):
                    if(len(data_packets) >=2):
                        ct = data_packets[1]['t']
                        cto = data_packets[0]['t']
                        dtt = (ct - cto)
                        ftt = 1/dtt
                        print(ftt)                    


                ta.append( time.time() )

                # This data is first put into the local intraque for data distribution (mainly the gui up to now)
                for data_packet in data_packets:
                    self.intraqueue.appendleft(data_packet)
                # Lets publish the converted data!
                for i in range(len(self.channel_streams)):
                    if(len(data_stream[i])>0):
                        self.channel_streams[i].pub_data(data_stream[i])

                # These are the aux streams (IMU stream [0], firesting stream [1], TODO, unify!)
                for i in range(len(self.aux_streams)):
                    if(len(aux_data_stream[i])>0):
                        self.aux_streams[i].pub_data(aux_data_stream[i])                        


                ta.append(time.time())
                ta = np.asarray(ta)
                #print(np.diff(ta))


            # Try to read from the queue, if something was read, quit
            try:
                data = self.conversion_thread_queue.get(block=False)
                self.logger.debug(funcname + ': Got data:' + data)
                self.conversion_thread_queue_ans.put('stopping')
                break
            except queue.Empty:
                pass                        




def todlraw_to_netCDF():
    """ Converts a todl file to netCDF
    
    """

    usage_str = 'todl_rawtonc'
    desc = 'Converts raw turbulent ocean data logger files into netCDF files. Example usage: ' + usage_str
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('rawfile', help= 'The filename of the raw data file')
    parser.add_argument('ncfile',help='The filename of the converted netcdf file')    
    parser.add_argument('--verbose', '-v', action='count')    

    args = parser.parse_args()
    # Print help and exit when no arguments are given
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)


    rawfile = args.rawfile
    ncfile = args.ncfile

    print(rawfile,ncfile)

    ncconv = todlnetCDF4File(rawfile)
    ncconv.to_ncfile_fast(ncfile)
    ncconv.close()
    print('Done')
    
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG
        
    logger.setLevel(loglevel)
    



def main():    
    s = todlDataStream(logging_level='DEBUG')
    s.add_serial_device('/dev/ttyUSB0')

    s.add_raw_data_stream()
    #s.load_file('netstring_format1.log')

    # Send a format 2 command
    time.sleep(0.5)
    s.init_todllogger(flag_adcs = [0],data_format=2)
    s.query_todllogger()
    time.sleep(0.5)
    #s.print_serial_data = True    
    s.start_converting_raw_data()
    print(s.get_info_str('short'))
    while(True):
        #print('Raw bytes read ' + str(s.bytes_read))
        #print(s.get_info_str('short'))
        time.sleep(5)


if __name__ == '__main__':
    main()
    
