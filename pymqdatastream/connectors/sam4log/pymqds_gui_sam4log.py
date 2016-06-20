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
        # Textdataformat of the show_textdata widget 0 str, 1 hex
        self.__textdataformat = 0 
        self.combo_format = QtWidgets.QComboBox()
        self.combo_format.addItem('utf-8')
        self.combo_format.addItem('hex')        
        self.combo_format.activated.connect(self.__combo_format)
        self.show_comdata = QtWidgets.QPlainTextEdit()
        self.show_comdata.setReadOnly(True)

        self._show_data_layout.addWidget(self.combo_format,0,0)
        self._show_data_layout.addWidget(self.show_textdata,1,0)
        self._show_data_layout.addWidget(self.show_comdata,1,1)


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
        info_layout.addWidget(self.__info_record_info,1,0)
        info_layout.addWidget(self.__info_plot_bu,2,0)


        #
        # Add eight lcd numbers for the adc data
        #

        self.__ad_choose_bu = QtWidgets.QPushButton('Choose LTCs')
        self.__ad_choose_bu.clicked.connect(self._open_ad_widget)

        self._ad_widget = None
        
        #
        # Add a qtable for realtime data showing of voltage/packets number/counter
        #http://stackoverflow.com/questions/20797383/qt-fit-width-of-tableview-to-width-of-content
        #
        self._ad_table = QtWidgets.QTableWidget()
        #self._ad_table.setMinimumSize(300, 300)
        #self._ad_table.setMaximumSize(300, 300)        
        self._ad_table.setColumnCount(2)
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

        self._ad_table.setHorizontalHeaderLabels(['Name','Data','subscribed'])
        # Make width and height of the table such that all entries can be seen
        vwidth = self._ad_table.verticalHeader().width()
        hwidth = self._ad_table.horizontalHeader().length()
        fwidth = self._ad_table.frameWidth() * 2
        swidth = self._ad_table.style().pixelMetric(QtGui.QStyle.PM_ScrollBarExtent)
        self._ad_table.setFixedWidth(vwidth + hwidth + fwidth)
        self._ad_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        height = 0
        hheight = self._ad_table.horizontalHeader().height()
        for i in range(self._ad_table.rowCount()):
            height += self._ad_table.rowHeight(i)
            
        print(height,hheight)
        self._ad_table.setFixedHeight(height + hheight + fwidth)
        

        # The main layout
        layout.addWidget(self.combo_serial,0,0)
        layout.addWidget(self.combo_baud,0,1)
        layout.addWidget(self._show_data_bu,4,4)
        layout.addWidget(self.serial_open_bu,0,2)
        layout.addWidget(self.bytesreadlcd,0,3)

        layout.addWidget(self._infosaveloadplot_widget,3,3)
        layout.addWidget(self.__ad_choose_bu,1,4,1,1)
        layout.addWidget(self._ad_table,2,0,2,4)
        layout.addWidget(QtWidgets.QLabel('Command'),4,0) # Command
        layout.addWidget(self.send_le,4,1,1,2) # Command
        layout.addWidget(send_bu,4,3) # Command



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


        self.lcdtimer = QtCore.QTimer(self)
        self.lcdtimer.setInterval(100)
        self.lcdtimer.timeout.connect(self.poll_serial_bytes)
        self.lcdtimer.start()


        self.dequetimer = QtCore.QTimer(self)
        self.dequetimer.setInterval(100)
        self.dequetimer.timeout.connect(self.poll_deque)
        self.dequetimer.start()


        self.intraqueuetimer = QtCore.QTimer(self)
        self.intraqueuetimer.setInterval(200)
        self.intraqueuetimer.timeout.connect(self.__poll_intraqueue)
        self.intraqueuetimer.start()                        


    def close_application(self):
        print('Goodbye!')
        # Closing potentially open widgets
        try:
            self._show_data_widget_opened.close()
        except:
            pass

        try:
            self._ad_widget.close()
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
                time.sleep(0.2)                
                self.sam4log.start_converting_raw_data()
                self.status = 1
            else:
                self.sam4log.stop_serial_data()
                self.sam4log.stop_converting_raw_data()
                self.serial_open_bu.setText('open')
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

                
    def _clicked_show_data_bu(self):
        """
        """
        
        t = self._show_data_bu.text()
        print('Click ' + str(t))
        if True:
            if(t == 'Show data'):
                self._show_data_widget_opened = self._show_data_widget
                self._show_data_widget_opened.show()
                self._show_data_bu.setText('Hide data')
            if(t == 'Hide data'):
                self._show_data_widget_opened.close()
                self._show_data_bu.setText('Show data')                

                
    def _open_ad_widget(self):
        """

        Opens the ad checkbox widget

        """

        self._ad_widget = QtWidgets.QWidget()
        ad_layoutV = QtWidgets.QVBoxLayout(self._ad_widget)
        self._ad_widget.destroyed.connect(self._close_ad_widget)
        self._ad_widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
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
            

        self.__ad_update_check_state()
        self._ad_widget.show()

        
    def _close_ad_widget(self):
        """


        """
        print('Close')
        self._ad_widget = None

        
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
        # Get all data
        while(len(self.sam4log.intraqueue) > 0):
            data = self.sam4log.intraqueue.pop()

        #show the last dataset in the table
        if(len(data)>0):
            # Packet number
            item = QtWidgets.QTableWidgetItem(str(data[-1][0]))
            self._ad_table.setItem(0, 1, item)
            # Counter
            item = QtWidgets.QTableWidgetItem(str(data[-1][1]))
            self._ad_table.setItem(1, 1, item)
            for i,n in enumerate(self.sam4log.flag_adcs):
                item = QtWidgets.QTableWidgetItem(str(data[-1][i+2]))
                self._ad_table.setItem(n+2, 1, item )  


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
        multiprocessing.set_start_method('spawn',force=True)        
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
                logstream = self.loggerDS.log_stream(self.sam4log.raw_stream)
                logstream = self.loggerDS.log_stream(self.sam4log.conv_stream)
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
