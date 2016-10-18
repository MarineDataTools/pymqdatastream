#!/usr/bin/env python
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import json
import logging
import argparse
import pymqdatastream
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service


# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger('pymqdatastream_qtshowstreamdata')
logger.setLevel(logging.DEBUG)



class qtshowstreamdataWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)        
        self.setMinimumSize(QtCore.QSize(500, 500))
        self.Datastream = pymqdatastream.DataStream(name='qtshowstreamdata')
        list_status = []
        # Datastream stuff
        #self.DatastreamChoose = DataStreamChooseShowWidget(self.Datastream, hide_myself=True)
        self.DatastreamChoose = datastream_qt_service.DataStreamSubscribeWidget(self.Datastream, hide_myself=True, stream_type = 'pubstream')
        #self.DatastreamChoose.query_datastreams(self.DatastreamChoose.address_list)
        #self.DatastreamChoose.handle_update_clicked()
        self.showwidgets = []
        
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        
        self.DatastreamChoose.signal_newstream.append(self.add_showwidget)
        self.DatastreamChoose.signal_remstream.append(self.rem_showwidget)
        
    def add_showwidget(self,stream):
        """
        Adds a showwidget to the layout
        """
        #showwidget = datastream_qt_service.DataStreamShowTextDataWidget(stream)
        showwidget = datastream_qt_service.DataStreamShowTableDataWidget(stream)
        self.showwidgets.append(showwidget)
        self.layout.addWidget(showwidget)

    def rem_showwidget(self,stream):
        """
        Removes a showwidget containing the stream object from the layout
        """
        funcname = self.__class__.__name__ + '.rem_showwidget()'
        logger.debug(funcname + ':' + str(stream))
        for i,showwidget in enumerate(self.showwidgets):
            if(showwidget.stream.socket.uuid == stream.socket.uuid):
                logger.debug('Found showwidget at position:' + str(i))
                self.showwidgets.pop(i)
                self.layout.removeWidget(showwidget)
                showwidget.deleteLater()
                showwidget.setParent(None)
                return

        logger.debug('Found no showwidget to remove!')


        
                
                


class qtshowstreamdataMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        print('Hallo')
        mainMenu = self.menuBar()
        self.setWindowTitle("Showstreamdata")
        quitAction = QtWidgets.QAction("&Quit", self)
        quitAction.setShortcut("Ctrl+Q")
        quitAction.setStatusTip('Closing the program')
        quitAction.triggered.connect(self.close_application)

        chooseStreamAction = QtWidgets.QAction("&Streams", self)
        chooseStreamAction.setShortcut("Ctrl+S")
        chooseStreamAction.setStatusTip('Choose Streams')
        chooseStreamAction.triggered.connect(self.choose_streams)        

        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(quitAction)
        fileMenu.addAction(chooseStreamAction)        
        
        self.statusBar()

        self.qtshowstreamdatawidget = qtshowstreamdataWidget()
        self.setCentralWidget(self.qtshowstreamdatawidget)
        
        self.show()

    def choose_streams(self):
        self.qtshowstreamdatawidget.DatastreamChoose.show()

    def close_application(self):
        self.qtshowstreamdatawidget.DatastreamChoose.close()
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
    elif(args.verbose == 1):
        logger.setLevel(logging.INFO)
        pymqdatastream.logger.setLevel(logging.INFO)
    elif(args.verbose == 2):
        logger.setLevel(logging.DEBUG)
        pymqdatastream.logger.setLevel(logging.DEBUG)        
    
    app = QtWidgets.QApplication(sys.argv)
    window = qtshowstreamdataMainWindow()
    window.show()
    sys.exit(app.exec_())
