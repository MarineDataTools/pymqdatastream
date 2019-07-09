import sys
import argparse
import numpy as np
import logging
from pymqdatastream.utils.utils_serial import serial_ports, test_serial_lock_file, serial_lock_file
import serial
import time

def get_todl_time(data):
    ind1 = data.find(b'Time')
    ind2 = data.find(b'\n>>>10kHz')
    if((ind1 > 0) and (ind2 > 0)):
        ts_todl = data[ind1:ind2].decode('utf-8')
        try:
            t_todl = datetime.datetime.strptime(ts_todl,'Time: %Y.%m.%d %H:%M:%S')
        except:
            t_todl = None
        return t_todl

    return None

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except:
    from qtpy import QtCore, QtGui, QtWidgets

#https://matplotlib.org/3.1.0/gallery/user_interfaces/embedding_in_qt_sgskip.html
from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('todl_set_time')
logger.setLevel(logging.DEBUG)

# Serial baud rates
baud = [300,600,1200,2400,4800,9600,19200,38400,57600,115200,460800,576000,921600]



class todlsettimeMainWindow(QtWidgets.QMainWindow):
    """The main interface of the TODL-Settime gui

    """
    def __init__(self,serialport):
        QtWidgets.QMainWindow.__init__(self)
        self.all_widgets = []
        mainMenu = self.menuBar()
        self.setWindowTitle("TODL Set Time")
        #self.setWindowIcon(QtGui.QIcon('logo/pymqdatastream_logo_v0.2.svg.png'))
        extractAction = QtWidgets.QAction("&Quit", self)
        extractAction.setShortcut("Ctrl+Q")
        extractAction.setStatusTip('Closing the program')
        extractAction.triggered.connect(self.close_application)

        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(extractAction)

        self.statusBar()

        self.mainwidget = todlsettimeWidget(serialport)
        self.setCentralWidget(self.mainwidget)                
        self.width_orig = self.frameGeometry().width()
        self.height_orig = self.frameGeometry().height()
        self.width_main = self.width_orig
        self.height_main = self.height_orig
    def close_application(self):
        logger.debug('Goodbye!')
        self.close()
        self.mainwidget.close()
        

class todlsettimeWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,serialport=None):
        QtWidgets.QMainWindow.__init__(self)
        layout = QtWidgets.QGridLayout()
        self.layout = layout
        self.setLayout(layout)
        # Serial interface stuff
        self.combo_serial = QtWidgets.QComboBox(self)
        ports = serial_ports()
        self.combo_serial.clear()
        for port in ports:
            self.combo_serial.addItem(str(port))
            
        self.combo_baud   = QtWidgets.QComboBox(self)
        for b in baud:
            self.combo_baud.addItem(str(b))

        self.combo_baud.setCurrentIndex(len(baud)-3)
        #self.combo_baud.setEditable(True)
        self.serial_open_bu = QtWidgets.QPushButton('Set time')
        self.serial_open_bu.clicked.connect(self.clicked_set_time)
        #self.serial_open_bu.setEnabled(False)
        layout.addWidget(self.combo_serial,0,0)
        layout.addWidget(self.combo_baud,0,1)
        layout.addWidget(self.serial_open_bu,0,2)                
        self.show()

    def clicked_set_time(self):
        self.open_todl()

    def open_todl(self):
        # Check if we have a TODL here
        PORT = self.combo_serial.currentText()
        BAUD = int(self.combo_baud.currentText())
        print('Looking for device on port: ' + PORT + ' with baudrate:' + str(BAUD))
        ser = serial.Serial(PORT,BAUD)  # open serial port
        print(ser.name)         # check which port was really used
        ser.reset_input_buffer()
        ser.write(b'stop\n')     # write a stop
        time.sleep(.5)
        ser.write(b'stop\n')     # write a stop
        time.sleep(.5)
        ser.write(b'time\n')     # write a time command
        time.sleep(0.1)
        data = ser.read(ser.in_waiting)
        t_todl = get_todl_time(data)
        if(t_todl is not None):
            print('Found a TODL')
        else:
            print('Did not find a TODL, exiting ...')
            ser.close()
            sys.exit()

    def set_time(self):
        # Setting time like this
        #set time yyyy-mm-dd HH:MM:SS
        dtoff = datetime.timedelta(0,1)
        t = datetime.datetime.utcnow()
        n = 1
        while True:
            t = datetime.datetime.utcnow()
            sec = t.second
            if(n == 0):
                break    
            if(t.microsecond > 970000): # A bit of time for programming needed roughly 0.03 seconds
                n -= 1        
                if True:
                    print('Setting time!')
                    tset = t + dtoff # strftime does not care about (rounds) 
                                     # microseconds, so we have to add the
                                     # dtoff
                    ts = tset.strftime('%Y-%m-%d %H:%M:%S') 
                    print('Setting time to:' + ts)
                    tcom = 'set time ' + ts
                    tcom = tcom.encode('utf-8') + b'\n'
                    ser.write(tcom)     # write a time command


        time.sleep(0.5)
        data = ser.read(ser.in_waiting)
        print(data)


    def compare_clocks(self):
        t = datetime.datetime.utcnow()
        second_done = t.second
        n_compare = 3
        dt_sleep = 0.01
        n_test = int(1.0/dt_sleep)
        dt_all = []
        while True:
            if(n_compare == 0):
                break

            sec = t.second
            time.sleep(.5)
            n_compare -= 1
            tall = []
            ttodl_all = []    
            for i in range(0,n_test):
                if True:
                    t = datetime.datetime.utcnow()
                    ts = t.strftime('%Y-%m-%d %H:%M:%S %Z')
                    ser.reset_input_buffer()
                    ser.write(b'time\n')     # write a time command
                    t1 = datetime.datetime.utcnow()
                    t2 = datetime.datetime.utcnow()
                #>>>Time: 2018.02.15 12:53:29\n

                time.sleep(dt_sleep)
                while( (ser.in_waiting <= 35) and ((t2 - t1) < datetime.timedelta(0,1)) ):
                    t2 = datetime.datetime.utcnow()

                t3 = datetime.datetime.utcnow()
                tall.append([t1,t3])                            
                data = ser.read(ser.in_waiting)
                t_todl = get_todl_time(data)            
                if(t_todl != None):
                    ttodl_all.append(t_todl)

                if(len(ttodl_all) > 1):
                    dttodl = ttodl_all[-1] - ttodl_all[-2]
                    if(dttodl.total_seconds() == 1):
                        #print(ttodl_all,dttodl)
                        break

        # This is not entirely correct as we should take the dt_sleep into account
        dt = t3 - t_todl
        dt_all.append(dt.total_seconds())
        tstr = 'Time TODL:' + str(t_todl) + ' time computer: ' + str(t3) + ' difference [s]: ' + str(dt.total_seconds())
        print(tstr)










        



# If run from the command line
def main():
    print(sys.version_info)
    print(sys.argv)
    app = QtWidgets.QApplication(sys.argv)
    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()
    if(len(sys.argv) > 1):
        serialport = sys.argv[1]
    else:
        serialport = None
        
    window = todlsettimeMainWindow(serialport=serialport)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main_gui()        

