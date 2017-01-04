
#!/usr/bin/env python3

#
#
from PyQt5 import QtCore, QtGui, QtWidgets
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
#import subprocess
import binascii

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
    
import pymqds_sam4log



def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system

        found here: http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    """
    
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            logger.debug("serial_ports(): Testing serial port " + str(port))
            ret = test_serial_lock_file(port)
            if(ret == False):
                logger.debug("serial_ports(): Opening serial port " + str(port))
                s = serial.Serial(port)
                s.close()
                result.append(port)
        #except (OSError, serial.SerialException):
        except Exception as e:
            logger.debug('serial_ports(): Exception:' + str(e))
            pass

    return result

def test_serial_lock_file(port):
    """
    Creates or removes a lock file for a serial port in linux
    """
    devicename = port.split('/')[-1]
    filename = '/var/lock/LCK..'+devicename
    print('serial_lock_file(): filename:' + str(filename))
    try:
        flock = open(filename,'r')
        flock.close()
        return True            
    except Exception as e:
        print('serial_lock_file():' + str(e))
        return False

def serial_lock_file(port,remove=False):
    """
    Creates or removes a lock file for a serial port in linux
    """
    devicename = port.split('/')[-1]
    filename = '/var/lock/LCK..'+devicename
    print('serial_lock_file(): filename:' + str(filename))
        
    if(remove == False):
        try:
            flock = open(filename,'w')
            flock.write(str(os.getpid()) + '\n')
            flock.close()
        except Exception as e:
            print('serial_lock_file():' + str(e))
    else:
        try:
            print('serial_lock_file(): removing filename:' + str(filename))
            flock = open(filename,'r')
            line = flock.readline()
            print('data',line)
            flock.close()
            os.remove(filename)
        except Exception as e:
            print('serial_lock_file():' + str(e))        

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
        self.formats =     [2              ,3    ]
        self.formats_str = ['binary (cobs)','csv']
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

            

def _start_pymqds_plotxy_old():
    """
    
    Start a pymqds_plotxy session
    
    """

    print('AFDFS')
    app = QtWidgets.QApplication([])
    plotxywindow = pymqds_plotxy.pyqtgraphMainWindow()
    plotxywindow.show()
    sys.exit(app.exec_())    
    print('FSFDS')


def _start_pymqds_plotxy(addresses):
    """
    
    Start a pymqds_plotxy session and plots the streams given in the addresses list
    Args:
        addresses: List of addresses of pymqdatastream Streams
    
    """

    logger.debug("_start_pymqs_plotxy():" + str(addresses))

    logging_level = logging.DEBUG
    datastreams = []
    
    for addr in addresses:
        datastream = pyqtgraphDataStream(name = 'plotxy_cont', logging_level=logging_level)
        stream = datastream.subscribe_stream(addr)
        datastream.init_stream_settings(stream, bufsize = 5000, plot_data = True, ind_x = 1, ind_y = 2, plot_nth_point = 6)
        datastream.plot_datastream(True)
        datastream.set_plotting_mode(mode='cont')        
        datastreams.append(datastream)

        datastream_xr = pyqtgraphDataStream(name = 'plotxy_xr', logging_level=logging_level)
        stream_xr = datastream_xr.subscribe_stream(addr)
        datastream_xr.init_stream_settings(stream_xr, bufsize = 5000, plot_data = True, ind_x = 1, ind_y = 2, plot_nth_point = 6)
        datastream_xr.plot_datastream(True)
        datastream_xr.set_plotting_mode(mode='xr',xl=5)        
        datastreams.append(datastream_xr)        


    app = QtWidgets.QApplication([])
    plotxywindow = pymqds_plotxy.pyqtgraphMainWindow(datastream=datastreams[0])
    for i,datastream in enumerate(datastreams):
        if(i > 0):
            plotxywindow.add_graph(datastream=datastream)
        
    plotxywindow.show()
    sys.exit(app.exec_())    
    logger.debug("_start_pymqs_plotxy(): done")


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
        layout = QtWidgets.QGridLayout(self.mainwidget)

        self.deviceinfo = sam4logInfo()

        # Serial interface stuff
        self.combo_serial = QtWidgets.QComboBox(self)
        self.combo_baud   = QtWidgets.QComboBox(self)
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
        self._bin_info = QtWidgets.QWidget()
        binlayout = QtWidgets.QGridLayout(self._bin_info)
        self.bytesreadlcd = QtWidgets.QLCDNumber(self)
        self.bytesreadlcd.setDigitCount(15)
        self.bytesreadlcd.display(200)

        # Command stuff
        self.send_le = QtWidgets.QLineEdit(self)
        send_bu = QtWidgets.QPushButton('send')
        send_bu.clicked.connect(self.clicked_send_bu)

        # Show the raw data of the logger
        self._show_data_widget = QtWidgets.QWidget()
        self._show_data_layout = QtWidgets.QGridLayout(self._show_data_widget)
        self.show_textdata = QtWidgets.QPlainTextEdit()
        self.show_textdata.setReadOnly(True)
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

        info_layout.addWidget(self._info_record_bu,0,2)
        info_layout.addWidget(self._info_record_info,1,2)
        info_layout.addWidget(self._info_plot_bu,0,1)
        info_layout.addWidget(self._show_data_bu,0,0)        

        #
        # Add a qtable for realtime data showing of voltage/packets number/counter
        # http://stackoverflow.com/questions/20797383/qt-fit-width-of-tableview-to-width-of-content
        #
        self._ad_table = QtWidgets.QTableWidget()
        #self._ad_table.setMinimumSize(300, 300)
        #self._ad_table.setMaximumSize(300, 300)
        self._ad_table_setup()

        

        # The main layout
        layout.addWidget(self.serial_test_bu,0,0)        
        layout.addWidget(self.combo_serial,0,1)
        layout.addWidget(self.combo_baud,0,2)
        layout.addWidget(self.serial_open_bu,0,3)
        layout.addWidget(self.bytesreadlcd,0,4)        
        layout.addWidget(self._s4l_settings_bu,1,3)
        layout.addWidget(self.deviceinfo,1,0,1,3)        
        
        #layout.addWidget(self._ad_choose_bu,3,1)        
        layout.addWidget(self._infosaveloadplot_widget,6,0,1,5)
        layout.addWidget(self._ad_table,4,0,2,5)
        

        self.setCentralWidget(self.mainwidget)
        
        self.show()

        # Start real init
        self.status = 0 # The status
        # 0 initialised without a logger open
        # 1 logger at a serial port open
        self.sam4log = pymqds_sam4log.sam4logDataStream(logging_level='DEBUG')
        self.sam4log.deques_raw_serial.append(collections.deque(maxlen=5000))
        self.rawdata_deque = self.sam4log.deques_raw_serial[-1]
        self.test_ports() # Looking for serial ports

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
        self.intraqueuetimer.setInterval(100)
        self.intraqueuetimer.timeout.connect(self._poll_intraqueue)
        self.intraqueuetimer.start()


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
        


    def _update_status_information(self):
        """
        """
        logger.debug('Update_status_information')
        self.deviceinfo.update(self.sam4log.device_info)


    def close_application(self):
        logger.debug('Goodbye!')
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
            self._settings_widget.close()
        except:
            pass

        try:
            self._plotxyprocess.stop()
        except:
            pass            
            
        self.close()

        
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


    def _clicked_settings_bu(self):
        """
        """
        print('Settings')
        self._settings_widget = sam4logConfig(self.sam4log)
        self._settings_widget.show()

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
                if(self.sam4log.query_sam4logger() == True):
                    self.deviceinfo.update(self.sam4log.device_info)
                    self._s4l_settings_bu.setEnabled(True)
                    self.serial_open_bu.setText('Open')
                    
            elif(t == 'Open'):
                #ser = str(self.combo_serial.currentText())
                #b = int(self.combo_baud.currentText())
                self.serial_open_bu.setText('Close')
                self._s4l_settings_bu.setEnabled(False)                
                #print('Opening port' + ser + ' with baudrate ' + str(b))
                #self.sam4log.add_serial_device(ser,baud=b)
                self._ad_table.clear()
                self._ad_table_setup()                
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


    def clicked_send_bu(self):
        data = self.send_le.text()
        print('Sending ' + str(data))
        self.sam4log.send_serial_data(str(data) + '\n')
        time.sleep(0.2)
        # Update the command history
        self.show_comdata.clear()
        for com in self.sam4log.commands:
            self.show_comdata.appendPlainText(str(com))


    def poll_serial_bytes(self):
        self.bytesreadlcd.display(self.sam4log.bytes_read)


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

        Polling the intraque , and displays the data in self._ad_table

        """
        data = []
        # Get all data
        while(len(self.sam4log.intraqueue) > 0):
            data = self.sam4log.intraqueue.pop()
            if(len(data)>0):
                # Get channel
                ch = data['ch']
                num = data['num']
                c50khz = data['50khz']
                V = data['V']
                # Packet number            
                item = QtWidgets.QTableWidgetItem(str(num))
                self._ad_table.setItem(0, ch + 1, item)
                # Counter
                item = QtWidgets.QTableWidgetItem(str(c50khz))
                self._ad_table.setItem(1, ch + 1, item)
                for n,i in enumerate(self.sam4log.flag_adcs):
                    item = QtWidgets.QTableWidgetItem(str(V[n]))

                    self._ad_table.setItem(i+2, ch+1, item )

        # Update the recording file status as well (addding file size)
        t = self._info_record_bu.text()
        if(t == self._recording_status[1]):
            self._info_record_info.setText('Status: Logging to file  '
                        + self.filename_log  + ' ( ' + str(self.sam4log.logfile_bytes_wrote)
                        + ' bytes wrote)')
            

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
                        + ' bytes wrote)')            
            
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
if __name__ == "__main__":
    print(sys.version_info)
    app = QtWidgets.QApplication(sys.argv)
    window = sam4logMainWindow()
    window.show()
    sys.exit(app.exec_())    
