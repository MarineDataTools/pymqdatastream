#!/usr/bin/env python3

#
#

"""Module for a Qt-Based GUI of the Turbulent Ocean Data Logger. The
heart are device objects with several mandatory function such that the
main object of this module can open/close and call information
functions

A device needs the following informations:

 __init__(self,      device_changed_function=None)

The device changed function is used to interconnect the device to each other


- setup(name)     (mandatory)
- info      (obligatory)
- show_data (obligatory)
- plot_data (obligatory)
- close     (mandatory)

.. moduleauthor:: Peter Holtermann <peter.holtermann@io-warnemuende.de>

"""


try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except:
    from qtpy import QtCore, QtGui, QtWidgets


import sys
import json
import numpy as np
import logging
import threading
import os,sys
import ntpath
import serial
import glob
import collections
import time
import multiprocessing
import binascii
import yaml
import datetime
# Import GPS/NMEA functionality
import pymqdatastream.connectors.nmea.pymqds_nmea0183_gui as pymqds_nmea0183_gui

# Get a standard configuration
from pkg_resources import Requirement, resource_filename
filename = resource_filename(Requirement.parse('pymqdatastream'),'pymqdatastream/connectors/todl/todl_config.yaml')
filename_version = resource_filename(Requirement.parse('pymqdatastream'),'pymqdatastream/VERSION')


with open(filename_version) as version_file:
    version = version_file.read().strip()

print(filename_version)
print(version)    

with open(filename) as config_file:
    config = yaml.load(config_file)
    print(config)
    
    

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqds_gui_todl')
logger.setLevel(logging.DEBUG)


import pymqdatastream
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service
try:
    import pymqdatastream.connectors.pyqtgraph.pymqds_plotxy as pymqds_plotxy
    from pymqdatastream.connectors.pyqtgraph import pyqtgraphDataStream
    FLAG_PLOTXY=True
except Exception as e:
    logger.warning('Could not import pymqds_plotxy, this is not fatal, but there will be no real time plotting (original error: ' + str(e) + ' )')
    FLAG_PLOTXY=False
    
import pymqdatastream.connectors.todl.pymqds_todl as pymqds_todl
from pymqdatastream.utils.utils_serial import serial_ports, test_serial_lock_file, serial_lock_file


counter_test = 0

            
# Serial baud rates
baud = [300,600,1200,2400,4800,9600,19200,38400,57600,115200,576000,921600]


class todlInfo(QtWidgets.QWidget):
    """
    Widget display status informations of a todl device
    """
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.f_version = QtWidgets.QLabel('Firmware: ?')
        self.b_version = QtWidgets.QLabel('Board: ?')
        self.adcs = QtWidgets.QLabel('ADCS: ?')       
        self.ch_seq = QtWidgets.QLabel('Channels: ?')
        self.data_format = QtWidgets.QLabel('Format: ?')
        self.freq = QtWidgets.QLabel('Conv. freq: ?')
        # Status packet labels
        self.status_date  = QtWidgets.QLabel('Date: ?')
        self.status_t     = QtWidgets.QLabel('t: ?')
        self.status_t32   = QtWidgets.QLabel('t32: ?')
        self.status_start = QtWidgets.QLabel('start: ?')
        self.status_show  = QtWidgets.QLabel('show: ?')
        self.status_log   = QtWidgets.QLabel('log: ?')
        self.status_sd    = QtWidgets.QLabel('sd: ?')
        self.status_fname = QtWidgets.QLabel('fname: ?')
        # Bytes read and bytes speed info
        self.bytesread    = QtWidgets.QLabel('Bytes read: ')
        # Widget to show the average transfer rate
        self.bytesspeed   = QtWidgets.QLabel('Bit/s:')                        

        
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.b_version,0,0)
        layout.addWidget(self.f_version,0,1)
        layout.addWidget(self.adcs,0,2)
        layout.addWidget(self.ch_seq,0,3)
        layout.addWidget(self.data_format,0,4)
        layout.addWidget(self.freq,0,5)
        layout.addWidget(self.status_date,1,0)
        layout.addWidget(self.status_t,1,1)
        layout.addWidget(self.status_t32,1,2)
        layout.addWidget(self.status_start,1,3)
        layout.addWidget(self.status_show,1,4)
        layout.addWidget(self.status_log,1,5)
        layout.addWidget(self.status_sd,1,6)
        layout.addWidget(self.status_fname,1,7)
        layout.addWidget(self.bytesread,2,0)
        layout.addWidget(self.bytesspeed,2,1)

        self.setLayout(layout)        

    def update(self,status):
        """
        Updates the widget with status dictionary
        """

        boardstr = 'Board: ' + status['board']
        firmstr = 'Firmware: ' + status['firmware']
        chstr = 'Channels: '
        for ch in status['channel_seq']:
            chstr += str(ch)
        formatstr = 'Format: ' + str(status['format'])
        adcstr = 'ADCS: '
        for adc in status['adcs']:
            adcstr += str(adc)
            

        freqstr = "Conv. freq: " + str(status['freq_str']) + ' [Hz]'
        
        self.b_version.setText(boardstr)
        self.f_version.setText(firmstr)
        self.ch_seq.setText(chstr)
        self.adcs.setText(adcstr)
        self.data_format.setText(formatstr)
        self.freq.setText(freqstr)

    def update_status_packet(self,status_packet):
        """Updates the widget with the data from a status packet

        """
        
        self.status_date.setText('Date:' + status_packet['date_str'])
        self.status_t.setText('t: ' + str(status_packet['t']))        
        self.status_t32.setText('t32: ' + str(status_packet['t32']))
        self.status_start.setText('Start: ' + str(status_packet['start']))
        self.status_show.setText('Show: ' + str(status_packet['show']))
        self.status_log.setText('Log: ' + str(status_packet['log']))
        self.status_sd.setText('SD: ' + str(status_packet['sd']))
        if(status_packet['filename'] is not None):
            self.status_fname.setText('Filename: ' + status_packet['filename'])


    def update_bytes(self,bytes_read,bytes_read_avg):
        """
        """
        self.bytesread.setText('Bytes read: ' + str(bytes_read))
        # Widget to show the average transfer rate
        self.bytesspeed.setText('Bit/s: ' + str(bytes_read_avg))

    



class todlConfig(QtWidgets.QWidget):
    """
    Configuration widget for the todl
    """
    # Conversion speeds of the device

    def __init__(self,todl=None, deviceinfowidget = None):
        self.deviceinfo = deviceinfowidget        
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QGridLayout()


        self.set_time     = QtWidgets.QPushButton('Set time')
        self.set_time.clicked.connect(self.clicked_set_time)
        self.timeWidget   = timeWidget()        

        # Conversion speed
        self._freq_button     = QtWidgets.QPushButton('Set frequency')
        self._freq_button.clicked.connect(self.clicked_set_freq)
        self._convspeed_combo = QtWidgets.QComboBox(self)
        # v0.75 speeds
        #self.speeds        = pymqds_todl.s4lv0_4_speeds
        #self.speeds_hz_adc = pymqds_todl.s4lv0_4_speeds_hz_adc
        #self.speeds_td     = pymqds_todl.s4lv0_4_speeds_td
        self.speeds_hz     = pymqds_todl.s4lv0_75_speeds_hz
        for i,speed in enumerate(self.speeds_hz):
            speed_hz = 'f: ' + str(self.speeds_hz[i]) + ' Hz'
            #speed_hz = 'f: ' + str(self.speeds_hz[i]) + \
            #           ' Hz (f ADC:' + str(self.speeds_hz_adc[i]) + ' Hz)'
            self._convspeed_combo.addItem(str(speed_hz))        

        # Data format
        self.formats =     [2              , 31   , 4                            ]
        self.formats_str = ['binary (cobs)','csv' , 'binary (cobs, reduced size)']
        self._set_format_button= QtWidgets.QPushButton('Set data format')
        self._set_format_button.clicked.connect(self.clicked_set_format)
        self._dataformat_combo = QtWidgets.QComboBox(self)
        for i,dformat in enumerate(self.formats):
            format_str = str(dformat) + ' ' + self.formats_str[i]
            self._dataformat_combo.addItem(format_str)        



        self._query_bu = QtWidgets.QPushButton('Query')
        self._query_bu.clicked.connect(self._query)
        self._ad_apply_bu = QtWidgets.QPushButton('Send to device')
        self._ad_apply_bu.clicked.connect(self._setup_device)

        # Which ADCs to sample?
        # Create an adc checkbox widget
        # 
        self._ad_set_button = QtWidgets.QPushButton('Set sampling ADCS')
        self._ad_set_button.clicked.connect(self.clicked_set_adcs)
        self._ad_widget_check = QtWidgets.QWidget()
        ad_layoutV = QtWidgets.QHBoxLayout(self._ad_widget_check)

        self._ad_check = []        
        for i in range(8):
            ad_check = QtWidgets.QCheckBox('AD ' + str(i))
            self._ad_check.append(ad_check)
            ad_layoutV.addWidget(ad_check)


        # Which channels to sample?            
        # Create a channel sequence widget
        self._channels_set_button = QtWidgets.QPushButton('Set channel sequence')
        self._channels_set_button.clicked.connect(self.clicked_set_channels)
        channels = ['0','1','2','3','-']
        self._ad_seq_check = QtWidgets.QWidget()
        ad_seq_layoutV = QtWidgets.QVBoxLayout(self._ad_seq_check)
        _ad_seq_check_tmp = QtWidgets.QWidget()
        ad_seq_layoutH = QtWidgets.QHBoxLayout(_ad_seq_check_tmp)
        self._seq_combo = []
        for i in range(8):
            seq_combo = QtWidgets.QComboBox()
            self._seq_combo.append(seq_combo)
            for ch in channels:
                seq_combo.addItem(ch)
            
            ad_seq_layoutH.addWidget(seq_combo)


        _ad_seq_check_tmp2 = QtWidgets.QWidget()
        ad_seq_layoutH2 = QtWidgets.QHBoxLayout(_ad_seq_check_tmp2)
        #ad_seq_layoutH2.addWidget(QtWidgets.QLabel('Define channel sequence'))
        #ad_seq_layoutV.addWidget(_ad_seq_check_tmp2)
        ad_seq_layoutV.addWidget(_ad_seq_check_tmp)


        # The main layout
        layout.addWidget(self.timeWidget,0,0,5,1)
        layout.addWidget(self.set_time,6,0)
        
        layout.addWidget(self._freq_button,1,0+1,1,2)
        layout.addWidget(self._convspeed_combo,0,0+1,1,2)
        
        layout.addWidget(self._set_format_button,1,2+1,1,2)
        layout.addWidget(self._dataformat_combo,0,2+1,1,2)
        
        layout.addWidget(self._ad_set_button,3,0+1,1,4)
        layout.addWidget(self._ad_widget_check,2,0+1,1,4)
        
        layout.addWidget(self._channels_set_button,5,0+1,1,4)
        layout.addWidget(self._ad_seq_check,4,0+1,1,4)
        
        layout.addWidget(self._query_bu,6,0+1)
        layout.addWidget(self._ad_apply_bu,6,1+1)        


        self.setLayout(layout)

        print('updating')
        # TODO do something if there is nothing
        self.todl = todl
        self._update_status()
        if(self.deviceinfo is not None):
            if(self.todl.status >= 0): # Opened serial port or converting
                print('updateting device info')
                self.deviceinfo.update(self.todl.device_info)


    def _update_status(self):
        """Updates all the information buttons

        """
        
        status = self.todl.device_info
        if(self.todl.status >= 0): # Opened serial port or converting
            print('status',status)
            # Channels
            #self.combo_baud.setCurrentIndex(len(baud)-1)
            for i,ch in enumerate(status['channel_seq']):
                self._seq_combo[i].setCurrentIndex(ch)

            # Fill the rest with None
            for i in range(i+1,8):
                self._seq_combo[i].setCurrentIndex(4)


            #
            # ADCS
            #
            for i,ad_check in enumerate(self._ad_check):            
                ad_check.setChecked(False)

            for i,adc in enumerate(status['adcs']):            
                self._ad_check[adc].setChecked(True)

            
    def _setup_device(self):
        freq_str = self._convspeed_combo.currentText()
        ind = self._convspeed_combo.currentIndex()
        freq_num = self.speeds_hz[ind]
        logger.debug('_setup_device(): Setting speed to ' + str(freq_str)\
                     + ' num:' + str(freq_num))

        data_format = 3
        print('Data format',data_format)        
        
        adcs = []
        for i,ad_check in enumerate(self._ad_check):            
            if(ad_check.isChecked()):
                adcs.append(i)

        print('ADCS List:',adcs)

        chs = []
        for i,seq_combo in enumerate(self._seq_combo):
            ind = seq_combo.currentIndex()
            if(ind < 4):
                chs.append(ind)
            else:
                break

        print('Chs List:',chs)
        print('init todllogger')
        self.todl.init_todllogger(adcs = adcs,channels=chs,freq=freq_num,data_format=31)
        self._update_status()
        self.deviceinfo.update(self.todl.device_info)


    def clicked_set_freq(self):
        """ Sets the frequency of the datalogger
        """
        funcname = 'clicked_set_freq()'
        freq_str = self._convspeed_combo.currentText()
        ind = self._convspeed_combo.currentIndex()
        freq_num = self.speeds_hz[ind]
        logger.debug(funcname + ': Setting speed to ' + str(freq_str)\
                     + ' num:' + str(freq_num))


        self.todl.init_todllogger(freq=freq_num)
        self._update_status()
        self.deviceinfo.update(self.todl.device_info)


    def clicked_set_adcs(self):
        """ Sets the sampling adcs
        """
        funcname = 'clicked_set_adcs()'
        adcs = []
        for i,ad_check in enumerate(self._ad_check):            
            if(ad_check.isChecked()):
                adcs.append(i)

        logger.debug(funcname + ': Setting ADCS list' + str(adcs))
        self.todl.init_todllogger(adcs=adcs)
        self._update_status()
        self.deviceinfo.update(self.todl.device_info)


    def clicked_set_channels(self):
        """ Sets the sampling channels
        """
        funcname = 'clicked_set_channels()'

        chs = []
        for i,seq_combo in enumerate(self._seq_combo):
            ind = seq_combo.currentIndex()
            if(ind < 4):
                chs.append(ind)
            else:
                break

        logger.debug(funcname + ': Setting channels' + str(chs))
        self.todl.init_todllogger(channels=chs)
        self._update_status()
        self.deviceinfo.update(self.todl.device_info)

        
    def clicked_set_format(self):
        """ Set the data format
        """
        funcname = 'clicked_set_format'

        ind = self._dataformat_combo.currentIndex()
        data_format = self.formats[ind]
        data_format_str = self.formats_str[ind]        
        logger.debug(funcname + ': Setting format to ' + str(data_format) + ' (' + data_format_str + ')')

        
    def clicked_set_time(self):
        self.todl.set_time(datetime.datetime.now(datetime.timezone.utc))
        pass                


    def _query(self):
        """ Querying the datalogger
        """
        self.todl.query_todllogger()
        
        self._update_status()
        self.deviceinfo.update(self.todl.device_info)
        

    def _close(self):
        self.close()


def _start_pymqds_plotxy(addresses):
    """
    
    Start a pymqds_plotxy session and plots the streams given in the addresses list
    Args:
        addresses: List of addresses of pymqdatastream Streams
    
    """

    logger.debug("_start_pymqds_plotxy():" + str(addresses))

    logging_level = logging.DEBUG
    datastreams = []
    
    for addr in addresses:
        datastream = pyqtgraphDataStream(name = 'plotxy_cont', logging_level=logging_level)
        stream = datastream.subscribe_stream(addr)
        print('HAllo,stream'+ str(stream))
        if(stream == None): # Could not subscribe
            logger.warning("_start_pymqds_plotxy(): Could not subscribe to:" + str(addr) + ' exiting plotting routine')
            return False
        

        datastream.set_stream_settings(stream, bufsize = 5000, plot_data = True, ind_x = 1, ind_y = 2, plot_nth_point = 10)
        datastream.plot_datastream(True)
        datastream.set_plotting_mode(mode='cont')        
        datastreams.append(datastream)

        if(False):
            datastream_xr = pyqtgraphDataStream(name = 'plotxy_xr', logging_level=logging_level)
            stream_xr = datastream_xr.subscribe_stream(addr)
            datastream_xr.init_stream_settings(stream_xr, bufsize = 5000, plot_data = True, ind_x = 1, ind_y = 2, plot_nth_point = 6)
            datastream_xr.plot_datastream(True)
            datastream_xr.set_plotting_mode(mode='xr',xl=5)        
            datastreams.append(datastream_xr)        


    app = QtWidgets.QApplication([])
    plotxywindow = pymqds_plotxy.pyqtgraphMainWindow(datastream=datastreams[0])
    if(False):
        for i,datastream in enumerate(datastreams):
            if(i > 0):
                plotxywindow.add_graph(datastream=datastream)
        
    plotxywindow.show()
    sys.exit(app.exec_())    
    logger.debug("_start_pymqds_plotxy(): done")




def _start_pymqds_plotxy_test(graphs):
    """
    Start a pymqds_plotxy session and plots the streams given in the addresses list
    Args:
        streams: Dictionary of a stream with additionally information as index to plot etc.
    
    """

    logger.debug("_start_pymqds_plotxy_test():" + str(graphs))

    logging_level = logging.DEBUG
    datastreams = []
    

    for n,streams in enumerate(graphs):
        datastream = pyqtgraphDataStream(name = 'plotxy_' + str(n), logging_level=logging_level)
        for dstream in streams:
            addr = dstream['address']
            stream = datastream.subscribe_stream(addr)
            print('HAllo,stream'+ str(stream))
            if(stream == None): # Could not subscribe
                logger.warning("_start_pymqds_plotxy(): Could not subscribe to:" + str(addr) + ' exiting plotting routine')
                return False

            datastream.set_stream_settings(stream, bufsize = 5000, plot_data = True, ind_x = dstream['ind_x'], ind_y = dstream['ind_y'], plot_nth_point = dstream['nth_point'])
            datastream.plot_datastream(True)
            datastream.set_plotting_mode(mode='cont')        
            datastreams.append(datastream)

            if(False):
                datastream_xr = pyqtgraphDataStream(name = 'plotxy_xr', logging_level=logging_level)
                stream_xr = datastream_xr.subscribe_stream(addr)
                datastream_xr.init_stream_settings(stream_xr, bufsize = 5000, plot_data = True, ind_x = 1, ind_y = 2, plot_nth_point = 6)
                datastream_xr.plot_datastream(True)
                datastream_xr.set_plotting_mode(mode='xr',xl=5)        
                datastreams.append(datastream_xr)        


        if(n == 0):
            app = QtWidgets.QApplication([])            
            plotxywindow = pymqds_plotxy.pyqtgraphMainWindow(datastream=datastreams[0])                        
        else:
            plotxywindow.add_graph(datastream=datastream)            

            
    plotxywindow.show()
    sys.exit(app.exec_())    
    logger.debug("_start_pymqds_plotxy(): done")



#
#
# GPS Device
#
#
class gpsDevice():
    """A device to interact with the connectors.nmea.pymqds_nmea0183logger
    object using the pymqds_nmea0183_gui.nmea0183SetupWidget widget
    for configuration

    """
    def __init__(self, device_changed_function=None):
        print('GPS Device')
        self.device_changed_function = device_changed_function
        
    def setup(self,name=None):
        self.name = name
        print('GPS Setup')
        self.w = pymqds_nmea0183_gui.nmea0183SetupWidget()
        # Copy the nmea0183logger
        self.nmea0183logger = self.w.nmea0183logger
        # Connect the device changed function
        self.nmea0183logger.signal_functions.append(self.device_changed)
        self.w.show()

        
    def close(self):
        """
        Cleanup of the device
        """
        self.w.close()

        
    def device_changed(self,fname):
        """A function called by the nmea0183logger to notice a change

        """
        print('Something changed here:',fname)
        # Call the update function
        if(not(self.device_changed_function == None)):
            self.device_changed_function(fname)

#
#
# TODL Device
#
#
class todlDevice():
    def __init__(self, device_changed_function=None):
        """
        A device class for the turbulent ocean data logger (TODL)
        
        """
        self.device_changed_function = device_changed_function
        self.ready = False
        self.all_widgets = []
        print('Hallo init!')
        # Create a todl object
        self.status = 0 # The status
        # 0 initialised without a logger open
        # 1 logger at a serial port open
        self.todl = pymqds_todl.todlDataStream(logging_level='DEBUG')
        # Add a deque for raw serial data
        self.todl.deques_raw_serial.append(collections.deque(maxlen=5000))
        self.rawdata_deque = self.todl.deques_raw_serial[-1]
        # If the configuration changed call the _update function
        self.todl.init_notification_functions.append(self._update_status_information)

        self.deviceinfo = todlInfo()            # Deviceinfo widget
        self.todlConfig = todlConfig(todl = self.todl,deviceinfowidget = self.deviceinfo) # TODL Config widget
        # A flag if only one channel is used
        self.ONECHFLAG = False

        # Command stuff
        self.send_le = QtWidgets.QLineEdit()
        send_bu = QtWidgets.QPushButton('send')
        send_bu.clicked.connect(self.clicked_send_bu)

        # Show the raw data of the logger
        self._show_data_widget = QtWidgets.QWidget()
        self._show_data_layout = QtWidgets.QGridLayout(self._show_data_widget)
        self.show_textdata = QtWidgets.QPlainTextEdit()
        self.show_textdata.setReadOnly(True)
        self.show_textdata.setMaximumBlockCount(10000)
        self.check_show_textdata = QtWidgets.QCheckBox('Show data')
        self.check_show_textdata.setChecked(True)
        
        self._show_data_bu = QtWidgets.QPushButton('Show data')
        self._show_data_bu.clicked.connect(self._clicked_show_data_bu)
        self.show_textdata.appendPlainText("Here comes the logger rawdata ...\n ")
        self._show_data_close = QtWidgets.QPushButton('Close')
        self._show_data_close.clicked.connect(self._clicked_show_data_bu)
        # Textdataformat of the show_textdata widget 0 str, 1 hex
        self._textdataformat = 0 
        self.combo_format = QtWidgets.QComboBox()
        self.combo_format.addItem('utf-8')
        self.combo_format.addItem('hex')        
        self.combo_format.activated.connect(self._combo_format)
        self.show_comdata = QtWidgets.QPlainTextEdit()
        self.show_comdata.setReadOnly(True)

        # Command widgets
        self._show_data_layout.addWidget(self._show_data_close)
        self._show_data_layout.addWidget(QtWidgets.QLabel('Command'),1,0) # Command
        self._show_data_layout.addWidget(self.send_le,1,1,1,2) # Command
        self._show_data_layout.addWidget(send_bu,1,3) # Command
        self._show_data_layout.addWidget(QtWidgets.QLabel('Format'),2,0) # Command        
        self._show_data_layout.addWidget(self.combo_format,2,1)
        self._show_data_layout.addWidget(self.show_textdata,3,0,1,4)
        #self._show_data_layout.addWidget(self.show_comdata,1,1)
        
        
        
        #
        # An information, saving, loading and plotting widget
        #
        self._infosaveloadplot_widget = QtWidgets.QWidget()
        info_layout = QtWidgets.QGridLayout(self._infosaveloadplot_widget)
        self._recording_status = ['Record','Stop recording']        
        self._info_record_bu = QtWidgets.QPushButton(self._recording_status[0])
        self._info_record_info = QtWidgets.QLabel('Status: Not recording')
        self._info_plot_bu = QtWidgets.QPushButton('Plot')
        self._info_plot_bu.setEnabled(FLAG_PLOTXY)
        self._info_plot_bu.clicked.connect(self._plot_clicked)
        self._info_record_bu.clicked.connect(self._record_clicked)
        # Plot test
        self._info_plot_test_bu = QtWidgets.QPushButton('Plot test')
        self._info_plot_test_bu.clicked.connect(self._plot_test_clicked)
        self._info_plot_IMU_bu = QtWidgets.QPushButton('Plot IMU')
        self._info_plot_IMU_bu.clicked.connect(self._plot_test_clicked)                
        
        info_layout.addWidget(self._info_record_bu,0,2)
        info_layout.addWidget(self._info_record_info,1,2)
        info_layout.addWidget(self._info_plot_bu,0,1)
        info_layout.addWidget(self._info_plot_IMU_bu,1,0)        
        info_layout.addWidget(self._info_plot_test_bu,1,1)
        info_layout.addWidget(self._show_data_bu,0,0)        
        
        # 
        # Add a qtable for realtime data showing of voltage/packets number/counter
        # http://stackoverflow.com/questions/20797383/qt-fit-width-of-tableview-to-width-of-content
        # 
        self._ad_table = QtWidgets.QTableWidget()
        # http://stackoverflow.com/questions/14143506/resizing-table-columns-when-window-is-maximized
        #self._ad_table.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self._ad_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch) #pyqt5
        #self._ad_table.setMinimumSize(300, 300)
        #self._ad_table.setMaximumSize(300, 300)
        self._ad_table_setup()

        #
        # Add a table for the IMU
        # PH: This is a hack TODO, make this clean
        #
        self._IMU_table = QtWidgets.QTableWidget()
        #self._IMU_table.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self._IMU_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch) # pyqt5
        self._IMU_table_setup()
        
        #
        # Add a table for the Pyro
        # PH: This is a hack TODO, make this clean
        #
        self._O2_table = QtWidgets.QTableWidget()
        #self._O2_table.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self._O2_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch) # pyqt5        
        self._O2_table_setup()

        # Widget to collect all information
        self.disp_widget = QtWidgets.QWidget()
        self.disp_widget_layout = QtWidgets.QGridLayout(self.disp_widget)

        self.all_widgets.append(self.disp_widget)

        # Timer to update the bytes read information of the deviceinfowidget
        self.lcdtimer = QtCore.QTimer()
        self.lcdtimer.setInterval(100)
        self.lcdtimer.timeout.connect(self.poll_serial_bytes)
        self.lcdtimer.start()

        # For showing the raw data
        self.dequetimer = QtCore.QTimer()
        self.dequetimer.setInterval(100)
        self.dequetimer.timeout.connect(self.poll_deque)
        self.dequetimer.start()

        # Updating the Voltage table
        self.intraqueuetimer = QtCore.QTimer()
        self.intraqueuetimer.setInterval(50)
        self.intraqueuetimer.timeout.connect(self._poll_intraqueue)
        self.intraqueuetimer.start()        


        self.disp_widget_layout.addWidget(self.deviceinfo,1,0,1,3)
        #layout.addWidget(self._ad_choose_bu,3,1)        
        self.disp_widget_layout.addWidget(self._infosaveloadplot_widget,6,0,1,5)
        self.disp_widget_layout.addWidget(self._ad_table,4,0,2,3)
        self.disp_widget_layout.addWidget(self._IMU_table,4,3,2,2)
        self.disp_widget_layout.addWidget(self._O2_table,4,5,2,2)

        

    def setup(self,name):
        """Setup of the device

        """
        self.name = name
        print('Hallo setup!')
                # Source
        sources = ['serial','file','ip']
        
        self.setup_widget = QtWidgets.QWidget()
        w = self.setup_widget
        w.setWindowTitle('todl setup')
        self.combo_source = QtWidgets.QComboBox(w)
        for s in sources:
            self.combo_source.addItem(str(s))        

        # The layout of the setup widget with two rows
        self.layout_source_v = QtWidgets.QVBoxLayout(w)
        self.layout_source = QtWidgets.QHBoxLayout()
        self.layout_source_row2 = QtWidgets.QGridLayout()                
        self.layout_source_v.addLayout(self.layout_source)
        self.layout_source_v.addLayout(self.layout_source_row2)        

        # Serial interface stuff
        self.combo_serial = QtWidgets.QComboBox(w)
        self.combo_baud   = QtWidgets.QComboBox(w)
        for b in baud:
            self.combo_baud.addItem(str(b))

        self.combo_baud.setCurrentIndex(len(baud)-1)
        
        self.setup_close_bu = QtWidgets.QPushButton('Close')
        self.setup_close_bu.clicked.connect(w.close)
        self.serial_open_bu = QtWidgets.QPushButton('Search TODL')
        self.serial_open_bu.clicked.connect(self.clicked_serial_open_bu)

        self.serial_test_bu = QtWidgets.QPushButton('Test ports')
        self.serial_test_bu.clicked.connect(self.test_ports)        

        self._s4l_settings_bu = QtWidgets.QPushButton('Device Setup')
        self._s4l_settings_bu.setEnabled(False)
        self._s4l_settings_bu.clicked.connect(self._clicked_settings_bu)

        # File source
        self.button_open_file      = QtWidgets.QPushButton('Open file')
        self.button_open_file.clicked.connect(self.open_file)
        self.button_startstopread_file = QtWidgets.QPushButton('Start read')
        self.button_startstopread_file.clicked.connect(self.startstopreadfile)
        self.label_file_read_dt    = QtWidgets.QLabel('Read in intervals of [s]')
        self.spin_file_read_dt     = QtWidgets.QDoubleSpinBox()
        self.spin_file_read_dt.setValue(0.05)
        self.label_nbytes          = QtWidgets.QLabel('Read number of bytes per dt')        
        self.spin_file_read_nbytes = QtWidgets.QSpinBox()
        self.spin_file_read_nbytes.setRange(1, 1024)
        #self.freqsld.setSingleStep(10)
        self.spin_file_read_nbytes.setValue(400)

        # IP source
        self.text_ip = QtWidgets.QLineEdit()
        # Hack, this should be removed later
        self.text_ip.setText('192.168.236.18:28117')
        self._button_sockets_choices = ['Connect to IP','Disconnect from IP']
        self.button_open_socket = QtWidgets.QPushButton(self._button_sockets_choices[0])
        #self.button_open_socket.clicked.connect(self.clicked_open_socket)

        # This function shows or hides the widgets needed for the choosen source
        self.combo_source.currentIndexChanged.connect(self.get_source)
        # Do the layout of the source
        self.test_ports() # Looking for serial ports        
        self.get_source()


        
        w.show()

    def get_source(self):
        """
        Changes the source (serial, file or ip. TODO pymqdatastream) of the logger
        """
        # The source data layout (serial, files)
        widgets_serial = [ self.setup_close_bu, self.combo_source, self.serial_test_bu, self.combo_serial,
                           self.combo_baud, self.serial_open_bu ]
        widgets_file   = [ self.setup_close_bu,
                           self.combo_source,self.button_open_file,
                           self.button_startstopread_file,self.label_nbytes,
                           self.spin_file_read_nbytes,
                           self.label_file_read_dt,
                           self.spin_file_read_dt ]
        widgets_ip = [ self.setup_close_bu,
                       self.combo_source,self.text_ip,
                       self.button_open_socket ]        

        logger.debug('get_source()')
        data_source = str( self.combo_source.currentText() )
        self.layout_source_row2.addWidget(self.deviceinfo,0,0)

        # TODO: Rescale the widget after things are removed or added ....
        
        if(data_source == 'serial'):
            whide = widgets_file + widgets_ip
            for w in whide:
                try:
                    self.layout_source.removeWidget(w)
                    w.hide()
                except Exception as e:
                    print(str(e))
                    pass

            self.layout_source_row2.addWidget(self.todlConfig,1,0)
            self.todlConfig.show()            
            for w in widgets_serial:
                try:
                    self.layout_source.addWidget(w)
                    w.show()
                except Exception as e:
                    print(str(e))                    
                    pass
                
        elif(data_source == 'file'):
            whide = widgets_serial + widgets_ip
            try:
                self.layout_source_row2.removeWidget(self.todlConfig)
                self.todlConfig.hide()
            except:
                pass
            
            for w in whide:
                try:
                    self.layout_source.removeWidget(w)
                    w.hide()
                except:
                    pass

            for w in widgets_file:
                try:
                    self.layout_source.addWidget(w)
                    w.show()
                except:
                    pass

        elif(data_source == 'ip'):
            whide = widgets_serial + widgets_file                        
            for w in whide:
                try:
                    self.layout_source.removeWidget(w)
                    w.hide()
                except:
                    pass

            self.layout_source_row2.addWidget(self.todlConfig,1,0)
            self.todlConfig.show()            
            for w in widgets_ip:
                try:
                    self.layout_source.addWidget(w)
                    w.show()
                except:
                    pass

    def test_ports(self):
        """
        
        Look for serial ports

        """
        ports = serial_ports()
        # This could be used to pretest devices
        #ports_good = self.test_device_at_serial_ports(ports)
        ports_good = ports
        self.combo_serial.clear()
        for port in ports_good:
            self.combo_serial.addItem(str(port))

    def clicked_serial_open_bu(self):
        """Function to open a serial device
        """
        funcname = 'clicked_serial_open_bu()'
        t = self.serial_open_bu.text()
        print('Click ' + str(t))
        if True:
            if(t == 'Search TODL'):
                ser = str(self.combo_serial.currentText())
                b = int(self.combo_baud.currentText())
                print('Opening port' + ser + ' with baudrate ' + str(b))
                self.todl.add_serial_device(ser,baud=b)
                if(self.todl.status == 0): # Succesfull opened
                    if(self.todl.query_todllogger() == True):
                        self.deviceinfo.update(self.todl.device_info)
                        # Enable a settings button or if version 0.45 add a frequency combo
                        vers = float(self.todl.device_info['firmware'])
                        # The high speed 0.45 version 
                        if(vers == 0.45):
                            logger.debug('Opening Version 0.45 device setup')
                            self._s4l_settings_bu.close()
                            self._s4l_freq_combo = QtWidgets.QComboBox(self)
                            #self._s4l_freq_combo.setEnabled(True)                            
                            self._speeds_hz     = pymqds_todl.s4lv0_45_speeds_hz
                            for i,speed in enumerate(self._speeds_hz):
                                self._s4l_freq_combo.addItem(str(speed))

                            self.layout.addWidget(self._s4l_freq_combo,1,3)
                            self._ad_table.clear()                                                        
                            self._ad_table_setup_1ch()
                            self._s4l_freq_combo.currentIndexChanged.connect(self._freq_set_v045)
                            # TODO Have to resize the widget to have nicer data
                        # The general purpose 
                        elif(vers >= 0.70):
                            logger.debug('Opening Version 0.70+ device setup')
                            self._s4l_settings_bu.close()
                            if(True):
                                self._ad_table.clear()                                                        
                                self._ad_table_setup()
                        else:
                            self._s4l_settings_bu.setEnabled(True)
                            self._ad_table.clear()                            
                            self._ad_table_setup()                                            
                        #                            
                        #
                        self.serial_open_bu.setText('Open')
                else:
                    logger.warning('Could not open port:' + str(ser))
                    
            elif(t == 'Open'):
                #ser = str(self.combo_serial.currentText())
                #b = int(self.combo_baud.currentText())
                self.serial_open_bu.setText('Close')
                self._s4l_settings_bu.setEnabled(False)
                #self._s4l_freq_combo.setEnabled(False)                                            
                #print('Opening port' + ser + ' with baudrate ' + str(b))
                #self.todl.add_serial_device(ser,baud=b)
                self.todl.add_raw_data_stream()
                time.sleep(0.2)
                self.todl.query_todllogger()
                #self.todl.init_todllogger(adcs = [0,2,4])
                time.sleep(0.2)                
                self.todl.start_converting_raw_data()
                self.combo_serial.setEnabled(False)
                self.combo_baud.setEnabled(False)                
                self.status = 1
                # Call the device changed function to notice the gui
                # that the serial device is open
                self.device_changed(funcname)
            else:
                self.todl.stop_serial_data()
                self.todl.stop_converting_raw_data()
                self.serial_open_bu.setText('Search TODL')
                self.combo_serial.setEnabled(True)
                self.combo_baud.setEnabled(True)                                
                self.status = 0

        else:
            print('bad open close')


    def clicked_open_socket(self):
        """
        Opens a 
        """
        print('Open!')
        funcname = 'clicked_open_socket()'
        addrraw = str(self.text_ip.text())
        print(addrraw)
        try:
            addr = addrraw.split(':')[0]
            port = int(addrraw.split(':')[1])
        except:
            print('Enter proper address')
            return

        print(addr,port)
        if(self.button_open_socket.text() == self._button_sockets_choices[0]):
            self.todl.add_socket(addr,port)
            if(self.todl.status == 0): # Succesfull opened            
                time.sleep(0.5)
                if(True):                    
                    print('Query socket/device')
                    if(self.todl.query_todllogger() == True):
                        self.deviceinfo.update(self.todl.device_info)
                        self.button_open_socket.setEnabled(False)
                        self.text_ip.setEnabled(False)
                    else:
                        print('No device found!')
                        return

                if(True):
                    #self.todl.
                    self.todl.send_serial_data('stop\n')
                    time.sleep(0.1)                                                
                    self.todl.send_serial_data('stop\n')
                    time.sleep(0.2)                            
                    self.todl.send_serial_data('freq 200\n')
                    #self.todl.send_serial_data('freq 333\n')
                    time.sleep(0.2)                            
                    if(self.todl.query_todllogger() == True):
                        self.deviceinfo.update(self.todl.device_info)
                        self.print_serial_data = False
                        time.sleep(0.1)            
                        self.todl.send_serial_data('start\n')


                if(True):            
                    time.sleep(.5)
                    self.todl.add_raw_data_stream()
                    time.sleep(0.2)
                    self.todl.start_converting_raw_data()

                # Call the device changed function to notice the gui
                # that the device is open
                self.device_changed(funcname)

    def _clicked_settings_bu(self):
        """
        """
        logger.debug('Settings')
        
        print('Firmware' + self.todl.device_info['firmware'])
        self._settings_widget = todlConfig(self.todl)    
        self._settings_widget.show()

    def open_file(self):
        """
        Opens a datafile
        """
        logger.debug('Open file')
        fname = QtWidgets.QFileDialog.getOpenFileName(self.setup_widget, 'Select file','', "Turbulent Ocean Data Logger [todl] (*.todl);; CSV (*.csv);; All files (*)");
        print(fname)
        if(len(fname[0]) > 0):
            if(isinstance(fname, str)):
                fname = [fname]
            filename = ntpath.basename(fname[0])
            path = ntpath.dirname(fname[0])
            logger.debug('Open file:' + str(fname[0]))
            ret = self.todl.load_file(fname[0],start_read=False)
            if(ret):
                self.deviceinfo.update(self.todl.device_info)
                self.todl.add_raw_data_stream()
                self.todl.start_converting_raw_data()


    def startstopreadfile(self):
        """
        Starts or stops reading the data file
        """
        logger.debug('Starting reading the datafile')
        t = self.button_startstopread_file.text()
        if('Start' in t):
            print('Start reading')
            num_bytes = self.spin_file_read_nbytes.value()
            dt=self.spin_file_read_dt.value()
            self.todl.start_read_file(num_bytes = num_bytes, dt=dt)
            self.button_startstopread_file.setText('Stop reading')
        elif('Stop' in t):
            self.todl.stop_read_file()
            self.button_startstopread_file.setText('Start read')            


    def show_data(self):
        """
        Function to show the data
        """
        print('Show data')
        self.disp_widget.show()


    def _update_status_information(self):
        """
        """
        logger.debug('Update_status_information')
        self.deviceinfo.update(self.todl.device_info)

    def _ad_table_setup(self):
        """ Setup of the table
        """
        self._ad_table_ind_ch = []
        if 'adcs' in self.todl.device_info.keys():
            num_ltcs = len(self.todl.device_info['adcs'])
            ltc_name = [i for i in self.todl.device_info['adcs']]
            ch_seq = np.unique(np.asarray(self.todl.device_info['channel_seq']))
            # Create an index between the channel numbers and the columns
            self._ad_table_ind_ch = [ i for i in range(ch_seq.max()+1)]
            header_label = ['Name']
            for i in range(len(ch_seq)):
                self._ad_table_ind_ch[ch_seq[i]] = i+1
                header_label.append('Ch ' + str(ch_seq[i]))

            num_cols = len(ch_seq) + 1
        else:
            num_ltcs = 8
            num_cols = 4 + 1            
            ltc_name = [i for i in range(num_ltcs)]
            header_label = ['Name','Ch 0','Ch 1','Ch 2','Ch 3']            
            for i in range(4):
                self._ad_table_ind_ch.append(i+1)

        num_rows =  num_ltcs + 3                        
        self._ad_table.setColumnCount(num_cols)
        self._ad_table.setRowCount(num_rows)
        self._ad_table.verticalHeader().setVisible(False)
        self._ad_table.setItem(0,
                               0, QtWidgets.QTableWidgetItem( ' Packet number' ))
        self._ad_table.setItem(1,
                               0, QtWidgets.QTableWidgetItem( ' Counter' ))
        for i in range(0,num_ltcs):
            adname='LTC2442 ' + str(ltc_name[i])
            self._ad_table.setItem(i+2,
                                0, QtWidgets.QTableWidgetItem( adname ))        

        self._ad_table.setHorizontalHeaderLabels(header_label)
        # Make width and height of the table such that all entries can be seen
        vwidth = self._ad_table.verticalHeader().width()
        hwidth = self._ad_table.horizontalHeader().length()
        fwidth = self._ad_table.frameWidth() * 2
        #swidth = self._ad_table.style().pixelMetric(QtGui.QStyle.PM_ScrollBarExtent)
        self._ad_table.setFixedWidth(vwidth + hwidth + fwidth)
        self._ad_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        height = 0
        hheight = self._ad_table.horizontalHeader().height()
        for i in range(self._ad_table.rowCount()):
            height += self._ad_table.rowHeight(i)
            
        self._ad_table.setFixedHeight(height + hheight + fwidth)
        # Only select one item
        #self._ad_table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self._ad_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        # Add a right click menu to the table
        self._ad_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._ad_table.customContextMenuRequested.connect(self._table_menu)

    def _table_menu(self, event):
        """
        Handling right click menu of the table
        """
        # From here https://stackoverflow.com/questions/20930764/how-to-add-a-right-click-menu-to-each-cell-of-qtableview-in-pyqt
        # and here https://stackoverflow.com/questions/7782071/how-can-i-get-right-click-context-menus-for-clicks-in-qtableview-header
        #index = self.indexAt(event.pos())
        if self._ad_table.selectionModel().selection().indexes():
            for i in self._ad_table.selectionModel().selection().indexes():
                row, column = i.row(), i.column()
        menu = QtGui.QMenu()
        # an action for everyone
        print('HALLLLOO!',str(event),row,column)


    def _ad_table_setup_1ch(self):
        self.ONECHFLAG = True
        self._ad_table.clear()
        while (self._ad_table.rowCount() > 0):
            self._ad_table.removeRow(0)

        while (self._ad_table.columnCount() > 0):
            self._ad_table.removeColumn(0)
            
        self._ad_table.setColumnCount(2)
        self._ad_table.setRowCount(3)
        self._ad_table.verticalHeader().setVisible(False)
        self._ad_table.setItem(0,
                               0, QtWidgets.QTableWidgetItem( ' Packet number' ))
        self._ad_table.setItem(1,
                               0, QtWidgets.QTableWidgetItem( ' Counter' ))
        for i in range(0,1):
            adname='LTC2442 ' + str(i)
            self._ad_table.setItem(i+2,
                                0, QtWidgets.QTableWidgetItem( adname ))        

        self._ad_table.setHorizontalHeaderLabels(['Name','Ch'])
        # Make width and height of the table such that all entries can be seen
        vwidth = self._ad_table.verticalHeader().width()
        hwidth = self._ad_table.horizontalHeader().length()
        fwidth = self._ad_table.frameWidth() * 2
        #swidth = self._ad_table.style().pixelMetric(QtGui.QStyle.PM_ScrollBarExtent)
        self._ad_table.setFixedWidth(vwidth + hwidth + fwidth)
        self._ad_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        height = 0
        hheight = self._ad_table.horizontalHeader().height()
        for i in range(self._ad_table.rowCount()):
            height += self._ad_table.rowHeight(i)
            
        self._ad_table.setFixedHeight(height + hheight + fwidth)        
        print('Hallo!!!',self._ad_table.columnCount())
        print('Hallo!!!',self._ad_table.rowCount())

    def _IMU_table_setup(self):
        accname = ['x','y','z']
        self._IMU_table.setColumnCount(2)
        self._IMU_table.setRowCount(9)
        self._IMU_table.verticalHeader().setVisible(False)
        self._IMU_table.setItem(0,
                               0, QtWidgets.QTableWidgetItem( ' Packet number' ))
        self._IMU_table.setItem(1,
                               0, QtWidgets.QTableWidgetItem( ' Counter' ))

        self._IMU_table.setItem(2,
                               0, QtWidgets.QTableWidgetItem( ' Temp' ))        
        for i in range(0,3):
            adname='acc ' + accname[i]            
            self._IMU_table.setItem(i+3,
                                0, QtWidgets.QTableWidgetItem( adname ))

        for i in range(0,3):
            adname='gyro ' + accname[i]
            self._IMU_table.setItem(i+6,
                                0, QtWidgets.QTableWidgetItem( adname ))                    

        self._IMU_table.setHorizontalHeaderLabels(['Name','IMU 0'])
        if(False):
            # Make width and height of the table such that all entries can be seen
            vwidth = self._IMU_table.verticalHeader().width()
            hwidth = self._IMU_table.horizontalHeader().length()
            fwidth = self._IMU_table.frameWidth() * 2
            #swidth = self._IMU_table.style().pixelMetric(QtGui.QStyle.PM_ScrollBarExtent)
            self._IMU_table.setFixedWidth(vwidth + hwidth + fwidth)
            self._IMU_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            height = 0
            hheight = self._IMU_table.horizontalHeader().height()
            for i in range(self._IMU_table.rowCount()):
                height += self._IMU_table.rowHeight(i)

            self._IMU_table.setFixedHeight(height + hheight + fwidth)

    def _O2_table_setup(self):
        self._O2_table.setColumnCount(2)
        self._O2_table.setRowCount(4)
        self._O2_table.verticalHeader().setVisible(False)
        self._O2_table.setItem(0,
                               0, QtWidgets.QTableWidgetItem( ' Counter' ))

        self._O2_table.setItem(1,
                               0, QtWidgets.QTableWidgetItem( ' dphi' ))

        self._O2_table.setItem(2,
                               0, QtWidgets.QTableWidgetItem( ' umol' ))                

        self._O2_table.setHorizontalHeaderLabels(['Name','O2 0'])


    def clicked_send_bu(self):
        data = self.send_le.text()
        print('Sending ' + str(data))
        self.todl.send_serial_data(str(data) + '\n')
        time.sleep(0.2)
        # Update the command history
        self.show_comdata.clear()
        for com in self.todl.commands:
            self.show_comdata.appendPlainText(str(com))

    def _freq_set_v045(self):
        logger.debug('_freq_set_v045')
        speed_str = self._s4l_freq_combo.currentText()
        #self.todl.stop_converting_raw_data()
        self.print_serial_data = True                
        self.todl.send_serial_data('stop\n')
        self.todl.send_serial_data('stop\n')
        self.todl.send_serial_data('freq ' + str(speed_str) + '\n')
        self.todl.send_serial_data('format 4\n')
        time.sleep(0.1)        
        if(self.todl.query_todllogger() == True):
            self.deviceinfo.update(self.todl.device_info)
            self.print_serial_data = False
            time.sleep(0.1)            
            self.todl.send_serial_data('start\n')
            #self.todl.start_converting_raw_data()                    
        else:
            logger.warning('Bad, frequency changed did not work out. ')

    def _freq_set(self):
        logger.debug('_freq_set')
        speed_str = self._s4l_freq_combo.currentText()
        #self.todl.stop_converting_raw_data()
        self.print_serial_data = True                
        self.todl.send_serial_data('stop\n')
        self.todl.send_serial_data('stop\n')
        self.todl.send_serial_data('freq ' + str(speed_str) + '\n')
        time.sleep(0.1)        
        if(self.todl.query_todllogger() == True):
            self.deviceinfo.update(self.todl.device_info)
            self.print_serial_data = False
            time.sleep(0.1)            
            self.todl.send_serial_data('start\n')
            #self.todl.start_converting_raw_data()                    
        else:
            logger.warning('Bad, frequency changed did not work out. ')                        


    def poll_serial_bytes(self):
        self.deviceinfo.update_bytes(self.todl.bytes_read, self.todl.bytes_read_avg)
        #self.bytesreadlcd.display(self.todl.bytes_read)
        #self.bytesspeed.setText(str(self.todl.bytes_read_avg))
        pass        


    def poll_deque(self):
        """ Reading the rawdata
        """
        while(len(self.rawdata_deque) > 0):
            data = self.rawdata_deque.pop()
            if(self.check_show_textdata.isChecked()):            
                if(self._textdataformat == 0):
                    try:
                        # This works for python3
                        data_str = data.decode('utf-8')
                    except UnicodeDecodeError:
                        ## This works for python3.5+                        
                        #data_str = data.hex()
                        # This works for python3.1+
                        data_str = str(binascii.hexlify(data),'ascii')
                        
                elif(self._textdataformat == 1):
                    ## This works for python3.5+
                    #data_str = data.hex()
                    # This works for python3.1+
                    data_str = str(binascii.hexlify(data),'ascii')


                self.show_textdata.appendPlainText(str(data_str))

                
    def _clicked_show_data_bu(self):
        """
        """
        sender = self.sender()
        t = self._show_data_bu.text()
        print('Click ' + str(t))
        if True:
            if(t == 'Show data'):
                self._show_data_widget_opened = self._show_data_widget
                self._show_data_widget_opened.show()
                self._show_data_bu.setText('Hide data')
            if(t == 'Hide data' or sender == self._show_data_close):
                self._show_data_widget_opened.close()
                self._show_data_bu.setText('Show data')                


    def _poll_intraqueue(self):
        """Polling the intraque , and updates and displays the data in
        self._ad_table
        """
        global counter_test
        counter_test += 1
        data = []
        showL = True
        showA = True
        showO = True
        show_channels = [True,True,True,True] # Show each channel once during the
        # Get all data        
        while(len(self.todl.intraqueue) > 0):
            data = self.todl.intraqueue.pop()
            if(data['type'] == 'Stat'):
                self.deviceinfo.update_status_packet(data)
                
                
            if(len(data)>0):
                # LTC channel data
                if((data['type']=='L') and showL):
                    # Get channel                    
                    ch = data['ch']
                    ind_col = self._ad_table_ind_ch[ch]
                    if(show_channels[ch]):
                        show_channels[ch] = False
                        #showL = False
                        if(self.ONECHFLAG):
                            ch = 0
                        num = data['num']
                        ct = data['t']
                        V = data['V']
                        # Packet number            
                        item = QtWidgets.QTableWidgetItem(str(num))
                        self._ad_table.setItem(0, ind_col, item)
                        # Counter
                        item = QtWidgets.QTableWidgetItem(str(ct))
                        self._ad_table.setItem(1, ind_col, item)
                        # Update all LTC data of that channel
                        #for n,i in enumerate(self.todl.flag_adcs):
                        for n,i in enumerate(self.todl.device_info['adcs']):
                            item = QtWidgets.QTableWidgetItem(str(V[n]))
                            self._ad_table.setItem(n+2, ind_col, item )

                # IMU data                        
                if((data['type']=='A') and showA):
                    showA = False
                    num = data['num']
                    ct = data['t']
                    # Packet number            
                    item = QtWidgets.QTableWidgetItem(str(num))
                    self._IMU_table.setItem(0, 1, item)
                    # Counter
                    item = QtWidgets.QTableWidgetItem(str(ct))
                    self._IMU_table.setItem(1, 1, item)
                    tabdata = data['T']
                    item = QtWidgets.QTableWidgetItem(str(tabdata))                    
                    self._IMU_table.setItem(2, 1, item)                    
                    for i in range(3):
                        tabdata = data['acc'][i]
                        item = QtWidgets.QTableWidgetItem(str(tabdata))
                        self._IMU_table.setItem(i+3, 1, item )
                    for i in range(3):
                        tabdata = data['gyro'][i]
                        item = QtWidgets.QTableWidgetItem(str(tabdata))
                        self._IMU_table.setItem(i+6, 1, item )


                # Oxygen data            
                if((data['type']=='O') and showO):
                    showO = False
                    #data_packet['phi']  = data_dphi 
                    #data_packet['umol'] = data_umol
                    ct = data['t']
                    # Packet number            
                    item = QtWidgets.QTableWidgetItem(str(ct))
                    self._O2_table.setItem(0, 1, item)
                    tabdata = data['phi']
                    item = QtWidgets.QTableWidgetItem(str(tabdata))                    
                    self._O2_table.setItem(1, 1, item)
                    tabdata = data['umol']
                    item = QtWidgets.QTableWidgetItem(str(tabdata))                    
                    self._O2_table.setItem(2, 1, item)                                                            
                    

        # Update the recording file status as well (addding file size)
        t = self._info_record_bu.text()
        if(t == self._recording_status[1]):
            self._info_record_info.setText('Status: Logging to file  '
                        + self.filename_log  + ' ( ' + str(self.todl.logfile_bytes_wrote)
                                           + ' bytes written)')
            

    def _combo_format(self):
        """
        """
        f = self.combo_format.currentText()
        if(f == 'utf-8'):
            self._textdataformat = 0
        if(f == 'hex'):
            self._textdataformat = 1

        print(self._textdataformat)

    def _plot_clicked(self):
        """
        
        Starts a pyqtgraph plotting process

        """

        logger.debug('Plotting the streams')
        # http://stackoverflow.com/questions/29556291/multiprocessing-with-qt-works-in-windows-but-not-linux
        # this does not work with python 2.7 
        multiprocessing.set_start_method('spawn',force=True)
        addresses = []
        for stream in self.todl.Streams:
            print(stream.get_family())
            if(stream.get_family() == "todl adc"):
                addresses.append(self.todl.get_stream_address(stream))
                
        self._plotxyprocess = multiprocessing.Process(target =_start_pymqds_plotxy,args=(addresses,))
        self._plotxyprocess.start()

    def _plot_test_clicked(self):
        """
        
        Starts a pyqtgraph plotting process

        """
        sender = self.sender()
        t = sender.text()
        logger.debug('Plotting the streams')
        plot_IMU = False
        if('IMU' in t):
            logger.debug('Plotting IMU')
            plot_IMU = True
        else:
            logger.debug('Plotting test')

        # http://stackoverflow.com/questions/29556291/multiprocessing-with-qt-works-in-windows-but-not-linux
        # this does not work with python 2.7 
        multiprocessing.set_start_method('spawn',force=True)
        addresses = []
        graphs = []
        dstreams = []
        dstreams_IMU = []
        dstreams_O2 = []
        
        iIMU = 0
        for stream in self.todl.Streams:
            print(stream.get_family())
            if(stream.get_family() == "todl adc"):
                addresses.append(self.todl.get_stream_address(stream))
                dstream = {}
                dstream['address'] = addresses[-1]
                dstream['ind_x'] = 1
                dstream['ind_y'] = 2
                dstream['nth_point'] = 1
                dstreams.append(dstream)

            if(stream.get_family() == "todl IMU"):
                addresses.append(self.todl.get_stream_address(stream))
                for i in range(3):
                    dstream = {}                
                    dstream['address'] = addresses[-1]
                    dstream['ind_x'] = 1
                    dstream['ind_y'] = 3 + iIMU
                    iIMU += 1
                    dstream['nth_point'] = 1
                    dstreams_IMU.append(dstream)
                    
            if(stream.get_family() == "todl O2"):
                addresses.append(self.todl.get_stream_address(stream))
                dstream = {}                
                dstream['address'] = addresses[-1]
                dstream['ind_x'] = 1
                dstream['ind_y'] = 2
                dstream['nth_point'] = 1
                dstreams_O2.append(dstream)
                
        if(plot_IMU):
            graphs = [[dstreams_IMU[0]],[dstreams_IMU[1]],[dstreams_IMU[2]]]            
        else:
            graphs = [[dstreams[0]],[dstreams[1]],dstreams_O2]            
            
        self._plotxyprocess = multiprocessing.Process(target =_start_pymqds_plotxy_test,args=(graphs,))
        self._plotxyprocess.start()        

        
    def _record_clicked(self):
        """
        
        Starts a recording process ( )

        """
        

        t = self._info_record_bu.text()
        logger.debug('Click ' + str(t))
        if(t == self._recording_status[0]):
            print('Record')
            #self._show_data_widget
            fname = QtWidgets.QFileDialog.getSaveFileName(self._show_data_widget, 'Select file','', "CSV (*.csv);; All files (*)");
            if(len(fname[0]) > 0):
                print(fname)
                filename = ntpath.basename(fname[0])
                path = ntpath.dirname(fname[0]) 
                fname_end = fname[1].split('*.')[-1]
                fname_end = fname_end.replace(')','')
                if( fname_end in filename ):
                    print( fname_end + ' already defined')
                else:
                    filename = filename + '.' + fname_end

                filename_full = path + '/' +filename
                self.filename_log = filename
                self._info_record_info.setText('Status: logfile: ' + self.filename_log)
                # Starting the logging:
                self.todl.log_serial_data(filename_full)
                self._info_record_bu.setText(self._recording_status[1])
        if(t == self._recording_status[1]):
            print('Stop record')            
            ret = self.todl.stop_log_serial_data()
            self._info_record_bu.setText(self._recording_status[0])
            self._info_record_info.setText('Status: Stopped logging to file  '
                        + self.filename_log  + ' ( ' + str(self.todl.logfile_bytes_wrote)
                                           + ' bytes written)')            
            
        # The more complex slogger object, disable for the moment
        if False:
            if(t == self._recording_status[0]):
                print('Record')            
                fname = QtWidgets.QFileDialog.getSaveFileName(self._show_data_widget, 'Select file','', "UBJSON (*.ubjson);; All files (*)");
                if(len(fname[0]) > 0):
                    self._info_record_info.setText('Status: logfile: ' + fname[0])
                    self.loggerDS = pymqdatastream.slogger.LoggerDataStream(logging_level = logging.DEBUG, filename = fname[0], name = 'todl logger')
                    logstream = self.loggerDS.log_stream(self.todl.raw_stream)
                    logstream = self.loggerDS.log_stream(self.todl.conv_stream)
                    print('Start write thread')
                    self.loggerDS.start_write_data_thread()
                    self._info_record_bu.setText(self._recording_status[1])
            if(t == self._recording_status[1]):
                print('Stop record')            
                ret = self.loggerDS.stop_poll_data_thread()
                self._info_record_bu.setText(self._recording_status[0])
                
                
    def add_nmea0183logger(self,nmea0183logger):
        """Adds a nmea0183logger to the device. This is basically used to set the
        time with the GPS-time instead of the PC-time

        """
        logger.debug('add_nmea0183logger()')
        self.nmea0183logger = nmea0183logger
        
        
    def close(self):
        """
        Cleanup of the device
        """
        for w in self.all_widgets:
            w.close()

        self.disp_widget.close()
        self.setup_widget.close() # Closing the TODL setup widget

        
    def device_changed(self,fname):
        """A function to notice a change

        """
        print('Something changed here:',fname)
        # Call the update function
        if(not(self.device_changed_function == None)):
            self.device_changed_function(fname)        



#
#
# Time widget
#
#
class timeWidget(QtWidgets.QWidget):
    """A time widget showing system time as well as additional clocks as e.g. GPS Time

    """
    def __init__(self):
        
        QtWidgets.QWidget.__init__(self)
        self.nmea0183logger = None
        self.lab_nmea0183logger = [] # Time labels for the nmealogger        
        self.time_widget_layout = QtWidgets.QGridLayout(self)
        self.lab_time_system = QtWidgets.QLabel('Systemtime (UTC): ')
        self.lab_showtime_system = QtWidgets.QLabel('')
        local_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Z')        
        self.lab_time_system_local = QtWidgets.QLabel('Systemtime (local)')
        self.lab_showtime_system_local = QtWidgets.QLabel('')                
        dev_rem = QtWidgets.QPushButton('Remove')

        self.time_widget_layout.addWidget(self.lab_time_system,0,0)
        self.time_widget_layout.addWidget(self.lab_showtime_system,1,0)
        self.time_widget_layout.addWidget(self.lab_time_system_local,2,0)
        self.time_widget_layout.addWidget(self.lab_showtime_system_local,3,0)
        #self.time_widget_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.ind_gps = 4

        # Create a timer to update the time
        self.time_timer = QtCore.QTimer(self)
        self.time_timer.setInterval(50)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start()

        
    def update_time(self):
        time_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
        time_str = time_str[:-5]
        self.lab_showtime_system.setText(time_str)        
        time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        time_str = time_str[:-5]
        self.lab_showtime_system_local.setText(time_str)
        if(self.nmea0183logger != None):
            for i,s in enumerate(self.nmea0183logger.serial):
                if('datetime' in s['parsed_data'].keys()):
                    lab2 = self.lab_nmea0183logger[i*2+1] # Get the right label
                    time_str = s['parsed_data']['datetime'].strftime('%Y-%m-%d %H:%M:%S')
                    lab2.setText(time_str)

                    
    def add_nmea0183logger(self,nmea0183logger):
        """Add a nmea0183logger to the widget, to show as well GPS time

        """
        print('add nmea0183logger()')
        for s in nmea0183logger.serial:
            print(s)
            lab1 = QtWidgets.QLabel(s['device_name'])
            lab2 = QtWidgets.QLabel('XXX')
            self.lab_nmea0183logger.append(lab1)
            self.lab_nmea0183logger.append(lab2)            
            self.time_widget_layout.addWidget(lab1,self.ind_gps,0)
            self.time_widget_layout.addWidget(lab2,self.ind_gps+1,0)            
            self.ind_gps +=2
            #QtWidgets.QLabel('Systemtime (UTC): ')

        # Do this in the end otherwise the QTimer could call the update function already
        self.nmea0183logger = nmea0183logger
        

    def rem_nmea0183logger(self):
        """Removes the nmealogger from the time Widget

        """
        print('rem nmea0183logger()')
        self.nmea0183logger = None
        for w in self.lab_nmea0183logger:
            self.time_widget_layout.removeWidget(w)
            w.deleteLater()

        self.lab_nmea0183logger = []
        self.ind_gps = 4



#
#
# The main window
#
#
class todlMainWindow(QtWidgets.QMainWindow):
    """The main interface of the TODL-GUI. Here the user can add and setup
    devices as GPS and TODL.
    """
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.all_widgets = []
        self.devices = []        
        
        mainMenu = self.menuBar()
        self.setWindowTitle("Turbulent Ocean Data Logger")
        #self.setWindowIcon(QtGui.QIcon('logo/pymqdatastream_logo_v0.2.svg.png'))
        extractAction = QtWidgets.QAction("&Quit", self)
        extractAction.setShortcut("Ctrl+Q")
        extractAction.setStatusTip('Closing the program')
        extractAction.triggered.connect(self.close_application)

        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(extractAction)
        
        self.statusBar()

        self.mainwidget = QtWidgets.QWidget()
        self.layout = QtWidgets.QGridLayout(self.mainwidget)
        # Create the time widget
        self.setup_time()
        # Create the device setup widget
        self.setup_devices()
        ## Create the info widget        
        #self.info_devices()
        # Create the show widget                
        self.show_devices()

        # Main tasks for the main layout
        self.tasks = []
        self.tasks.append({'name':'Time','widget':self.time_widget})        
        self.tasks.append({'name':'Devices','widget':self.device_setup_widget})
        #self.tasks.append({'name':'Info','widget':self.device_info_widget})
        self.tasks.append({'name':'Show','widget':self.device_show_widget})        
        self.tasks.append({'name':'Plot','widget':QtWidgets.QPushButton('Plot data')})
        self.tasks.append({'name':'Quit','widget':QtWidgets.QPushButton('Quit')})
        self.tasks[-1]['widget'].clicked.connect(self.close_application)

        # The main layout
        # Add all tasks
        for i,task in enumerate(self.tasks):
            self.layout.addWidget(task['widget'],i,3)
            
        
        self.setCentralWidget(self.mainwidget)
        
        self.show()


    def setup_time(self):
        """
        Create a time and date widget
        """
        self.time_widget        = timeWidget()
        w = self.time_widget
        self.all_widgets.append(w)
        



    def setup_devices(self):
        """
        Adding and removing functions for the device setup
        """
        self.device_setup_widget        = QtWidgets.QWidget()
        w = self.device_setup_widget
        self.all_widgets.append(w)        
        self.device_setup_widget_layout = QtWidgets.QGridLayout(self.device_setup_widget)
        #cl = QtWidgets.QPushButton('Close')
        #cl.clicked.connect(self.device_setup_widget.close)

        dev_add = QtWidgets.QPushButton('Add')
        dev_add.clicked.connect(self.add_devices)
        dev_rem = QtWidgets.QPushButton('Remove')
        dev_rem.setEnabled(False)
        dev_rem.clicked.connect(self.rem_devices)        

        self.combo_dev_add     = QtWidgets.QComboBox(w)
        self.combo_dev_rem     = QtWidgets.QComboBox(w)        

        for d in config['devices']:
            devname = list(d)[0]
            self.combo_dev_add.addItem(devname)

        b = QtWidgets.QPushButton('Devices')
        b.setEnabled(False)
        self.device_setup_widget_layout.addWidget(b,0,0,1,2)
        self.device_setup_widget_layout.addWidget(self.combo_dev_add,1,0)
        self.device_setup_widget_layout.addWidget(dev_add,1,1)
        self.device_setup_widget_layout.addWidget(self.combo_dev_rem,2,0)
        self.device_setup_widget_layout.addWidget(dev_rem,2,1)        
        #self.device_setup_widget_layout.addWidget(cl,1,0)
        self.device_setup_widget.show()

        
    def add_devices(self):
        """

        Looks in the configuration for devices and initializing that
        device object with the appropriate functions

        """
        dev = str( self.combo_dev_add.currentText() )
        print('Hallo add: ' + dev)
        for d in config['devices']: # Search for the config entry
            devname = list(d)[0]
            if(devname == dev):
                print('Found device ... with object name ' + str(d[devname]['object']))
                obj = str(d[devname]['object'])
                #tmp = getattr(globals(),'todlDevice')

                # Call the object of the device and give the
                # device_changed function to allow this gui to be
                # notified whenever the device has been changed
                # (added, removed opened)
                deviceobj = globals()[obj](self.device_changed)
                devicename = self.combo_dev_add.currentText()
                deviceobj.setup(name = devicename)

                self.devices.append(deviceobj)
                
        #type
        #SubClass = type('SubClass', (BaseClass,), {'set_x': set_x})


    def device_changed(self,fname=None):
        """This function is given as a callback to the devices to notify if
        something changed. This is an important key function of the
        object as it is interconnecting the individual device. TODO:
        Think about a smart way to connect the devices. At the moment
        it is hardcoded.

        """
        print('Device changed function')
        print('Our devices are',self.devices)

        # Connect GPS with 
        for d in self.devices:
            if(type(d) is gpsDevice):
                logger.debug('Found a GPS device')
                # Found a GPS device, loop through all devices again
                # and search for todlDevice
                # Add to the time widget
                if 'add_serial_device()' in fname:
                    self.time_widget.rem_nmea0183logger()                    
                    self.time_widget.add_nmea0183logger(d.nmea0183logger)
                elif 'add_tcp_stream()'  in fname:
                    self.time_widget.rem_nmea0183logger()                    
                    self.time_widget.add_nmea0183logger(d.nmea0183logger)
                # Check if a NMEA0183 GPS serial device has been removed
                elif 'rem_serial_device()' in fname:
                    self.time_widget.rem_nmea0183logger()
                    self.time_widget.add_nmea0183logger(d.nmea0183logger)

                for d2 in self.devices:
                    if(type(d) is todlDevice):
                        logger.debug('Found a todl, adding the GPS')
                        d2.add_nmea0183logger(d)
                        
            else:
                pass
                #print('Device',d)


        self.update_show_devices()

                
    def rem_devices(self):
        """
        Dummy function for removing devices
        """
        pass
        

    def info_devices(self):
        """
        Create a QWidget with for calling the info function of the device
        """
        self.device_info_widget        = QtWidgets.QWidget()
        w = self.device_setup_widget
        self.all_widgets.append(w)        
        self.device_info_widget_layout = QtWidgets.QGridLayout(self.device_info_widget)

        dev_info = QtWidgets.QPushButton('Open Info')
        dev_info.clicked.connect(self.info_devices)
        dev_info.setEnabled(False)

        self.combo_dev_info     = QtWidgets.QComboBox(w)

        for d in config['devices']:
            devname = list(d)[0]
            self.combo_dev_info.addItem(devname)

        b = QtWidgets.QPushButton('Info')
        b.setEnabled(False)
        self.device_info_widget_layout.addWidget(b,0,0,1,2)
        self.device_info_widget_layout.addWidget(self.combo_dev_info,1,0)
        self.device_info_widget_layout.addWidget(dev_info,1,1)
        self.device_info_widget.show()


    def show_devices(self):
        """
        Create a QWidget with for calling the show_data function of the device. 
        The device widget usually creates a widget
        """
        self.device_show_widget        = QtWidgets.QWidget()
        w = self.device_setup_widget
        self.all_widgets.append(w)        
        self.device_show_widget_layout = QtWidgets.QGridLayout(self.device_show_widget)

        self.bu_dev_show = QtWidgets.QPushButton('Open Show')
        self.bu_dev_show.clicked.connect(self.clicked_show_devices)
        self.bu_dev_show.setEnabled(False)

        self.combo_dev_show     = QtWidgets.QComboBox(w)

        b = QtWidgets.QPushButton('Show')
        b.setEnabled(False)
        self.device_show_widget_layout.addWidget(b,0,0,1,2)
        self.device_show_widget_layout.addWidget(self.combo_dev_show,1,0)
        self.device_show_widget_layout.addWidget(self.bu_dev_show,1,1)
        self.device_show_widget.show()


    def update_show_devices(self):
        """ Whenever a new device has been added or removed, call this function to update the show devices list
        """

        self.combo_dev_show.clear()
        
        for d in self.devices:
            self.combo_dev_show.addItem(d.name)


        if(len(self.devices) > 0):
            self.bu_dev_show.setEnabled(True)
        else:
            self.bu_dev_show.setEnabled(False)
            
        #for d in config['devices']:
        #    devname = list(d)[0]
        #    self.combo_dev_show.addItem(devname)


    def clicked_show_devices(self):
        """ Calls the show function of the device choosen
        """
        devname = str( self.combo_dev_show.currentText() )
        print('Show data of device:' + devname)
        
        for d in self.devices:
            if(d.name == devname):
                d.show_data()



    def close_application(self):
        logger.debug('Goodbye!')

        for w in self.devices:
            w.close()        

        for w in self.all_widgets:
            w.close()
        # Closing potentially open widgets
        try:
            self._show_data_widget_opened.close()
        except:
            pass

        try:
            self._ad_widget.close()
        except:
            pass

        try:
            self._IMU_widget.close()
        except:
            pass        

        try:
            self._settings_widget.close()
        except:
            pass

        try:
            self._plotxyprocess.stop()
        except:
            pass            
            
        self.close()



            


                
# If run from the command line
def main():
    print(sys.version_info)
    app = QtWidgets.QApplication(sys.argv)
    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()
    window = todlMainWindow()
    # Resize the window
    #window.resize(width-100,2*height/3)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
