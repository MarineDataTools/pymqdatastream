#!/usr/bin/env python3

#
#

"""Module for a Qt-Based GUI of the Turbulent Ocean Data Logger. The
heart are device objects with several mandatory function such that the
main object of this module can open/close and call information
functions

A device needs the following informations:

 __init__(self,      device_changed_function=None)

The device changed function is used to interconnect the device to each
other and to notify if possibly new information from other devices ia
available (e.g. a todl device might be interested in gps information)


- setup(name,mainwindow)     (mandatory)
- info      (obligatory)
- show_data (obligatory)
- plot_data (obligatory)
- close     (mandatory)

.. moduleauthor:: Peter Holtermann <peter.holtermann@io-warnemuende.de>

"""


try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except:
    from qtpy import QtCore, QtGui, QtWidgets


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
import binascii
import yaml
import datetime
import importlib
from pkg_resources import Requirement, resource_filename
filename_version = resource_filename(Requirement.parse('pymqdatastream'),'pymqdatastream/VERSION')


with open(filename_version) as version_file:
    version = version_file.read().strip()



logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('todl_data_tool')
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)


import pymqdatastream
import pymqdatastream.connectors.todl.pymqds_todl as pymqds_todl

class todldatatoolMainWindow(QtWidgets.QWidget):
    """
    """
    def __init__(self):
        # See here
        #https://stackoverflow.com/questions/25784865/pyqt5-filebrowser-signal-slot-connecting-qtreeview-to-qcolumnview#25836177

        filters = '*.todl,*.nc'
        QtWidgets.QMainWindow.__init__(self)
        layout = QtWidgets.QGridLayout()
        # Create a directory view
        dpath = '/home/holterma/'
        self.FolderTree = QtWidgets.QListView()
        self.FileView = QtWidgets.QListView()

        dirmodel = QtWidgets.QFileSystemModel()
        #set filter to show only folders
        dirmodel.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllDirs)
        dirmodel.setRootPath(dpath)        

        filemodel = QtWidgets.QFileSystemModel()
        filemodel.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Files)
        filemodel.setRootPath(dpath)
        filemodel.setNameFilters(filters.split(','))
        filemodel.setNameFilterDisables(0)
        
        self.filemodel = filemodel

        self.FolderTree.setModel(dirmodel)
        self.FileView.setModel(filemodel)

        
        self.FolderTree.setRootIndex(dirmodel.index(dpath))
        self.FileView.setRootIndex(filemodel.index(dpath))
        self.FolderTree.clicked['QModelIndex'].connect(self.setpathonclick)
        self.FileView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.FileView.selectionModel().selectionChanged.connect(self.fileclicked)
        self.FileView.clicked.connect(self.fileclicked)

        self.setLayout(layout)
        self.filter0 = QtWidgets.QLineEdit(filters)
        self.filter0.editingFinished.connect(self.newfilefilter)

        filterlayout = QtWidgets.QHBoxLayout()
        filterlayout.addWidget(self.filter0)
        layout.addWidget(self.FolderTree,0,0)
        layout.addWidget(self.FileView,0,1)
        layout.addLayout(filterlayout,1,1)        

    def fileclicked(self,index):
        print('clicked',index)
        for ind in self.FileView.selectionModel().selectedIndexes():
            fname = self.FileView.model().fileName(ind)
            print(fname)

    def newfilefilter(self):
        """ Changes the file filters
        """
        print(self.filter0.text())
        filters = self.filter0.text()
        self.filemodel.setNameFilters(filters.split(','))        
        
    def setpathonclick(self,index):
        currentpathindex = self.FolderTree.currentIndex()
        print(currentpathindex)
        rootpath = self.FolderTree.model().filePath(index)
        filemodel = self.FileView.model()
        filemodel.setRootPath(rootpath)
        self.FileView.setRootIndex(filemodel.index(rootpath))
        

# If run from the command line
def main():
    print(sys.version_info)
    app = QtWidgets.QApplication(sys.argv)
    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()
    window = todldatatoolMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
