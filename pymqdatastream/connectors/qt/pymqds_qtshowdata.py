#!/usr/bin/env python


try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except:
    from qtpy import QtCore, QtGui, QtWidgets
    
    
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
    def __init__(self,logging_level=logging.INFO):
        QtWidgets.QWidget.__init__(self)        
        self.setMinimumSize(QtCore.QSize(500, 500))
        self.Datastream = pymqdatastream.DataStream(name='qtshowstreamdata',logging_level=logging_level)
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
    def __init__(self,logging_level=logging.INFO):
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

        self.qtshowstreamdatawidget = qtshowstreamdataWidget(logging_level=logging_level)
        self.setCentralWidget(self.qtshowstreamdatawidget)
        
        self.show()

    def choose_streams(self):
        self.qtshowstreamdatawidget.DatastreamChoose.show()

    def close_application(self):
        self.qtshowstreamdatawidget.DatastreamChoose.close()
        sys.exit()                        



def main():
    # Remove string and then quit gives segfault!
    # Verbosity of datastream objects
    datastream_help = 'Query datastream with address e.g. -d tcp://192.168.178.97:18055'    
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--datastream', '-d', nargs = '?', default = False, help=datastream_help)    
    args = parser.parse_args()
    logging_level = logging.INFO
    if(args.verbose == None):
        logging_level = logging.CRITICAL        
        logger.setLevel(logging.CRITICAL)
        pymqdatastream.logger.setLevel(logging.CRITICAL)
    elif(args.verbose == 1):
        logging_level = logging.INFO
        logger.setLevel(logging.INFO)
        pymqdatastream.logger.setLevel(logging.INFO)
    elif(args.verbose >= 2):
        print('Debug logging level')
        logging_level = logging.DEBUG
        logger.setLevel(logging.DEBUG)
        pymqdatastream.logger.setLevel(logging.DEBUG)

    print('Args datastream:',args.datastream)
    if(args.datastream != False):    
        if(args.datastream == None):
            logger.debug('Connecting to  pymqdatastream Datastream logger')
        else:
            logger.debug('Connecting to pymqdatastream at address: ' + str(args.datastream))
    
    app = QtWidgets.QApplication(sys.argv)
    window = qtshowstreamdataMainWindow(logging_level = logging_level)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
