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
import socket
import datetime
import collections
import time
import argparse
import glob
import pymqdatastream.connectors.nmea.pymqds_nmea0183logger as pymqds_nmea0183logger

try:
    import pymqdatastream.connectors.qt.qt_service as datastream_qt_service
    FLAG_PYMQDATASTREAM=True
except:
    FLAG_PYMQDATASTREAM=False    
    print('Did not found pymqdatastream')

# TODO
# Implement this here
# http://stackoverflow.com/questions/24469662/how-to-redirect-logger-outpu-tinto-pyqt-text-widget
#
#

# A stylesheet for the device widgets

device_style = """ nmea0183Widget { border: 2px solid black; border-radius: 2px; background-color: rgb(255, 255, 255); } """


# Import qt
try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    print('Using pyqt5')
except:
    try:
        from PyQt4.QtGui import * 
        from PyQt4.QtCore import *
        print('Using pyqt4')
    except:
        raise Exception('Could not import qt, exting')



logging.basicConfig(stream=sys.stderr)
logger = logging.getLogger('pymqds_nmea0183_gui')
logger.setLevel(logging.DEBUG)

#pynmeatools.nmea0183logger.logger.setLevel(logging.DEBUG)

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



class positionWidget(QWidget):
    """
    A widget for NMEA position datasets (GGA, GGL)
    """
    def __init__(self,port='XXX'):
        funcname = self.__class__.__name__ + '.___init__()'
        #self.__version__ = pymqdatastream.__version__
        QWidget.__init__(self)
        self.port = port
        Font = QFont('SansSerif', 15)
        self.titles = {}
        self.titles['lat']  = QLabel('Latitude')
        self.titles['lon']  = QLabel('Longitude')
        self.titles['time'] = QLabel('Time (UTC)')
        self.titles['sat'] = QLabel('# Sat.')
        self.titles['dil'] = QLabel('Accur.')                

        self.labels = {}
        self.labels['lat']  = QLabel('XX')
        self.labels['lon']  = QLabel('XX')
        self.labels['time'] = QLabel('XX')
        self.labels['sat']  = QLabel('XX')
        self.labels['dil']  = QLabel('XX')                
        for lab in self.titles.items():
            lab[1].setFont(Font)

        for lab in self.labels.items():
            lab[1].setFont(Font)            

        mainlayout = QVBoxLayout(self)

        layout = QGridLayout(self)
        layout.addWidget(self.titles['time'],0,0)
        layout.addWidget(self.labels['time'],1,0)                        
        layout.addWidget(self.titles['lat'],0,1)
        layout.addWidget(self.labels['lat'],1,1)
        layout.addWidget(self.titles['lon'],0,2)
        layout.addWidget(self.labels['lon'],1,2)
        layout.addWidget(self.titles['sat'],2,0)
        layout.addWidget(self.titles['dil'],2,1)                                
        layout.addWidget(self.labels['sat'],3,0)
        layout.addWidget(self.labels['dil'],3,1)

        lab = QLabel(self.port)
        lab.setFont(Font)            
        mainlayout.addWidget(lab)
        mainlayout.addLayout(layout)


    def new_data(self,new_data):
        """
        The function to feed the widget with new data
        """
        try:
            data = pymqds_nmea0183logger.parse(new_data['nmea'])
        except Exception as e:
            print(str(e))
            return

        # This is interpretation of data and could (should?!) be done
        # also in the nmea0183logger object
        #print('DATA',data)            
        if('GGA' in data.identifier()):
            if(not(data.timestamp == None)):
                tstr = data.timestamp.strftime('%H:%M:%S')
                self.labels['time'].setText(tstr)
            if(len(data.lat) > 0):
                #latstr = str(data.latitude)
                latstr = '{:03.6f} '.format(data.latitude)
                latstr += data.lat_dir
                self.labels['lat'].setText(latstr)
            if(len(data.lon) > 0):
                #lonstr = str(data.longitude)                
                lonstr = '{:03.6f} '.format(data.longitude)
                lonstr += data.lon_dir
                self.labels['lon'].setText(lonstr)
            if(len(data.num_sats) > 0):
                self.labels['sat'].setText(data.num_sats)
            if(len(data.horizontal_dil) > 0):
                self.labels['dil'].setText(data.horizontal_dil)                
            


#
#
# NMEA device
#
# Connect NMEA sentences and widgets which can plot them
plotwidgets = []
plotwidgets.append(['GGA',positionWidget,'Position'])        

#class nmea0183Widget(QWidget):
class nmea0183Widget(QFrame):
    """
    A widget for a single NMEA device in a nmea0183logger
    """
    # Signal, have to explain briefly what it does
    update_ident_widgets = pyqtSignal()    
    def __init__(self, ind_device=0, parent_gui = None, dequelen = 100000):
        # Do the rest
        #QWidget.__init__(self)
        super(nmea0183Widget, self).__init__()
        funcname = self.__class__.__name__ + '.___init__()'
        #self.__version__ = pynmeatools.__version__
        # Do the rest
        self.dequelen = dequelen
        QWidget.__init__(self)
        self.parent_gui = parent_gui
        self.nmea0183logger = parent_gui.nmea0183logger
        self.serial = self.nmea0183logger.serial[ind_device]
        self.data_deque = collections.deque(maxlen=self.dequelen) # Get the data from nmealogger
        self.identifiers = []
        self.num_identifiers = []        
        self.serial['data_queues'].append(self.data_deque)
        self._info_str = str(self.serial['device_name'])
        self._qlabel_info     = QLabel(self._info_str)
        self._qlabel_bin      = QLabel('')
        self._qlabel_sentence = QLabel('')
        self._qlabels_identifiers = []
        self._update_info()

        # A list of widgets to plot the NMEA data
        self.plot_widgets = []        
        
        self._flag_show_raw_data = False
        self._button_raw_data = QPushButton('Raw data')
        self._button_raw_data.clicked.connect(self._show_raw_data)
        self._button_close = QPushButton('Close')
        self._button_close.serial = self.serial # Add serial to the
                                                # close button, this
                                                # allows other widgets
                                                # to identify the
                                                # device to be closed
        self._button_close.clicked.connect(self.close_device)
        self.layout = QGridLayout(self)
        self.layout_idents = QVBoxLayout(self)
        self.layout_plot_idents = QVBoxLayout(self)
        self.layout.addWidget(self._button_close,0,0)        
        self.layout.addWidget(self._qlabel_info,1,0)
        self.layout.addWidget(self._qlabel_bin,2,0)
        self.layout.addWidget(self._qlabel_sentence,3,0)
        self.layout.addLayout(self.layout_idents,4,0)
        self.layout.addLayout(self.layout_plot_idents,5,0)
        self.layout_plot_idents.addWidget(self._button_raw_data)
        
        
    def _new_data(self):
        """Function called as a signal when new data arrives, this is a dummy
        function which emits a signal (update_ident_widgets.) and is
        otherwise doing not much

        """
        funcname = self.__class__.__name__ + '._new_data()'
        # We do it with signals to make it thread-safe
        # Check if we have a new identifier in the received data
        self.update_ident_widgets.emit()
        #print('Hallo new data!')

    def _update_info(self):
        #print('Update')        
        if( self.nmea0183logger != None ):
            self._bin_str = 'Bytes read \t' + str(self.serial['bytes_read'])
            self._sentence_str = 'NMEA sets read \t' + str(self.serial['sentences_read'])
            self._qlabel_bin.setText(self._bin_str)
            self._qlabel_sentence.setText(self._sentence_str)

            for ind,lab in enumerate(self._qlabels_identifiers):
                txt = self.identifiers[ind][:-1] + ' \t' + str(self.num_identifiers[ind])
                lab.setText(txt)
                

    def _update_identifier_widgets(self):
        """
        """
        while(len(self.data_deque) > 0):
            raw_data = self.data_deque.pop()
            #print('Got: ' + str(raw_data))
            data = pymqds_nmea0183logger.parse(raw_data['nmea'])
            # Show raw data
            if(self._flag_show_raw_data):
                self._plaintext_data.insertPlainText(str(raw_data['nmea']))

            # Send data to widgets
            # TODO: This could be done thread safe using queues
            
            for w in self.plot_widgets:
                w.new_data(raw_data)

            # Check for new identifiers
            if(data != None):
                ident = data.identifier()
                #print('Ident:' + ident)
                try:
                    ind = self.identifiers.index(ident)
                    self.num_identifiers[ind] += 1
                except:
                    #print('Adding identifier:' + str(ident))
                    self.identifiers.append(ident)
                    self.num_identifiers.append(0)
                    lab = QLabel(ident[:-1] + ' 1')
                    self._qlabels_identifiers.append(lab)
                    self.layout_idents.addWidget(lab)   
                    # Test if we have a widget for plotting this dataset
                    for ide in plotwidgets:
                        if(isinstance(ide[0], str)):
                            ind = ident.find(ide[0])
                            if(ind >= 0):
                                print('Found a widget for ' + str(ident) + ':' + str(ide[1]))
                                but = QPushButton(ide[2])
                                but.clicked.connect(self._open_widgets)
                                self.layout_plot_idents.addWidget(but)
                                
                self._update_info()
                #print(self.identifiers)
                #print(self.num_identifiers)
                
                
    def _open_widgets(self):
        """
        Opens widgets for plotting data
        """
        sender = self.sender()
        sender_txt =str(sender.text())
        #print('Hallo: ' + str(sender.text()))
        # Check which widget we have
        for ide in plotwidgets:
            print(ide)
            if(sender_txt == ide[2]):
                w = ide[1]
                self.plot_widgets.append(w(port=self.serial['device_name']))
                self.plot_widgets[-1].show()

                
    def _show_raw_data(self):
        """
        Plots the raw data in a plaintextwidget
        """
        self._flag_show_raw_data = True
        self._plaintext_data = QPlainTextEdit()
        self._plaintext_data.setAttribute(Qt.WA_DeleteOnClose)
        self._plaintext_data.destroyed.connect(self._raw_data_close)
        self._plaintext_data.show()


    def _raw_data_close(self):
        print('Destroyed!')
        self._flag_show_raw_data = False


    def closeEvent(self, event):
        print("Closing all plot widgets")
        try:
            self._plaintext_data.close()
        except:
            pass
        for w in self.plot_widgets:
            w.close()


    def close_device(self):
        """
        Closes the device
        """
        self.nmea0183logger.rem_serial_device(number = self.serial['number'])
        self.serial = None
        self.parent_gui._rem_device(device = self)
        
        
        


class serialWidget(QWidget):
    """
    A widget for serial connections of 
    """
    def __init__(self,parent_gui):
        funcname = self.__class__.__name__ + '.___init__()'
        #self.__version__    = pynmeatools.__version__
        self.parent_gui     = parent_gui
        self.nmea0183logger = parent_gui.nmea0183logger
        self.emit_signals   = []
        self.ports_open     = []
        # Do the rest
        QWidget.__init__(self)
        
        layout = QGridLayout(self)
        # Serial baud rates
        baud = [300,600,1200,2400,4800,9600,19200,38400,57600,115200,576000,921600]
        self._combo_serial_devices = QComboBox(self)
        self._combo_serial_devices.currentIndexChanged.connect(self._serial_device_changed)
        self._combo_serial_baud = QComboBox(self)
        for b in baud:
            self._combo_serial_baud.addItem(str(b))

        self._combo_serial_baud.setCurrentIndex(4)
        self._button_serial_openclose = QPushButton('Open')
        self._button_serial_openclose.clicked.connect(self._openclose)
        self._test_serial_ports()
        
        layout.addWidget(self._combo_serial_devices,0,0)
        layout.addWidget(self._combo_serial_baud,0,1)
        layout.addWidget(self._button_serial_openclose,0,2)
        
        
    def _test_serial_ports(self):
        """
        
        Look for serial ports

        """
        funcname = self.__class__.__name__ + '._test_serial_ports()'
        ports = serial_ports()
        # This could be used to pretest devices
        #ports_good = self.test_device_at_serial_ports(ports)
        ports_good = ports
        logger.debug(funcname + ': ports:' + str(ports_good))
        self._combo_serial_devices.clear()
        for port in ports_good:
            self._combo_serial_devices.addItem(str(port))
            
        
    def _openclose(self):
        """

        Opening or closing a serial device

        """
        funcname = self.__class__.__name__ + '._openclose()'
        print(funcname)
        logger.debug(funcname)
        port = str(self._combo_serial_devices.currentText())
        ind = self._combo_serial_devices.currentIndex()
        b = int(self._combo_serial_baud.currentText())
        if(self.sender().text() == 'Open'):
            logger.debug(funcname + ": Opening Serial port" + port)
            ret = self.nmea0183logger.add_serial_device(port)
            if(ret):
                self.parent_gui._add_device(self.nmea0183logger.serial[-1])
                # This is somewhat spaghetti, but lets leave it for
                # the moment, connect the close button of the dV
                # widget in the parent gui with the remove device
                # widget here
                self.parent_gui.device_widgets[-1]._button_close.clicked.connect(self.close_device)
                self.ports_open.append(port)                
                self._serial_device_changed()
                
                    
        else:
            logger.debug(funcname + ": We should never have come here!")


        # Call all the functions in self.emit_signals
        for s in self.emit_signals:
            s()


    def close_device(self):
        """Function that is connected to a button with a serial device
        attached to it that a sender = self.sender() and sender.serial
        is the device to be closed

        """
        funcname = "close_device"
        sender = self.sender()
        serial = sender.serial
        port = serial['port']
        logger.debug(funcname + ": Closing Serial port" + port)
        self.ports_open.remove(port)
        self._serial_device_changed()
        # This does not work anymore, because the serial has been
        # already removed by the nmeaWidget from the nmea0183logger
        ## Device
        #for ind,s in enumerate(self.nmea0183logger.serial):
        #    if(s['port'] == port):
        #        logger.debug(funcname + ": Found serial device for port:" + port + ' at index:' + str(ind))

                    

    def _serial_device_changed(self):
        funcname = "_serial_device_changed()"
        logger.debug(funcname)
        port = str(self._combo_serial_devices.currentText())
        ind = self._combo_serial_devices.currentIndex()
        for p in self.ports_open:
            if(p == port):
                #self._button_serial_openclose.setText('Close')
                self._button_serial_openclose.setEnabled(False)
                return

        self._button_serial_openclose.setEnabled(True)



class tcpWidget(QWidget):
    """A widget for a TCP connection of a GPS device

    """
    def __init__(self,parent_gui):
        funcname = self.__class__.__name__ + '.___init__()'
        #self.__version__    = pynmeatools.__version__
        self.parent_gui     = parent_gui
        self.nmea0183logger = parent_gui.nmea0183logger
        self.emit_signals   = []
        self.ports_open     = []
        # Do the rest
        QWidget.__init__(self)
        
        layout = QGridLayout(self)

        # IP source
        self.text_ip = QLineEdit()
        # Hack, this should be removed later
        self.text_ip.setText('192.168.178.34:9001')
        self._button_sockets_choices = ['Connect to IP','Disconnect from IP']
        self.button_open_socket = QPushButton('Open')
        self.button_open_socket.clicked.connect(self.clicked_open_socket)
        
        layout.addWidget(self.text_ip,0,0)
        layout.addWidget(self.button_open_socket,0,1)
        
        
    def clicked_open_socket(self):
        """
        Opens a TCP socket to get data
        """
        funcname = "clicked_open_socket()"
        logger.debug(funcname)        
        addrraw = str(self.text_ip.text())
        print(addrraw)
        try:
            addr = addrraw.split(':')[0]
            port = int(addrraw.split(':')[1])
        except:
            print('Enter proper address')
            return

        print(addr,port)
        logger.debug(funcname + 'Address:port: ' + str(addr) + ':' + str(port))                
        # Opening the socket
        ret = self.nmea0183logger.add_tcp_stream(addr,port)
        if(ret):
            self.parent_gui._add_device(self.nmea0183logger.serial[-1])
                    
        else:
            logger.debug(funcname + ": We should never have come here!")        
            
        
        # Call all the functions in self.emit_signals
        for s in self.emit_signals:
            s()



            

class QtPlainTextLoggingHandler(logging.Handler):
    """
    A handler to display logging text into a qt text widget
    """
    def __init__(self,qtplaintextedit):
        logging.Handler.__init__(self)
        self.qtplaintextedit = qtplaintextedit

    def emit(self, record):
        record = self.format(record)
        #XStream.stdout().write("{}\n".format(record))
        self.qtplaintextedit.insertPlainText("{}\n".format(record))


#
#
#
#
#
#

class nmea0183SetupWidget(QWidget):
    """
    A widget for the setup of a NMEA0183 device;
    either serial, tcp or datastream
    """
    def __init__(self):
        funcname = self.__class__.__name__ + '.___init__()'
        #self.__version__ = pynmeatools.__version__
        # Add a logger object
        self.nmea0183logger = pymqds_nmea0183logger.nmea0183logger(loglevel=logging.DEBUG)
        # Do the rest
        QWidget.__init__(self)
        # Create the menu
        self.device_widgets = []
        mainwidget = self
        mainlayout = QGridLayout(mainwidget)
        self._serial_widget = serialWidget(self)
        self._widget_tcp = tcpWidget(self)
        self._close = QPushButton('Close')
        self._close.clicked.connect(self.close)
        
        # Logging widget
        self._button_log = QPushButton('Show log')
        self._button_log.clicked.connect(self._log_widget)
        self._combo_loglevel = QComboBox()
        self._combo_loglevel.addItem('Debug')
        self._combo_loglevel.addItem('Info')
        self._combo_loglevel.addItem('Warning')

        # Datastream widgets
        # Do only if pymqdatastream exists
        if(FLAG_PYMQDATASTREAM):
            self._widget_pymqds = QWidget(self)
            self._button_pymqds = QPushButton('Open')
            self.nmea0183logger.create_pymqdatastream()
            self._layout_pymqds = QHBoxLayout(self._widget_pymqds)                
            self._layout_pymqds.addWidget(self._button_pymqds)
            self._layout_pymqds.addStretch(1)
            #self.DatastreamChoose.handle_update_clicked()
            self._button_pymqds.clicked.connect(self._clicked_datastream_subscribe)

        # A table to add all the NMEA devices
        self._widget_devices = QWidget(self)
        self._layout_devices = QHBoxLayout(self._widget_devices)
        self._layout_devices.addStretch(1)
        
        # Layout
        mainlayout.addWidget(self._close,3,0)
        mainlayout.addWidget(QLabel('Serial device'),0,0)        
        mainlayout.addWidget(self._serial_widget,0,1)
        mainlayout.addWidget(self._button_log,0,2)
        mainlayout.addWidget(self._combo_loglevel,0,3)
        mainlayout.addWidget(QLabel('TCP'),1,0)
        mainlayout.addWidget(self._widget_tcp,1,1)        
        mainlayout.addWidget(QLabel('Datastream'),2,0)
        mainlayout.addWidget(self._widget_pymqds,2,1)

        mainlayout.addWidget(self._widget_devices,3,0,2,3)

    def _add_device(self,device):
        """
        
        Adds a new nmea0183Widget
        
        """
        #self._combo_serial_devices.removeItem(ind)
        # Create a new device widget
        ind_serial = len(self.nmea0183logger.serial) - 1
        dV = nmea0183Widget(ind_device = ind_serial, parent_gui = self)
        dV.setStyleSheet(device_style)
        # The signal seems to have to be connected here, otherwise it
        # does not work ...
        dV.update_ident_widgets.connect(dV._update_identifier_widgets)
        self.nmea0183logger.serial[-1]['data_signals'].append(dV._new_data)
        dV.setMaximumWidth(300)
        ind = len(self.device_widgets)
        self.device_widgets.append(dV)
        self._layout_devices.insertWidget(ind,dV)


    def _rem_device(self,port=None,device=None):
        """
        
        Closes and removes a nmea0183Widget
        
        """
        funcname = '_rem_device()'
        logger.debug(funcname)
        if(port != None):
            for dev in self.device_widgets:
                if(dev.serial['port'] == port):
                    logger.debug(funcname + 'Found device to remove')
                    dev.close()
                    self.device_widgets.remove(dev)

        elif(device != None):
            device.close()
            self.device_widgets.remove(device)
                
        
    def _log_widget(self):
        """
        A widget of log data
        """

        self._log_text = QPlainTextEdit()
        self._log_widget = self._log_text        
        handler = QtPlainTextLoggingHandler(self._log_text)
        lformat='%(asctime)-15s:%(levelname)-8s:%(name)-20s:%(message)s'

        # Adding the gui logger
        handler.setFormatter(logging.Formatter(lformat))
        logger.addHandler(handler)
        # Adding the nmea0183 logger
        self.nmea0183logger.logger.addHandler(handler)

        self._log_text.show()
        #print('hallo!')
        logger.info('hallo')


    def _something_changed(self):
        """
        """
        funcname = self.__class__.__name__ + '._something_changed()'        
        logger.debug(funcname)

        
    def _clicked_datastream_subscribe(self):
        self._datastreamsubscribe = datastream_qt_service.DataStreamSubscribeWidget(self.nmea0183logger.pymqdatastream, hide_myself=True, stream_type = 'pubstream')
        self._datastreamsubscribe.signal_newstream.append(self.nmea0183logger.add_pymqdsStream)
        self._datastreamsubscribe.signal_newstream.append(self._new_pymqdsStream)
        self._datastreamsubscribe.signal_remstream.append(self._rem_pymqdsStream)        
        self._datastreamsubscribe.show()


    def _new_pymqdsStream(self,stream):
        """
        Creating a device widget for a new pymqdsStream
        """
        funcname = '_new_pymqdsStream()'        
        logger.debug(funcname)
        # The last serial is a datastream as before this function
        # self.nmea0183logger.add_pymqdsStream has been called        
        ind_serial = len(self.nmea0183logger.serial) - 1
        dV = nmea0183Widget(ind_device = ind_serial,parent_gui = self)
        dV.setStyleSheet(device_style)
        # The signal seems to be connected here, otherwise it does not work ...
        dV.update_ident_widgets.connect(dV._update_identifier_widgets)
        self._add_device(dV)
        self.nmea0183logger.serial[-1]['data_signals'].append(dV._new_data)

    def _rem_pymqdsStream(self,stream):
        """
        Removes the infrastructure for a pymqds Stream
        """
        funcname = '_rem_pymqdsStream()'        
        logger.debug(funcname)
        for dV in self.device_widgets:
            if(stream == dV.serial['device']):
                logger.debug(funcname + ': Found a matching stream to remove')
                self._rem_device(device=dV)
                return
            

    def _quit(self):
        funcname = '_quit()'        
        logger.debug(funcname)
        
        try:
            self._about_label.close()
        except:
            pass

        try:
            self._log_widget.close()
        except:
            pass

        try:
            self._datastreamsubscribe.close()
        except:
            pass        

        # Closing all device widgets
        for w in self.device_widgets:
            w.close()
        
        self.close()

        
    def _about(self):
        about_str = '\n pymqds_nmea0183_gui \n'        
        #about_str += '\n This is pynmeatools_gui: ' + str(self.__version__)
        about_str += '\n Written by Peter Holtermann \n'
        about_str += '\n peter.holtermann@io-warnemuende.de \n'
        about_str += '\n under the GPL v3 license \n'                
        self._about_label = QLabel(about_str)
        self._about_label.show()        

    
#
#
# The main gui
#
#
class guiMain(QMainWindow):
    """

    The main gui widget

    """
    def __init__(self):
        funcname = self.__class__.__name__ + '.___init__()'
        #self.__version__ = pymqdatastream.__version__
        # Add a logger object
        self.nmea0183logger = pymqds_nmea0183logger.nmea0183logger(loglevel=logging.DEBUG)
        # Do the rest
        QWidget.__init__(self)
        # Create the menu
        self.file_menu = QMenu('&File',self)
        self.device_widgets = []
        #self.file_menu.addAction('&Settings',self.fileSettings,Qt.CTRL + Qt.Key_S)
        self.file_menu.addAction('&Quit',self._quit,Qt.CTRL + Qt.Key_Q)
        self.about_menu = QMenu('&About',self)
        self.about_menu.addAction('&About',self._about)
        self.menuBar().addMenu(self.file_menu)
        self.menuBar().addMenu(self.about_menu)
        
        mainwidget = nmea0183SetupWidget()

        # Focus 
        mainwidget.setFocus()
        self.setCentralWidget(mainwidget)


    def _quit(self):
        funcname = '_quit()'        
        logger.debug(funcname)
        self.close()

        
    def _about(self):
        about_str = '\n pymqds_nmea0183_gui \n'        
        about_str += '\n This is pynmeatools_gui: ' + str(self.__version__)
        about_str += '\n Written by Peter Holtermann \n'
        about_str += '\n peter.holtermann@io-warnemuende.de \n'
        about_str += '\n under the GPL v3 license \n'                
        self._about_label = QLabel(about_str)
        self._about_label.show()        


def main():
    app = QApplication(sys.argv)
    myapp = guiMain()
    myapp.show()
    sys.exit(app.exec_())    

if __name__ == "__main__":
    main()

