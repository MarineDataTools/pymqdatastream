#!/usr/bin/env python3

#
#
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

# Get a standard configuration
from pkg_resources import Requirement, resource_filename
filename = resource_filename(Requirement.parse('pymqdatastream'),'pymqdatastream/connectors/sam4log/sam4log_config.yaml')
filename_version = resource_filename(Requirement.parse('pymqdatastream'),'pymqdatastream/VERSION')


with open(filename_version) as version_file:
    version = version_file.read().strip()

print(filename_version)
print(version)    

with open(filename) as config_file:
    config = yaml.load(config_file)
    print(config)
    
    

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqds_gui_sam4log')
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
    
import pymqdatastream.connectors.sam4log.pymqds_sam4log as pymqds_sam4log
from pymqdatastream.utils.utils_serial import serial_ports, test_serial_lock_file, serial_lock_file


counter_test = 0

            
# Serial baud rates
baud = [300,600,1200,2400,4800,9600,19200,38400,57600,115200,576000,921600]


class sam4logInfo(QtWidgets.QWidget):
    """
    Widget display status informations of a sam4log device
    """
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.f_version = QtWidgets.QLabel('Firmware: ?')
        self.b_version = QtWidgets.QLabel('Board: ?')
        self.adcs = QtWidgets.QLabel('ADCS: ?')       
        self.ch_seq = QtWidgets.QLabel('Channels: ?')
        self.data_format = QtWidgets.QLabel('Format: ?')
        self.freq = QtWidgets.QLabel('Conv. freq: ?')             
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.b_version)
        layout.addWidget(self.f_version)
        layout.addWidget(self.adcs)
        layout.addWidget(self.ch_seq)
        layout.addWidget(self.data_format)
        layout.addWidget(self.freq)        
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
            

        freqstr = "Conv. freq: " + str(status['freq']) + ' [Hz]'
        
        self.b_version.setText(boardstr)
        self.f_version.setText(firmstr)
        self.ch_seq.setText(chstr)
        self.adcs.setText(adcstr)
        self.data_format.setText(formatstr)
        self.freq.setText(freqstr)        




class sam4logConfig(QtWidgets.QWidget):
    """
    Configuration widget for the sam4log
    """
    # Conversion speeds of the device

    def __init__(self,sam4log=None):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QGridLayout()

        # Conversion speed
        self._convspeed_combo = QtWidgets.QComboBox(self)
        # v0.4 speeds
        self.speeds        = pymqds_sam4log.s4lv0_4_speeds
        self.speeds_hz_adc = pymqds_sam4log.s4lv0_4_speeds_hz_adc
        self.speeds_td     = pymqds_sam4log.s4lv0_4_speeds_td
        self.speeds_hz     = pymqds_sam4log.s4lv0_4_speeds_hz
        for i,speed in enumerate(self.speeds):
            speed_hz = 'f: ' + str(self.speeds_hz[i]) + \
                       ' Hz (f ADC:' + str(self.speeds_hz_adc[i]) + ' Hz)'
            self._convspeed_combo.addItem(str(speed_hz))        

        # Data format
        self.formats =     [2              , 3   , 4                            ]
        self.formats_str = ['binary (cobs)','csv', 'binary (cobs, reduced size)']
        self._dataformat_combo = QtWidgets.QComboBox(self)
        for i,dformat in enumerate(self.formats):
            format_str = str(dformat) + ' ' + self.formats_str[i]
            self._dataformat_combo.addItem(format_str)        



        self._query_bu = QtWidgets.QPushButton('Query')
        self._query_bu.clicked.connect(self._query)
        self._ad_apply_bu = QtWidgets.QPushButton('Send to device')
        self._ad_apply_bu.clicked.connect(self._setup_device)
        self._ad_close_bu = QtWidgets.QPushButton('Close')
        self._ad_close_bu.clicked.connect(self._close)

        # Create an adc checkbox widget
        self._ad_widget_check = QtWidgets.QWidget()
        ad_layoutV = QtWidgets.QHBoxLayout(self._ad_widget_check)


        self._ad_check = []        
        for i in range(8):
            ad_check = QtWidgets.QCheckBox('AD ' + str(i))
            self._ad_check.append(ad_check)
            ad_layoutV.addWidget(ad_check)


        # Create a channel sequence widget
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


        self.deviceinfo = sam4logInfo()


        # The main layout
        layout.addWidget(QtWidgets.QLabel('Set speed'),0,0)
        layout.addWidget(self._convspeed_combo,0,1)
        layout.addWidget(QtWidgets.QLabel('Set data format'),0,2)
        layout.addWidget(self._dataformat_combo,0,3)
        layout.addWidget(QtWidgets.QLabel('Choose LTC2442 ADCS '),1,0)
        layout.addWidget(self._ad_widget_check,2,0,1,4)
        layout.addWidget(QtWidgets.QLabel('Define channel sequence'),3,0)
        layout.addWidget(self._ad_seq_check,4,0,1,4)
        layout.addWidget(self.deviceinfo,5,0,1,4)
        layout.addWidget(self._query_bu,6,0)
        layout.addWidget(self._ad_apply_bu,6,1)        
        layout.addWidget(self._ad_close_bu,6,2)


        self.setLayout(layout)

        print('updating')
        # TODO do something if there is nothing
        self.sam4log = sam4log
        self._update_status()
        self.deviceinfo.update(self.sam4log.device_info)


    def _update_status(self):
        """
        Updates all the information buttons
        """
        
        status = self.sam4log.device_info
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
        speed_str = self._convspeed_combo.currentText()
        ind = self._convspeed_combo.currentIndex()
        speed_num = self.speeds[ind]
        logger.debug('_setup_device(): Setting speed to ' + str(speed_str)\
                     + ' num:' + str(speed_num))

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
        print('init sam4logger')
        self.sam4log.init_sam4logger(adcs = adcs,channels=chs,speed=speed_num,data_format=3)
        self._update_status()
        self.deviceinfo.update(self.sam4log.device_info)        

    def _query(self):
        self.sam4log.query_sam4logger()
        self._update_status()
        self.deviceinfo.update(self.sam4log.device_info)

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
#
#
class sam4logDevice():
    def __init__(self):
        self.ready = False
        print('Hallo init!')

    def setup(self):
        """
        Setup of the device
        """
        print('Hallo setup!')
                # Source
        sources = ['serial','file','ip']
        
        self.setup_widget = QtWidgets.QWidget()
        w = self.setup_widget
        w.setWindowTitle('sam4log setup')
        self.combo_source = QtWidgets.QComboBox(w)
        for s in sources:
            self.combo_source.addItem(str(s))        
            
        
        self.layout_source = QtWidgets.QHBoxLayout(w)
        # Serial interface stuff
        self.combo_serial = QtWidgets.QComboBox(w)
        self.combo_baud   = QtWidgets.QComboBox(w)
        for b in baud:
            self.combo_baud.addItem(str(b))

        self.combo_baud.setCurrentIndex(len(baud)-1)
        self.serial_open_bu = QtWidgets.QPushButton('Query')
        self.serial_open_bu.clicked.connect(self.clicked_open_bu)

        self.serial_test_bu = QtWidgets.QPushButton('Test ports')
        self.serial_test_bu.clicked.connect(self.test_ports)        

        self._s4l_settings_bu = QtWidgets.QPushButton('Device Setup')
        self._s4l_settings_bu.setEnabled(False)
        self._s4l_settings_bu.clicked.connect(self._clicked_settings_bu)

        # Widget to show info about how much bytes have been received
        # TODO This should be an info widget
        self.bytesreadlcd = QtWidgets.QLCDNumber(w)
        self.bytesreadlcd.setDigitCount(15)
        self.bytesreadlcd.display(200)
        # Widget to show the average transfer rate
        self.bytesspeedlabel = QtWidgets.QLabel('Bit/s')
        self.bytesspeed      = QtWidgets.QLabel('NaN')                
        
        # File source
        self.button_open_file      = QtWidgets.QPushButton('Open file')
        #self.button_open_file.clicked.connect(self.open_file)
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
        
        self.combo_source.currentIndexChanged.connect(self.get_source)
        # Do the layout of the source
        self.test_ports() # Looking for serial ports        
        self.get_source()
        w.show()

    def get_source(self):
        """
        Changes the source of the logger
        """
        # The source data layout (serial, files)
        widgets_serial = [ self.combo_source,self.serial_test_bu,self.combo_serial,
                           self.combo_baud  ,self.serial_open_bu,self.bytesreadlcd, self.bytesspeedlabel,self.bytesspeed]
        widgets_file   = [ self.combo_source,self.button_open_file, self.label_nbytes,
                           self.spin_file_read_nbytes, self.label_file_read_dt, self.spin_file_read_dt]
        widgets_ip     = [ self.combo_source,self.text_ip, self.button_open_socket, self.bytesspeedlabel,self.bytesspeed ]        

        logger.debug('get_source()')
        data_source = str( self.combo_source.currentText() )

        if(data_source == 'serial'):
            whide = widgets_file + widgets_ip
            for w in whide:
                try:
                    self.layout_source.removeWidget(w)
                    w.hide()
                except Exception as e:
                    print(str(e))
                    pass

            for w in widgets_serial:
                try:
                    self.layout_source.addWidget(w)
                    w.show()
                except Exception as e:
                    print(str(e))                    
                    pass
                
        elif(data_source == 'file'):
            whide = widgets_serial + widgets_ip            
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

    def clicked_open_bu(self):
        """
        """
        t = self.serial_open_bu.text()
        print('Click ' + str(t))
        if True:
            if(t == 'Query'):
                ser = str(self.combo_serial.currentText())
                b = int(self.combo_baud.currentText())
                print('Opening port' + ser + ' with baudrate ' + str(b))
                self.sam4log.add_serial_device(ser,baud=b)
                if(self.sam4log.status == 0): # Succesfull opened
                    if(self.sam4log.query_sam4logger() == True):
                        self.deviceinfo.update(self.sam4log.device_info)
                        # Enable a settings button or if version 0.45 add a frequency combo
                        vers = float(self.sam4log.device_info['firmware'])
                        # The high speed 0.45 version 
                        if(vers == 0.45):
                            logger.debug('Opening Version 0.45 device setup')
                            self._s4l_settings_bu.close()
                            self._s4l_freq_combo = QtWidgets.QComboBox(self)
                            #self._s4l_freq_combo.setEnabled(True)                            
                            self._speeds_hz     = pymqds_sam4log.s4lv0_45_speeds_hz
                            for i,speed in enumerate(self._speeds_hz):
                                self._s4l_freq_combo.addItem(str(speed))

                            self.layout.addWidget(self._s4l_freq_combo,1,3)
                            self._ad_table.clear()                                                        
                            self._ad_table_setup_1ch()
                            self._s4l_freq_combo.currentIndexChanged.connect(self._freq_set_v045)
                            # TODO Have to resize the widget to have nicer data
                        # The general purpose 
                        elif(vers >= 0.46):
                            logger.debug('Opening Version 0.46 device setup')
                            self._s4l_settings_bu.close()
                            self._s4l_freq_combo = QtWidgets.QComboBox(self)
                            #self._s4l_freq_combo.setEnabled(True)                            
                            self._speeds_hz     = pymqds_sam4log.s4lv0_46_speeds_hz
                            for i,speed in enumerate(self._speeds_hz):
                                self._s4l_freq_combo.addItem(str(speed))

                            self.layout.addWidget(self._s4l_freq_combo,1,3)
                            self._ad_table.clear()                                                        
                            self._ad_table_setup()
                            self._s4l_freq_combo.currentIndexChanged.connect(self._freq_set)
                            # TODO Have to resize the widget to have nicer data                            
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
                self._s4l_freq_combo.setEnabled(False)                                            
                #print('Opening port' + ser + ' with baudrate ' + str(b))
                #self.sam4log.add_serial_device(ser,baud=b)
                self.sam4log.add_raw_data_stream()
                time.sleep(0.2)
                self.sam4log.query_sam4logger()
                #self.sam4log.init_sam4logger(adcs = [0,2,4])
                time.sleep(0.2)                
                self.sam4log.start_converting_raw_data()
                self.combo_serial.setEnabled(False)
                self.combo_baud.setEnabled(False)                
                self.status = 1
            else:
                self.sam4log.stop_serial_data()
                self.sam4log.stop_converting_raw_data()
                self.serial_open_bu.setText('Query')
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
            self.sam4log.add_socket(addr,port)
            if(self.sam4log.status == 0): # Succesfull opened            
                time.sleep(0.5)
                if(True):                    
                    print('Query socket/device')
                    if(self.sam4log.query_sam4logger() == True):
                        self.deviceinfo.update(self.sam4log.device_info)
                        self.button_open_socket.setEnabled(False)
                        self.text_ip.setEnabled(False)
                    else:
                        print('No device found!')
                        return

                if(True):
                    #self.sam4log.
                    self.sam4log.send_serial_data('stop\n')
                    time.sleep(0.1)                                                
                    self.sam4log.send_serial_data('stop\n')
                    time.sleep(0.2)                            
                    self.sam4log.send_serial_data('freq 200\n')
                    #self.sam4log.send_serial_data('freq 333\n')
                    time.sleep(0.2)                            
                    if(self.sam4log.query_sam4logger() == True):
                        self.deviceinfo.update(self.sam4log.device_info)
                        self.print_serial_data = False
                        time.sleep(0.1)            
                        self.sam4log.send_serial_data('start\n')


                if(True):            
                    time.sleep(.5)
                    self.sam4log.add_raw_data_stream()
                    time.sleep(0.2)
                    self.sam4log.start_converting_raw_data()

    def _clicked_settings_bu(self):
        """
        """
        logger.debug('Settings')
        
        print('Firmware' + self.sam4log.device_info['firmware'])
        self._settings_widget = sam4logConfig(self.sam4log)    
        self._settings_widget.show()                    
        


#
#
# The main window
#
#
class sam4logMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        
        mainMenu = self.menuBar()
        self.setWindowTitle("sam4log")
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

        # Main tasks for the main layout
        self.tasks = []
        self.tasks.append({'name':'Devices','widget':QtWidgets.QPushButton('Devices')})
        self.tasks[-1]['widget'].clicked.connect(self.setup_devices)
        
        self.tasks.append({'name':'Info','widget':QtWidgets.QPushButton('Info')})
        self.tasks.append({'name':'Show','widget':QtWidgets.QPushButton('Show data')})
        self.tasks.append({'name':'Plot','widget':QtWidgets.QPushButton('Plot data')})

        self.all_widgets = []
        self.devices = []

        #print(self.tasks.keys())
        #print('fsdfds')
        #print('fsdfds')
        #print('fsdfds')
        #print('fsdfds')        

        # Widget to collect all information
        self.disp_widget = QtWidgets.QWidget()
        self.disp_widget_layout = QtWidgets.QGridLayout(self.disp_widget)

        self.all_widgets.append(self.disp_widget)

        self.deviceinfo = sam4logInfo()
        # A flag if only one channel is used
        self.ONECHFLAG = False



        # Command stuff
        self.send_le = QtWidgets.QLineEdit(self)
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
        self._ad_table.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        #self._ad_table.setMinimumSize(300, 300)
        #self._ad_table.setMaximumSize(300, 300)
        self._ad_table_setup()

        #
        # Add a table for the IMU
        # PH: This is a hack TODO, make this clean
        #
        self._IMU_table = QtWidgets.QTableWidget()
        self._IMU_table.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self._IMU_table_setup()
        
        #
        # Add a table for the Pyro
        # PH: This is a hack TODO, make this clean
        #
        self._O2_table = QtWidgets.QTableWidget()
        self._O2_table.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        self._O2_table_setup()        
        


        # The main layout
        # Add all tasks
        for i,task in enumerate(self.tasks):
            self.layout.addWidget(task['widget'],i,3)
            
        if(False):
            self.layout.addLayout(self.layout_source,0,0,1,3)
            self.layout.addWidget(self._s4l_settings_bu,1,3)
            self.layout.addWidget(self.deviceinfo,1,0,1,3)
            #layout.addWidget(self._ad_choose_bu,3,1)        
            self.layout.addWidget(self._infosaveloadplot_widget,6,0,1,5)
            self.layout.addWidget(self._ad_table,4,0,2,3)
            self.layout.addWidget(self._IMU_table,4,3,2,2)
            self.layout.addWidget(self._O2_table,4,5,2,2)
        else:
            self.disp_widget_layout.addWidget(self.deviceinfo,1,0,1,3)
            #layout.addWidget(self._ad_choose_bu,3,1)        
            self.disp_widget_layout.addWidget(self._infosaveloadplot_widget,6,0,1,5)
            self.disp_widget_layout.addWidget(self._ad_table,4,0,2,3)
            self.disp_widget_layout.addWidget(self._IMU_table,4,3,2,2)
            self.disp_widget_layout.addWidget(self._O2_table,4,5,2,2)
            self.disp_widget.show()
            
        
        self.setCentralWidget(self.mainwidget)
        
        self.show()

        # Start real init
        self.status = 0 # The status
        # 0 initialised without a logger open
        # 1 logger at a serial port open
        self.sam4log = pymqds_sam4log.sam4logDataStream(logging_level='DEBUG')
        self.sam4log.deques_raw_serial.append(collections.deque(maxlen=5000))
        self.rawdata_deque = self.sam4log.deques_raw_serial[-1]


        # If the configuration changed call the _update function
        self.sam4log.init_notification_functions.append(self._update_status_information)


        self.lcdtimer = QtCore.QTimer(self)
        self.lcdtimer.setInterval(100)
        self.lcdtimer.timeout.connect(self.poll_serial_bytes)
        self.lcdtimer.start()

        # For showing the raw data
        self.dequetimer = QtCore.QTimer(self)
        self.dequetimer.setInterval(100)
        self.dequetimer.timeout.connect(self.poll_deque)
        self.dequetimer.start()

        # Updating the Voltage table
        self.intraqueuetimer = QtCore.QTimer(self)
        self.intraqueuetimer.setInterval(50)
        self.intraqueuetimer.timeout.connect(self._poll_intraqueue)
        self.intraqueuetimer.start()

    def setup_devices(self):
        """
        Bais adding and removing functions for the device setup
        """
        self.device_setup_widget        = QtWidgets.QWidget()
        w = self.device_setup_widget
        self.all_widgets.append(w)        
        self.device_setup_widget_layout = QtWidgets.QGridLayout(self.device_setup_widget)
        cl = QtWidgets.QPushButton('Close')
        cl.clicked.connect(self.device_setup_widget.close)

        dev_add = QtWidgets.QPushButton('Add')
        dev_add.clicked.connect(self.add_devices)

        self.combo_dev_add     = QtWidgets.QComboBox(w)

        for d in config['devices']:
            devname = list(d)[0]
            self.combo_dev_add.addItem(devname)
        

        self.device_setup_widget_layout.addWidget(self.combo_dev_add,0,0)
        self.device_setup_widget_layout.addWidget(dev_add,0,1)
        self.device_setup_widget_layout.addWidget(cl,1,0)
        self.device_setup_widget.show()

        
    def add_devices(self):
        """
        Adds a device using a device object with the appropriate functions
        """
        dev = str( self.combo_dev_add.currentText() )
        print('Hallo add: ' + dev)
        for d in config['devices']: # Search for the config entry
            devname = list(d)[0]
            if(devname == dev):
                print('Found device ... with object name ' + str(d[devname]['object']))
                
                obj = str(d[devname]['object'])
                #tmp = getattr(globals(),'sam4logDevice')
                deviceobj = globals()[obj]() # Call the object of the device
                deviceobj.setup()
                self.devices.append(deviceobj)
                
        #type
        #SubClass = type('SubClass', (BaseClass,), {'set_x': set_x})
        



    def _ad_table_setup(self):
        self._ad_table.setColumnCount(5)
        self._ad_table.setRowCount(10)
        self._ad_table.verticalHeader().setVisible(False)
        self._ad_table.setItem(0,
                               0, QtWidgets.QTableWidgetItem( ' Packet number' ))
        self._ad_table.setItem(1,
                               0, QtWidgets.QTableWidgetItem( ' Counter' ))
        for i in range(0,8):
            adname='LTC2442 ' + str(i)
            self._ad_table.setItem(i+2,
                                0, QtWidgets.QTableWidgetItem( adname ))        

        self._ad_table.setHorizontalHeaderLabels(['Name','Ch 0','Ch 1','Ch 2','Ch 3'])
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
        self._ad_table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
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



    def _update_status_information(self):
        """
        """
        logger.debug('Update_status_information')
        self.deviceinfo.update(self.sam4log.device_info)


    def close_application(self):
        logger.debug('Goodbye!')

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


    def open_file(self):
        """
        Opens a datafile
        """
        logger.debug('Open file')
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Select file','', "CSV (*.csv);; All files (*)");
        print(fname)
        if(len(fname[0]) > 0):
            if(isinstance(fname, str)):
                fname = [fname]
            filename = ntpath.basename(fname[0])
            path = ntpath.dirname(fname[0])
            logger.debug('Open file:' + str(fname[0]))
            ret = self.sam4log.load_file(fname[0],num_bytes = self.spin_file_read_nbytes.value(),dt=self.spin_file_read_dt.value())
            if(ret):
                self.deviceinfo.update(self.sam4log.device_info)
                self.sam4log.add_raw_data_stream()
                self.sam4log.start_converting_raw_data()
            




    def clicked_send_bu(self):
        data = self.send_le.text()
        print('Sending ' + str(data))
        self.sam4log.send_serial_data(str(data) + '\n')
        time.sleep(0.2)
        # Update the command history
        self.show_comdata.clear()
        for com in self.sam4log.commands:
            self.show_comdata.appendPlainText(str(com))

    def _freq_set_v045(self):
        logger.debug('_freq_set_v045')
        speed_str = self._s4l_freq_combo.currentText()
        #self.sam4log.stop_converting_raw_data()
        self.print_serial_data = True                
        self.sam4log.send_serial_data('stop\n')
        self.sam4log.send_serial_data('stop\n')
        self.sam4log.send_serial_data('freq ' + str(speed_str) + '\n')
        self.sam4log.send_serial_data('format 4\n')
        time.sleep(0.1)        
        if(self.sam4log.query_sam4logger() == True):
            self.deviceinfo.update(self.sam4log.device_info)
            self.print_serial_data = False
            time.sleep(0.1)            
            self.sam4log.send_serial_data('start\n')
            #self.sam4log.start_converting_raw_data()                    
        else:
            logger.warning('Bad, frequency changed did not work out. ')

    def _freq_set(self):
        logger.debug('_freq_set')
        speed_str = self._s4l_freq_combo.currentText()
        #self.sam4log.stop_converting_raw_data()
        self.print_serial_data = True                
        self.sam4log.send_serial_data('stop\n')
        self.sam4log.send_serial_data('stop\n')
        self.sam4log.send_serial_data('freq ' + str(speed_str) + '\n')
        time.sleep(0.1)        
        if(self.sam4log.query_sam4logger() == True):
            self.deviceinfo.update(self.sam4log.device_info)
            self.print_serial_data = False
            time.sleep(0.1)            
            self.sam4log.send_serial_data('start\n')
            #self.sam4log.start_converting_raw_data()                    
        else:
            logger.warning('Bad, frequency changed did not work out. ')                        


    def poll_serial_bytes(self):
        #self.bytesreadlcd.display(self.sam4log.bytes_read)
        #self.bytesspeed.setText(str(self.sam4log.bytes_read_avg))
        pass        


    def poll_deque(self):
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
        """

        Polling the intraque , and updates and displays the data in self._ad_table

        """
        global counter_test
        counter_test += 1
        data = []
        showL = True
        showA = True
        showO = True
        show_channels = [True,True,True,True] # Show each channel once during the
        # Get all data        
        while(len(self.sam4log.intraqueue) > 0):
            data = self.sam4log.intraqueue.pop()


        if(True):
            if(len(data)>0):
                # LTC channel data
                if((data['type']=='L') and showL):
                    # Get channel                    
                    ch = data['ch']
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
                        self._ad_table.setItem(0, ch + 1, item)
                        # Counter
                        item = QtWidgets.QTableWidgetItem(str(ct))
                        self._ad_table.setItem(1, ch + 1, item)
                        # Update all LTC data of that channel
                        for n,i in enumerate(self.sam4log.flag_adcs):
                            item = QtWidgets.QTableWidgetItem(str(V[n]))
                            self._ad_table.setItem(i+2, ch+1, item )

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
                        + self.filename_log  + ' ( ' + str(self.sam4log.logfile_bytes_wrote)
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
        for stream in self.sam4log.Streams:
            print(stream.get_family())
            if(stream.get_family() == "sam4log adc"):
                addresses.append(self.sam4log.get_stream_address(stream))
                
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
        for stream in self.sam4log.Streams:
            print(stream.get_family())
            if(stream.get_family() == "sam4log adc"):
                addresses.append(self.sam4log.get_stream_address(stream))
                dstream = {}
                dstream['address'] = addresses[-1]
                dstream['ind_x'] = 1
                dstream['ind_y'] = 2
                dstream['nth_point'] = 1
                dstreams.append(dstream)

            if(stream.get_family() == "sam4log IMU"):
                addresses.append(self.sam4log.get_stream_address(stream))
                for i in range(3):
                    dstream = {}                
                    dstream['address'] = addresses[-1]
                    dstream['ind_x'] = 1
                    dstream['ind_y'] = 3 + iIMU
                    iIMU += 1
                    dstream['nth_point'] = 1
                    dstreams_IMU.append(dstream)
                    
            if(stream.get_family() == "sam4log O2"):
                addresses.append(self.sam4log.get_stream_address(stream))
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
            fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Select file','', "CSV (*.csv);; All files (*)");
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
                self.sam4log.log_serial_data(filename_full)
                self._info_record_bu.setText(self._recording_status[1])
        if(t == self._recording_status[1]):
            print('Stop record')            
            ret = self.sam4log.stop_log_serial_data()
            self._info_record_bu.setText(self._recording_status[0])
            self._info_record_info.setText('Status: Stopped logging to file  '
                        + self.filename_log  + ' ( ' + str(self.sam4log.logfile_bytes_wrote)
                                           + ' bytes written)')            
            
        # The more complex slogger object, disable for the moment
        if False:
            if(t == self._recording_status[0]):
                print('Record')            
                fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Select file','', "UBJSON (*.ubjson);; All files (*)");
                if(len(fname[0]) > 0):
                    self._info_record_info.setText('Status: logfile: ' + fname[0])
                    self.loggerDS = pymqdatastream.slogger.LoggerDataStream(logging_level = logging.DEBUG, filename = fname[0], name = 'sam4log logger')
                    logstream = self.loggerDS.log_stream(self.sam4log.raw_stream)
                    logstream = self.loggerDS.log_stream(self.sam4log.conv_stream)
                    print('Start write thread')
                    self.loggerDS.start_write_data_thread()
                    self._info_record_bu.setText(self._recording_status[1])
            if(t == self._recording_status[1]):
                print('Stop record')            
                ret = self.loggerDS.stop_poll_data_thread()
                self._info_record_bu.setText(self._recording_status[0])
            


                
# If run from the command line
def main():
    print(sys.version_info)
    app = QtWidgets.QApplication(sys.argv)
    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()
    window = sam4logMainWindow()
    # Resize the window
    #window.resize(width-100,2*height/3)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
