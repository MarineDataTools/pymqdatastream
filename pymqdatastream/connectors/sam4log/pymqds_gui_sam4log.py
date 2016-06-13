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
import serial
import glob
import collections
import time
import multiprocessing
#import subprocess
import pymqdatastream
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service
import pymqdatastream.connectors.pyqtgraph.pymqds_plotxy as pymqds_plotxy
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
            #print("Opening serial port", port)
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


baud = [300,600,1200,2400,4800,9600,19200,38400,57600,115200,576000,921600]



def _start_pymqds_plotxy():
    """
    
    Start a pymqds_plotxy session
    
    """

    print('AFDFS')
    app = QtWidgets.QApplication([])
    plotxywindow = pymqds_plotxy.pyqtgraphMainWindow()
    plotxywindow.show()
    sys.exit(app.exec_())    
    print('FSFDS')    


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

        # Serial interface stuff
        self.combo_serial = QtWidgets.QComboBox(self)
        self.combo_baud   = QtWidgets.QComboBox(self)
        for b in baud:
            self.combo_baud.addItem(str(b))

        self.combo_baud.setCurrentIndex(len(baud)-1)
        self.serial_open_bu = QtWidgets.QPushButton('open')
        self.serial_open_bu.clicked.connect(self.clicked_open_bu)

        self.bytesreadlcd = QtWidgets.QLCDNumber(self)
        self.bytesreadlcd.setDigitCount(15)
        self.bytesreadlcd.display(200)

        # Command stuff
        self.send_le = QtWidgets.QLineEdit(self)
        send_bu = QtWidgets.QPushButton('send')
        send_bu.clicked.connect(self.clicked_send_bu)

        # Show the raw data of the logger
        self.show_textdata = QtWidgets.QPlainTextEdit()
        self.show_textdata.setReadOnly(True)
        self.check_show_textdata = QtWidgets.QCheckBox('Show data')
        self.check_show_textdata.setChecked(True)
        self.show_textdata.appendPlainText("Here comes the logger rawdata ...\n ")
        # Textdataformat of the show_textdata widget 0 str, 1 hex
        self.__textdataformat = 0 
        self.combo_format = QtWidgets.QComboBox()
        self.combo_format.addItem('utf-8')
        self.combo_format.addItem('hex')        
        self.combo_format.activated.connect(self.__combo_format)
        self.show_comdata = QtWidgets.QPlainTextEdit()
        self.show_comdata.setReadOnly(True)


        #
        # An information, saving, loading and plotting widget
        #
        self._infosaveloadplot_widget = QtWidgets.QWidget()
        info_layout = QtWidgets.QGridLayout(self._infosaveloadplot_widget)
        self.__recording_status = ['Record','Stop recording']        
        self.__info_record_bu = QtWidgets.QPushButton(self.__recording_status[0])
        self.__info_record_info = QtWidgets.QLabel('Status: Not recording')
        self.__info_plot_bu = QtWidgets.QPushButton('Plot')
        self.__info_plot_bu.clicked.connect(self.__plot_clicked)
        self.__info_record_bu.clicked.connect(self.__record_clicked)

        info_layout.addWidget(self.__info_record_bu,0,0)
        info_layout.addWidget(self.__info_record_info,1,0,1,2)
        info_layout.addWidget(self.__info_plot_bu,0,1)


        #
        # Add eight lcd numbers for the adc data
        #
        
        self._ad_widget = QtWidgets.QWidget()
        ad_layoutV = QtWidgets.QVBoxLayout(self._ad_widget)


        self.__ad_apply_bu = QtWidgets.QPushButton('Apply')
        self.__ad_reset_bu = QtWidgets.QPushButton('Reset')
        self.__ad_apply_bu.clicked.connect(self.__ad_check)
        self.__ad_reset_bu.clicked.connect(self.__ad_update_check_state)
        ad_widget_tmp = QtWidgets.QWidget()
        ad_layoutH = QtWidgets.QHBoxLayout(ad_widget_tmp)
        ad_layoutH.addWidget(self.__ad_apply_bu)
        ad_layoutH.addWidget(self.__ad_reset_bu)        

        ad_layoutV.addWidget(ad_widget_tmp)        

        
        self._ad_lcds = []
        self._ad_check = []        
        for i in range(8):
            ad_lcd = QtWidgets.QLCDNumber(self)
            ad_lcd.setDigitCount(8)
            ad_check = QtWidgets.QCheckBox('AD ' + str(i))
            self._ad_lcds.append(ad_lcd)
            self._ad_check.append(ad_check)
            ad_widget_tmp = QtWidgets.QWidget()
            ad_layoutH = QtWidgets.QHBoxLayout(ad_widget_tmp)
            ad_layoutH.addWidget(ad_check)            
            ad_layoutH.addWidget(ad_lcd)
            ad_layoutV.addWidget(ad_widget_tmp)





        # The main layout
        layout.addWidget(self.combo_serial,0,0)
        layout.addWidget(self.combo_baud,0,1)
        layout.addWidget(self.combo_format,1,1)
        layout.addWidget(self.check_show_textdata,1,0)
        layout.addWidget(self.serial_open_bu,0,2)
        layout.addWidget(self.bytesreadlcd,0,3)
        layout.addWidget(self.send_le,1,2)
        layout.addWidget(send_bu,1,3)
        layout.addWidget(self.show_textdata,2,0,2,2)
        layout.addWidget(self.show_comdata,2,2,2,2)

        layout.addWidget(self._infosaveloadplot_widget,0,4)
        layout.addWidget(self._ad_widget,2,4,2,1)        


        self.setCentralWidget(self.mainwidget)
        
        self.show()

        # Start real init
        print('Hallo')
        self.sam4log = pymqds_sam4log.sam4logDataStream(logging_level='DEBUG')
        self.raw_stream = self.sam4log.add_raw_data_stream()
        self.sam4log.deques_raw_serial.append(collections.deque(maxlen=5000))
        self.rawdata_deque = self.sam4log.deques_raw_serial[-1]
        self.test_ports() # Looking for serial ports


        self.lcdtimer = QtCore.QTimer(self)
        self.lcdtimer.setInterval(100)
        self.lcdtimer.timeout.connect(self.poll_serial_bytes)
        self.lcdtimer.start()


        self.dequetimer = QtCore.QTimer(self)
        self.dequetimer.setInterval(100)
        self.dequetimer.timeout.connect(self.poll_deque)
        self.dequetimer.start()


        self.intraqueuetimer = QtCore.QTimer(self)
        self.intraqueuetimer.setInterval(100)
        self.intraqueuetimer.timeout.connect(self.__poll_intraqueue)
        self.intraqueuetimer.start()                        


    def close_application(self):
        print('Goodbye!')
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


    def clicked_open_bu(self):
        """
        """
        t = self.serial_open_bu.text()
        print('Click ' + str(t))
        if True:
            if(t == 'open'):
                ser = str(self.combo_serial.currentText())
                b = int(self.combo_baud.currentText())
                self.serial_open_bu.setText('close')
                print('Opening port' + ser + ' with baudrate ' + str(b))
                self.sam4log.add_serial_device(ser,baud=b)
                self.sam4log.add_raw_data_stream()
                time.sleep(0.2)
                self.sam4log.init_sam4logger(flag_adcs = [0,2,4])
                self.__ad_update_check_state()
                time.sleep(0.2)                
                self.sam4log.start_converting_raw_data()
            else:
                self.sam4log.stop_serial_data()
                self.serial_open_bu.setText('open')

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
                if(self.__textdataformat == 0):
                    try:
                        # This works for python3
                        data_str = data.decode('utf-8')
                    except UnicodeDecodeError:
                        # This works for python3                        
                        data_str = data.hex()
                elif(self.__textdataformat == 1):
                    # This works for python3
                    data_str = data.hex()


                self.show_textdata.appendPlainText(str(data_str))
            

    def __ad_check(self):
        """

        Function called to change the adcs transmitted from the logger 

        """

        flag_adcs = []
        for i,ad in enumerate(self._ad_check):
            if(ad.isChecked()):
                flag_adcs.append(i)

        self.sam4log.init_sam4logger(flag_adcs,data_format=2)
        print(flag_adcs)

    def __ad_update_check_state(self):
        """

        Check the flag state in the sam4log class and updates the check

        """

        flag_adcs = self.sam4log.flag_adcs
        for i in flag_adcs:
            self._ad_check[i].setChecked(True)

    def __poll_intraqueue(self):
        """

        Polling the intraque to fill the ad lcd numbers with data

        """
        data = []
        while(len(self.sam4log.intraqueue) > 0):
            data = self.sam4log.intraqueue.pop()
            #print('Hallo!',data)

        #show the last dataset
        if(len(data)>0):
            for i,n in enumerate(self.sam4log.flag_adcs):
                self._ad_lcds[n].display(data[-1][i+2])


    def __combo_format(self):
        """
        """
        f = self.combo_format.currentText()
        print(f)            
        if(f == 'utf-8'):
            self.__textdataformat = 0
        if(f == 'hex'):
            self.__textdataformat = 1

        print(self.__textdataformat)


    def __plot_clicked(self):
        """
        
        Starts a plotting process ( at the moment pymqds_plotxy )

        """

        print('Plotting')
        # http://stackoverflow.com/questions/29556291/multiprocessing-with-qt-works-in-windows-but-not-linux
        # this does not work with python 2.7 
        multiprocessing.set_start_method('spawn')
        self.__plotxyprocess = multiprocessing.Process(target =_start_pymqds_plotxy)
        self.__plotxyprocess.start()

        
    def __record_clicked(self):
        """
        
        Starts a recording process ( )

        """
        

        t = self.__info_record_bu.text()
        print('Click ' + str(t))
        if(t == self.__recording_status[0]):
            print('Record')            
            fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Select file','', "UBJSON (*.ubjson);; All files (*)");
            if(len(fname[0]) > 0):
                self.__info_record_info.setText('Status: logfile: ' + fname[0])
                self.loggerDS = pymqdatastream.slogger.LoggerDataStream(logging_level = logging.DEBUG, filename = fname[0], name = 'sam4log logger')
                logstream = self.loggerDS.log_stream(self.raw_stream)
                print('Start write thread')
                self.loggerDS.start_write_data_thread()
                self.__info_record_bu.setText(self.__recording_status[1])
        if(t == self.__recording_status[1]):
            print('Stop record')            
            ret = self.loggerDS.stop_poll_data_thread()
            self.__info_record_bu.setText(self.__recording_status[0])
            


                



    

# If run from the command line
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = sam4logMainWindow()
    window.show()
    sys.exit(app.exec_())    
