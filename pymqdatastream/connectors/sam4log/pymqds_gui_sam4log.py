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
import pymqdatastream
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service
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

        self.show_textdata = QtWidgets.QPlainTextEdit()
        self.show_textdata.setReadOnly(True)

        self.show_textdata.appendPlainText("HALLO!!")


        self.show_comdata = QtWidgets.QPlainTextEdit()
        self.show_comdata.setReadOnly(True)     

        # timer to read the data of the stream
        self.show_timer = QtCore.QTimer(self)
        self.show_timer.timeout.connect(self.show_data)
        #self.timer.start(25)
        #self.show_textdata.clear()

        layout.addWidget(self.combo_serial,0,0)
        layout.addWidget(self.combo_baud,0,1)
        layout.addWidget(self.serial_open_bu,0,2)
        layout.addWidget(self.bytesreadlcd,0,3)
        layout.addWidget(self.send_le,1,2)
        layout.addWidget(send_bu,1,3)
        layout.addWidget(self.show_textdata,2,0,2,2)
        layout.addWidget(self.show_comdata,2,2,2,2)
        
        self.setCentralWidget(self.mainwidget)
        
        self.show()

        # Start real init
        print('Hallo')
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


    def open_close_serial(self):
        """
        """

        
        ser = str(self.combo_serial.currentText())
        b = int(self.combo_baud.currentText())
        print(ser,b)
        if(self.sam4log == None):
            print('Opening port' + ser + ' with baudrate ' + str(b))
            self.sam4log.add_serial_device(ser,baud=b)
            return True
        else:
            print('Closing port ')
            self.sam4log.stop_serial_data()
            return True
            #

        #

        return False

    def clicked_open_bu(self):
        """
        """
        t = self.serial_open_bu.text()
        print('Click ' + str(t))
        #ret = self.open_close_serial()
        if True:
            if(t == 'open'):
                ser = str(self.combo_serial.currentText())
                b = int(self.combo_baud.currentText())
                self.serial_open_bu.setText('close')
                print('Opening port' + ser + ' with baudrate ' + str(b))
                self.sam4log.add_serial_device(ser,baud=b)
                self.sam4log.add_raw_data_stream()
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
            self.show_textdata.appendPlainText(str(data))
            

    def show_data(self):
        # Load data and plot
        while(len(self.stream.deque) > 0):
            data = self.stream.deque.pop()
            # Convert the data to a str
            data_str = self.data2str(data)
            self.show_textdata.appendPlainText(data_str)
            #print(self.data2str_raw(data))


        self.stream_data.verticalScrollBar().setValue(
            self.stream_data.verticalScrollBar().maximum())                


# If run from the command line
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = sam4logMainWindow()
    window.show()
    sys.exit(app.exec_())    
