#!/usr/bin/env python3
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import json
# This is a hack to import datastream for testing
import os
sys.path.insert(0, os.path.abspath('..'))
import pymqdatastream
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service

class Window(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.D = pymqdatastream.DataStream(name='qtoverview')
        list_status = []
        # Datastream stuff
        self.address_list = pymqdatastream.standard_datastream_control_addresses

        self.list_status = self.query_datastreams(self.address_list)
        self.datastream_statuswidget = datastream_qt_service.DataStreamStatusViewWidget(self.list_status)
        self.button = QtWidgets.QPushButton('Query', self)
        self.button.clicked.connect(self.handleQuery)

        #self.datastream_controlwidget = datastream_qt_service.DataStreamControlStreamWidget(self.D,remote_addresses = self.address_list)
        #self.datastream_controlwidget.update_tree()
        
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.datastream_statuswidget,0,0)
        layout.addWidget(self.button,1,0)
        self.setLayout(layout)
        
    def handleQuery(self):
        self.list_status = self.query_datastreams(self.address_list)
        self.datastream_statuswidget.populate_with_status(self.list_status)

    def query_datastreams(self,addresses):
        list_status = []
        for address in addresses:
            print(address)
            [ret,reply_dict] = self.D.get_datastream_info(address,dt_wait=0.01)
            if(ret):
                try:
                    list_status.append(reply_dict)
                    print("query_datastream(): Reply:" + str(reply_dict))
                except:
                    print("query_datastream(): Could not decode json reply:" + str(reply))

        return list_status

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
