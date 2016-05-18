#!/usr/bin/env python
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import json
import logging
import argparse
import pymqdatastream
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service
import pymqds_logger

# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger('pymqds_gui_logger')
logger.setLevel(logging.DEBUG)



class qtloggerWidget(QtWidgets.QWidget):
    def __init__(self,logging_level = 'INFO'):
        logger.debug('__init__()')
        QtWidgets.QWidget.__init__(self)
        self.setMinimumSize(QtCore.QSize(500, 500))
        #self.Datastream = pymqdatastream.DataStream(name='logger')
        list_status = []
        # Datastream stuff
        #self.DatastreamChoose = datastream_qt_service.DataStreamSubscribeWidget(self.Datastream, hide_myself=True, stream_type = 'pubstream')
        
        #self.DatastreamChoose.handle_update_clicked()

        self.logging_level = logging_level
        # Control buttons 
        self.button_file = QtWidgets.QPushButton('Create logfile', self)
        self.button_file.clicked.connect(self.add_file)

        self.button_stream = QtWidgets.QPushButton('Add stream', self)
        self.button_stream.clicked.connect(self.add_stream)
        self.button_stream.setEnabled(False)

        self.button_log = QtWidgets.QPushButton('Start logging', self)
        self.button_log.clicked.connect(self.logging)
        self.button_log.setEnabled(False)        

        # A Qtree to show all files and the streams which are logged
        # to the files
        self.tree_files = QtWidgets.QTreeWidget()
        self.tree_files.setHeaderHidden(True)
        self.tree_files.itemClicked.connect(self.handle_item_clicked)
        self.LoggerDataStream_clicked = None # Datastream object to work with        

        # The layout
        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.tree_files,0,0,1,3)
        self.layout.addWidget(self.button_file,1,0)
        self.layout.addWidget(self.button_stream,1,1)
        self.layout.addWidget(self.button_log,1,2)        
        self.setLayout(self.layout)

        #
        self.log_datastreams = []
        self.log_fnum = 0

        
        #self.DatastreamChoose.signal_newstream.append(self.add_showwidget)
        #self.DatastreamChoose.signal_remstream.append(self.rem_showwidget)

        
    def handle_item_clicked(self, item, column):
        """
        
        """
        logger.debug('handle_item_clicked()')
        self.button_log.setEnabled(False)        
        try:
            # 
            self.LoggerDataStream_clicked = item.LoggerDataStream
            self.button_stream.setEnabled(True)
            # Start stop logging button
            self.update_buttons()

        except Exception as e:
            self.LoggerDataStream_clicked = None
            self.button_stream.setEnabled(False)

            
    def update_buttons(self):
        """
        """
        print('update')
        if(self.LoggerDataStream_clicked != None):
            if(len(self.LoggerDataStream_clicked.log_streams) > 0):
                if(self.LoggerDataStream_clicked.logging == False):
                    self.button_log.setText('Start logging')
                    self.button_log.setEnabled(True)
                else:
                    self.button_log.setText('Stop logging')
                    self.button_log.setEnabled(True)        

        
    def update_tree_files(self):
        """
        
        """
        return

    def add_file(self):
        """
        
        Adds a LoggerDataStream object to log to the file

        """
        self.log_fnum += 1
        fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Select file')
        str_tree = str(self.log_fnum)  + ' ' + str(fname[0].rsplit('/')[-1]) # This rsplit will prob. not work in windows ?!

        # Create a logger datastream object
        logger.debug('Creating LoggerDatastrem with file:' + str(fname[0]))
        logDS = pymqds_logger.LoggerDataStream(filename=fname[0], name = 'logger gui: ' + str_tree, logging_level = self.logging_level)
        self.log_datastreams.append(logDS)
        file_item = self.addParent(self.tree_files.invisibleRootItem(), 0, str_tree, fname)
        file_item.LoggerDataStream = logDS

    def add_stream(self):
        """ Adds a stream to the choosen datastream log object, stream is
        choosen by a DataStreamSubscribeWidget

        """
        logger.debug('add_stream()')        
        if(self.LoggerDataStream_clicked != None):
            logger.debug('add_stream(): DataStreamSubscribeWidget')        
            self.DatastreamChoose = datastream_qt_service.DataStreamSubscribeWidget(self.LoggerDataStream_clicked, hide_myself=True, stream_type = 'pubstream',multiple_subscription=False)
            # Add to the signal_newstream caller the logging call of the LoggerDatastream object
            # When this function is called the logging starts!
            self.DatastreamChoose.signal_newstream.append(self.LoggerDataStream_clicked.log_stream)
            # We want to have the stream object as well to add it to the child tree items
            self.DatastreamChoose.signal_newstream.append(self.get_stream)            
            self.DatastreamChoose.show()

            
        else:
            logger.warning('add_stream(): no Datastream choosen!')
            
            
            
        return

    def logging(self):
        """ Start stop logging button

        """
        logger.debug('logging()')                
        if(self.sender().text() == 'Start logging'):
            logger.debug('logging(): Start logging')                
            self.LoggerDataStream_clicked.start_logging()
        elif(self.sender().text() == 'Stop logging'):
            logger.debug('logging(): Stop logging')                            
            self.LoggerDataStream_clicked.stop_logging()


        self.update_buttons()


    def get_stream(self,stream):
        """
        Dummy function to get stream object from signal handler
        """

        # Add child object
        # TODO: remove if not logged anymore
        root = self.tree_files.invisibleRootItem()
        file_count = root.childCount()
        for i in range(file_count):
            file_item = root.child(i)
            if(file_item.LoggerDataStream == self.LoggerDataStream_clicked):
                name = str(stream.log_stream_number) + ' ' + stream.name
                stream_item = self.addChild(file_item, 0, name, 'JA')


    def addParent(self, parent, column, title, data):
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        item.setData(column, QtCore.Qt.UserRole, data)
        item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
        item.setExpanded(False)
        return item

    def addChild(self, parent, column, title, data):
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        item.setData(column, QtCore.Qt.UserRole, data)
        #item.setCheckState (column, QtCore.Qt.Unchecked)
        return item


    def close_files(self):
        """
        """
        logger.debug('close_files(): Closing files')                                    
        for log_datastream in self.log_datastreams:
            log_datastream.close_file()

        
        



class qtloggerMainWindow(QtWidgets.QMainWindow):
    def __init__(self,logging_level='INFO'):
        QtWidgets.QMainWindow.__init__(self)
        print('Hallo')
        mainMenu = self.menuBar()
        self.setWindowTitle("Log Streamdata")

        chooseStreamAction = QtWidgets.QAction("&Streams", self)
        chooseStreamAction.setShortcut("Ctrl+L")
        chooseStreamAction.setStatusTip('Create Logfile')
        chooseStreamAction.triggered.connect(self.log_file)

        quitAction = QtWidgets.QAction("&Quit", self)
        quitAction.setShortcut("Ctrl+Q")
        quitAction.setStatusTip('Closing the program')
        quitAction.triggered.connect(self.close_application)        

        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(chooseStreamAction)
        fileMenu.addAction(quitAction)        
        
        self.statusBar()

        self.qtloggerWidget = qtloggerWidget(logging_level = logging_level)
        self.setCentralWidget(self.qtloggerWidget)
        
        self.show()

    def log_file(self):
        self.qtloggerWidget.add_file()

    def close_application(self):
        self.qtloggerWidget.close_files()
        sys.exit()                        


if __name__ == "__main__":
    # Remove string and then quit gives segfault!
    # Verbosity of datastream objects
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()
    
    if(args.verbose == None):
        logger.setLevel(logging.CRITICAL)
        pymqdatastream.logger.setLevel(logging.CRITICAL)
        logging_level = logging.CRITICAL
    elif(args.verbose == 1):
        logger.setLevel(logging.INFO)
        pymqdatastream.logger.setLevel(logging.INFO)
        logging_level = logging.INFO
    elif(args.verbose == 2):
        logger.setLevel(logging.DEBUG)
        pymqdatastream.logger.setLevel(logging.DEBUG)
        logging_level = logging.DEBUG   

    logging_level = logging.DEBUG   
    logger.setLevel(logging_level)
    app = QtWidgets.QApplication(sys.argv)
    window = qtloggerMainWindow(logging_level=logging_level)
    window.show()
    sys.exit(app.exec_())
