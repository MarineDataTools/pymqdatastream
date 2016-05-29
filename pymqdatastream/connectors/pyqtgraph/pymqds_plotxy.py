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
import pyqtgraph as pg
import pymqdatastream
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service

#import datastream.qt.pyqtgraph_service as datastream_pyqtgraph_service


# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

logger = logging.getLogger('pydatastream_plotxy')
logger.setLevel(logging.INFO)

class SetupStreamStyle(QtWidgets.QWidget):
    """
    A widget to setup the plotting style of the stream
    """
    def __init__(self,stream):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout(self)
        self.stream = stream
        self.button_ok = QtWidgets.QPushButton('Ok', self)
        self.button_ok.clicked.connect(self.handle_ok)
        self.button_cancel = QtWidgets.QPushButton('Cancel', self)
        self.button_cancel.clicked.connect(self.handle_cancel)
        print('Hallo stream:',stream)
        self.label_nplot = QtGui.QLabel('Plot every nth point')
        self.spin_nplot = QtGui.QSpinBox()
        self.spin_nplot.setRange(1, 100000)
        try:
            nplot = self.stream.pyqtgraph_nplot
        except:
            nplot = 1
            
        self.spin_nplot.setValue(nplot)
        layout.addWidget(self.label_nplot)
        layout.addWidget(self.spin_nplot)
        wi = QtWidgets.QWidget()
        layoutH = QtWidgets.QHBoxLayout(wi)
        layoutH.addWidget(self.button_ok)
        layoutH.addWidget(self.button_cancel)        
        layout.addWidget(wi)        



    def handle_ok(self):
        print('Ok')
        self.stream.pyqtgraph_nplot = self.spin_nplot.value()
        print('Ok',self.stream.pyqtgraph_nplot)
    def handle_cancel(self):
        print('Cancel')
        self.close()
        

class DataStreamChoosePlotWidget(datastream_qt_service.DataStreamSubscribeWidget):
    """

    This widget is a copy of the
    datastream_qt_service.DataStreamSubscribeWidget and is modified to
    choose some plotting parameters

    """
    def __init__(self,Datastream,hide_myself = False):
        datastream_qt_service.DataStreamSubscribeWidget.__init__(self,Datastream, hide_myself)
        self.button_subscribe.setText('Add Stream')
        self.button_subscribe.clicked.connect(self.handle_button_subscribed)
        self.button_unsubscribe.setText('Remove Stream')
        self.button_clear = QtWidgets.QPushButton('Clear', self)
        self.button_clear.clicked.connect(self.handle_button_plot_clear)
        self.button_plot = QtWidgets.QPushButton('Plot Streams', self)        
        self.button_plot.clicked.connect(self.handle_button_plot_stream)        
        self.button_plotting_setup = QtWidgets.QPushButton('Plotting Setup', self)
        self.button_plotting_setup.clicked.connect(self.handle_button_plotting_setup)
        self.button_plotting_setup.setEnabled(False)
        # For the plotting setup
        self.treeWidgetsub.itemClicked.connect(self.handleItemClicked)
        self.button_unsubscribe.clicked.connect(self.handle_unsubscribe_clicked_setup)
        
        layout_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(layout_widget)
        self.layout.addWidget(layout_widget,4,0,1,2)
        layout.addWidget(self.button_plot)
        layout.addWidget(self.button_plotting_setup)
        layout.addWidget(self.button_clear)        
        self._plot_stream = False
        self.line_colors = [QtGui.QColor(255,0,0),QtGui.QColor(0,255,0),QtGui.QColor(0,0,255),QtGui.QColor(255,0,255)]
        
        self.color_ind = 0

    def handle_button_plotting_setup(self):
        print('HALLO')
        print(self.unsubscribe_item)        
        if(self.unsubscribe_item != None):
            print('JO')
            print(self.unsubscribe_item.stream)
            self.__style = SetupStreamStyle(self.unsubscribe_item.stream)
            self.__style.show()
                         

    def handle_button_plot_stream(self):
        if(self._plot_stream == False):
            self._plot_stream = True
            self.button_plot.setText('Pause Plot')
        else:
            self._plot_stream = False
            self.button_plot.setText('Plot Streams')


    def handle_button_plot_clear(self):
        """
        Clears all the data
        """
        for i,stream in enumerate(self.Datastream.Streams):
            if(stream.stream_type == 'substream'):
                try:
                    stream.pyqtgraph_npdata['ind_end'] = 0
                    stream.pyqtgraph_npdata['ind_start'] = 0
                except Exception as e:
                    pass

    def handleItemClicked(self, item, column):
        """

        Opens a setup dialog for that stream

        """
        print('item',item,'column',column)
        # Try if it is an item with a stream
        try:
            item.stream
        except:
            self.button_plotting_setup.setEnabled(False)
            return
        if(item != None):
            self.button_plotting_setup.setEnabled(True)

    def handle_unsubscribe_clicked_setup(self):
        """
        Grey out plotting setup, if the stream was unsubscribed
        """
        self.button_plotting_setup.setEnabled(False)

    def handle_button_subscribed(self):
        """

        Add a check state box for the subscribed streams, indicating
        if to plot or not, choose color for plot and which data to
        plot against in x and y

        """
        # http://stackoverflow.com/questions/1667688/qcombobox-inside-qtreewidgetitem
        print(self.treeWidgetsub)
        root = self.treeWidgetsub.invisibleRootItem()
        child_count = root.childCount()
        self.treeWidgetsub.setColumnCount(3)
        #self.treeWidgetsub.setHeaderHidden(False)
        print('Columncount',self.treeWidgetsub.columnCount())
        root.setData(0, QtCore.Qt.UserRole, 'blab')
        root.setData(1, QtCore.Qt.UserRole, 'blab')
        column = 0
        for i in range(child_count):
            childitem = root.child(i)
            try:
                childitem.stream.pyqtgraph
            except:
                childitem.stream.pyqtgraph = {'color':self.line_colors[self.color_ind]}
                childitem.stream.pyqtgraph['ind_x'] = 0
                childitem.stream.pyqtgraph['ind_y'] = 1
                self.color_ind += 1
                if(self.color_ind == len(self.line_colors)):
                    self.color_ind = 0                 
                
            childitem.setData(0, QtCore.Qt.UserRole, 'blab')
            childitem.setData(1, QtCore.Qt.UserRole, 'blab')            
            grandchild_count = childitem.childCount()
            print('grandchild',grandchild_count)
            # Add plot options as grandchilds if initialized the first time
            if(grandchild_count == 0):
                childitem.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
                # Create X axis and Y axis data indicators
                ind_x = childitem.stream.pyqtgraph['ind_x']
                ind_y = childitem.stream.pyqtgraph['ind_y']
                strvar_x = str(childitem.stream.variables[ind_x]['name'])
                strvar_y = str(childitem.stream.variables[ind_y]['name'])                
                streamx_txt = 'X Data: ' + strvar_x + ' (' + str(ind_x) + ')'
                streamy_txt = 'Y Data: ' + strvar_y + ' (' + str(ind_y) + ')'
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, [streamx_txt])
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, ['X'])
                self.button_X = QtWidgets.QPushButton('Change X')
                self.button_X.clicked.connect(self.handle_button_XY_clicked)
                self.button_X.stream = childitem.stream
                self.treeWidgetsub.setItemWidget(grandchilditem, 0 , self.button_X)

                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, [streamy_txt])                
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, ['Y'])
                self.button_Y = QtWidgets.QPushButton('Change Y')
                self.button_Y.clicked.connect(self.handle_button_XY_clicked)                
                self.button_Y.stream = childitem.stream
                self.treeWidgetsub.setItemWidget(grandchilditem, 0 , self.button_Y)
                # Create color choosing button
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, ['Color'])
                button = QtWidgets.QPushButton('Color')
                button.clicked.connect(self.handle_button_color_clicked)
                button.pyqtgraph = childitem.stream.pyqtgraph
                color = button.pyqtgraph['color']
                p = button.palette()
                p.setColor(button.backgroundRole(), color)
                button.setPalette(p)
                self.treeWidgetsub.setItemWidget(grandchilditem, 0 , button)
            else:
                print('All here already')


    def handle_button_color_clicked(self):
        """

        Adding a color to the stream 
        
        """
        print('Clicked color')
        dia = QtGui.QColorDialog(self)
        color = dia.getColor()
        button = self.sender()
        button.pyqtgraph['color'] = color
        p = button.palette()
        p.setColor(button.backgroundRole(), color)
        button.setPalette(p)


    def handle_button_XY_clicked(self):
        """

        Choosing the variables of the stream to be plotted
        
        """
        print('Clicked XY')
        layout = QtGui.QVBoxLayout()  # layout for the central widget
        widget = QtGui.QWidget()  # central widget
        widget.setLayout(layout)
        self._number_group=QtWidgets.QButtonGroup() # Number group
        self._number_group.buttonClicked[QtWidgets.QAbstractButton].connect(self.XY_group_clicked)
        button = self.sender()
        for i,var in enumerate(button.stream.variables):
            r0 = QtGui.QRadioButton(str(i) + ': ' + var['name'])
            self._number_group.addButton(r0)
            layout.addWidget(r0)            


        self._XY_widget = widget
        print('Clicked XY show')        
        self._XY_widget.show()
        print('Clicked XY end')

    def XY_group_clicked(self,btn):
        print('Hallo' + str(btn.text()))

class pyqtgraphMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        
        mainMenu = self.menuBar()
        self.setWindowTitle("Python Zeromq Datastream_PlotXY")
        self.setWindowIcon(QtGui.QIcon('logo/pymqdatastream_logo_v0.2.svg.png'))
        extractAction = QtWidgets.QAction("&Quit", self)
        extractAction.setShortcut("Ctrl+Q")
        extractAction.setStatusTip('Closing the program')
        extractAction.triggered.connect(self.close_application)

        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(extractAction)
        
        self.statusBar()


        # Add the pyqtgraphWidget
        self.pyqtgraphwidget = pyqtgraphWidget()
        self.setCentralWidget(self.pyqtgraphwidget)
        
        self.show()
        #self.pyqtgraphwidget.show()

    def close_application(self):
        print('Goodbye!')
        self.pyqtgraphwidget.update_timer.stop()        
        self.close()

        
class pyqtgraphWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.Datastream = pymqdatastream.DataStream(name = 'plotxy')
        list_status = []
        self.color_ind = 0
        # Datastream stuff


        self.datastream_subscribe = DataStreamChoosePlotWidget(self.Datastream,hide_myself = True)

        # The pyqtgraph stuff
        self.pyqtgraph_line = []
        self.pyqtgraph_layout = pg.GraphicsLayoutWidget()
        self.pyqtgraph_axes = self.pyqtgraph_layout.addPlot()
        
        #self.pyqtgraph_axes.setTitle("Title")
        self.pyqtgraph_axes.setLabel('left', "Y Axis")
        self.pyqtgraph_axes.setLabel('bottom', "X Axis")

        # Layout
        splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.datastream_subscribe)
        splitter.addWidget(self.pyqtgraph_layout)        
        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)


        # update the figure once in a while
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_plot)
        timer.start(25)
        self.update_timer = timer
        
        self.setLayout(layout)
        self.bufsize = 20000
        self.buf_tilesize = int ( 0.5 * self.bufsize )
        

    def update_plot(self):
        if(self.datastream_subscribe._plot_stream):
            # Check if the number of streams changed, if yes
            if(len(self.pyqtgraph_line) != ( len(self.Datastream.Streams) - 1 )):
                self.pyqtgraph_line = []
                for i,stream in enumerate(self.Datastream.Streams):
                    if(stream.stream_type == 'substream'):
                        try:         # Check if we have already created a line for the stream
                            self.pyqtgraph_line.append(stream.pyqtgraph_line)
                        except Exception as e:
                            stream.pyqtgraph_line = pg.PlotDataItem( pen=stream.pyqtgraph['color'])
                            stream.pyqtgraph_npdata = {'time':np.zeros((self.bufsize,)),'x':np.zeros((self.bufsize,)),'y':np.zeros((self.bufsize,)),'ind_start':0,'ind_end':0}
                            self.pyqtgraph_axes.addItem(stream.pyqtgraph_line)
                            self.pyqtgraph_line.append({'line':stream.pyqtgraph_line,'uuid':stream.uuid})
                            try: # Check if nplot exists, otherwise create it
                                stream.pyqtgraph_nplot
                            except:
                                stream.pyqtgraph_nplot = 1
                                
                            stream.pyqtgraph_cmod = 0


                self.pyqtgraph_axes.clear()
                for i,stream in enumerate(self.Datastream.Streams):
                    if(stream.stream_type == 'substream'):            
                        self.pyqtgraph_axes.addItem(stream.pyqtgraph_line)

            # Load data and plot
            for i,stream in enumerate(self.Datastream.Streams):
                if(stream.stream_type == 'substream'):
                    # Finally get the data
                    #if(len(stream.deque) > 0):
                    while(len(stream.deque) > 0):
                        data = stream.deque.pop()
                        plot_data = data['data']
                        time_plot_data = data['info']['ts']
                        ind_start = stream.pyqtgraph_npdata['ind_start']
                        ind_end = stream.pyqtgraph_npdata['ind_end']
                        ind_x = stream.pyqtgraph['ind_x']
                        ind_y = stream.pyqtgraph['ind_y']                        
                        for n in range(len(plot_data)):
                            stream.pyqtgraph_cmod += 1
                            if(stream.pyqtgraph_cmod >= stream.pyqtgraph_nplot):
                                stream.pyqtgraph_cmod = 0
                                stream.pyqtgraph_npdata['time'][stream.pyqtgraph_npdata['ind_end']] = time_plot_data
                                stream.pyqtgraph_npdata['x'][stream.pyqtgraph_npdata['ind_end']] = plot_data[n][ind_x]
                                stream.pyqtgraph_npdata['y'][stream.pyqtgraph_npdata['ind_end']] = plot_data[n][ind_y]

                                ind_end += 1
                                if( (ind_end - ind_start ) >= self.buf_tilesize):
                                    ind_start += 1                                            

                                xd = stream.pyqtgraph_npdata['x'][ind_start:ind_end].copy()
                                yd = stream.pyqtgraph_npdata['y'][ind_start:ind_end].copy()
                                stream.pyqtgraph_line.setData(x=xd,y=yd, pen=stream.pyqtgraph['color'])
                                # check for a buffer overflow
                                if(ind_end == self.bufsize ):
                                    stream.pyqtgraph_npdata['time'][0:self.buf_tilesize] = stream.pyqtgraph_npdata['time'][-self.buf_tilesize:]
                                    stream.pyqtgraph_npdata['x'][0:self.buf_tilesize] = stream.pyqtgraph_npdata['x'][-self.buf_tilesize:]
                                    stream.pyqtgraph_npdata['y'][0:self.buf_tilesize] = stream.pyqtgraph_npdata['y'][-self.buf_tilesize:]
                                    ind_end = self.buf_tilesize
                                    ind_start = 0

                                stream.pyqtgraph_npdata['ind_start'] = ind_start
                                stream.pyqtgraph_npdata['ind_end'] = ind_end

            
        
    def handlePlot(self):
        print('Plotting Streams...')
        #self.plot_streams = True



# If run from the command line
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = pyqtgraphMainWindow()
    window.show()
    sys.exit(app.exec_())    
