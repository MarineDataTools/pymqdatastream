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
import argparse
import pymqdatastream
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service
import time

#import datastream.qt.pyqtgraph_service as datastream_pyqtgraph_service


# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

logger = logging.getLogger('pymqds_plotxy')
logger.setLevel(logging.INFO)



class pyqtgraphDataStream(pymqdatastream.DataStream):
    """

    A child of a datastream with extensions for pyqtgraph plotting

    """
    def __init__(self,*args,**kwargs):
        super(pyqtgraphDataStream, self).__init__(*args,**kwargs)
        self.pyqtgraph = {}
        self.pyqtgraph['plot_stream'] = False        


def setup_stream_pyqtgraph(stream):
    """
    Adds data and information to stream needed to for plotting
    """
    pass
    

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
    def __init__(self,*args,**kwargs):
        super(DataStreamChoosePlotWidget, self).__init__(*args,**kwargs)
        #datastream_qt_service.DataStreamSubscribeWidget.__init__(self,Datastream, hide_myself)
        self.button_subscribe.setText('Add Stream')
        self.button_subscribe.clicked.connect(self.handle_button_subscribed)
        self.button_unsubscribe.setText('Remove Stream')
        self.button_clear = QtWidgets.QPushButton('Clear', self)
        self.button_clear.clicked.connect(self.handle_button_plot_clear)
        self.button_plot = QtWidgets.QPushButton('Plot Streams', self)        
        self.button_plot.clicked.connect(self.handle_button_plot_stream)        

        # For the plotting setup
        self.treeWidgetsub.itemClicked.connect(self.handleItemClicked)
        self.button_unsubscribe.clicked.connect(self.handle_unsubscribe_clicked_setup)
        # Plotting options
        self.button_plotting_setup = QtWidgets.QPushButton('Plotting Setup', self)
        self.button_plotting_setup.clicked.connect(self.handle_button_plotting_setup)
        self.button_plotting_setup.setEnabled(False)        
        self.layout_options = QtWidgets.QVBoxLayout()
        self.layout_options.addWidget(self.button_plotting_setup)
        
        layout_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(layout_widget)
        self.layout.addWidget(layout_widget,4,0,1,2)
        self.layout.addLayout(self.layout_options,1,2)        
        layout.addWidget(self.button_plot)
        layout.addWidget(self.button_clear)


        # Check if we have already the dictionary pyqtgraph in the Datastream object
        try:
            self.Datastream.pyqtgraph
        except:
            self.Datastream.pyqtgraph = {}
            self.Datastream.pyqtgraph['plot_stream'] = True
            
        self.line_colors = [QtGui.QColor(255,0,0),QtGui.QColor(0,255,0),QtGui.QColor(0,0,255),QtGui.QColor(255,0,255)]
        
        self.color_ind = 0

        self.handle_button_subscribed()
        #.pyqtgraph['ind_x']

    def handle_button_plotting_setup(self):
        print('HALLO')
        print(self.unsubscribe_item)        
        if(self.unsubscribe_item != None):
            print('JO')
            print(self.unsubscribe_item.stream)
            self.__style = SetupStreamStyle(self.unsubscribe_item.stream)
            self.__style.show()
                         

    def handle_button_plot_stream(self):
        if(self.Datastream.pyqtgraph['plot_stream'] == False):
            self.Datastream.pyqtgraph['plot_stream'] = True
            self.button_plot.setText('Pause Plot')
        else:
            self.Datastream.pyqtgraph['plot_stream'] = False
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

        The basic subscription procedure is done in the inherited module, here
        extra stuff special for pyqtgraph are handled. Add a check
        state box for the subscribed streams, indicating if to plot or
        not, choose color for plot and which data to plot against in x
        and y.

        """
        # http://stackoverflow.com/questions/1667688/qcombobox-inside-qtreewidgetitem
        print(self.treeWidgetsub)
        root = self.treeWidgetsub.invisibleRootItem()
        child_count = root.childCount()
        self.treeWidgetsub.setColumnCount(1)
        #self.treeWidgetsub.setHeaderHidden(False)
        print('Columncount',self.treeWidgetsub.columnCount())
        root.setData(0, QtCore.Qt.UserRole, 'blab')
        root.setData(1, QtCore.Qt.UserRole, 'blab')
        column = 0
        for i in range(child_count):
            childitem = root.child(i)
            # do we have a pyqtgraph dictionary for plotting information?
            # TODO, this should be done in a general routine
            try:
                childitem.stream.pyqtgraph
            except:
                childitem.stream.pyqtgraph = {}

            # Color information?
            try:
                childitem.stream.pyqtgraph['color']
            except:
                childitem.stream.pyqtgraph['color'] = self.line_colors[self.color_ind]
                self.color_ind += 1
                if(self.color_ind == len(self.line_colors)):
                    self.color_ind = 0

            # Test if we have already an ind_x/ind_y and a plot_data
            try:
                childitem.stream.pyqtgraph['ind_x']
                childitem.stream.pyqtgraph['ind_y']
            except:                    
                childitem.stream.pyqtgraph['ind_x'] = 0
                childitem.stream.pyqtgraph['ind_y'] = 1

            # Test if we have plot_data
            try:
                childitem.stream.pyqtgraph['plot_data']
            except:                    
                childitem.stream.pyqtgraph['plot_data'] = False

            # Test if we have a line variable
            try:
                childitem.stream.pyqtgraph_line
            except:                    
                childitem.stream.pyqtgraph_line = None
                #childitem.stream.pyqtgraph['bufsize'] = 200000
                childitem.stream.pyqtgraph['bufsize'] = 1000
                childitem.stream.pyqtgraph['buf_tilesize'] = int(childitem.stream.pyqtgraph['bufsize']/2)
                bufsize = childitem.stream.pyqtgraph['bufsize']
                childitem.stream.pyqtgraph_npdata = {'time':np.zeros((bufsize,)),'x':np.zeros((bufsize,)),'y':np.zeros((bufsize,)),'ind_start':0,'ind_end':0}
                childitem.stream.pyqtgraph_nplot = 1
                childitem.stream.pyqtgraph_cmod = 0


            # Define the plotting mode
            try:
                childitem.stream.pyqtgraph['mode']
            except:                    
                #childitem.stream.pyqtgraph['mode'] = 'cont'
                #childitem.stream.pyqtgraph['mode'] = 'xl'
                childitem.stream.pyqtgraph['mode'] = 'xr'

            try:
                childitem.stream.pyqtgraph['xl']
            except:                                    
                childitem.stream.pyqtgraph['xl'] = 10

            try:
                childitem.stream.pyqtgraph['xrs']
            except:                                    
                childitem.stream.pyqtgraph['xrs'] = 0                

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
                childitem.stream.pyqtgraph['itemX'] = grandchilditem
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, [streamy_txt])
                childitem.stream.pyqtgraph['itemY'] = grandchilditem                                
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, ['Y'])
                self.button_Y = QtWidgets.QPushButton('Change X/Y data')
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
                # Create a plot option
                check_plot = QtWidgets.QCheckBox()
                check_plot.setText('Plot stream')
                check_plot.setChecked(childitem.stream.pyqtgraph['plot_data'])
                check_plot.stateChanged.connect(self.handle_check_plot_changed)
                check_plot.pyqtgraph = childitem.stream.pyqtgraph
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, [])                
                self.treeWidgetsub.setItemWidget(grandchilditem, 0 , check_plot)                
            else:
                print('All here already')

    def handle_check_plot_changed(self):
        """
        """
        print('Check plot change!')
        check_plot = self.sender()
        check_plot.pyqtgraph['plot_data'] = check_plot.isChecked()

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
        button = self.sender()
        
        layoutH = QtGui.QHBoxLayout()  # layout for the central widget
        widget = QtGui.QWidget()  # central widget        
        widget.setLayout(layoutH)        
        layoutX = QtGui.QVBoxLayout()  # layout for the central widget
        layoutY = QtGui.QVBoxLayout()  # layout for the central widget        
        widgetX = QtGui.QWidget()  # central widget        
        widgetX.setLayout(layoutX)
        widgetY = QtGui.QWidget()  # central widget        
        widgetY.setLayout(layoutY)
        layoutH.addWidget(widgetX)
        layoutH.addWidget(widgetY)

        self._number_groupX=QtWidgets.QButtonGroup() # Number group
        self._number_groupY=QtWidgets.QButtonGroup() # Number group        

        self._number_groupX.buttonClicked[QtWidgets.QAbstractButton].connect(self.XY_group_clicked)
        self._number_groupY.buttonClicked[QtWidgets.QAbstractButton].connect(self.XY_group_clicked)
        # To get the indices
        self._number_groupX.pyqtgraph = button.stream.pyqtgraph
        self._number_groupY.pyqtgraph = button.stream.pyqtgraph        
        

            
        labX = QtWidgets.QLabel('X-Axis')
        labY = QtWidgets.QLabel('Y-Axis')
        layoutX.addWidget(labX)
        layoutY.addWidget(labY)
        for i,var in enumerate(button.stream.variables):
            rX = QtGui.QRadioButton(str(i) + ': ' + var['name'])
            rX.var_ind = i
            rX.var_name = var['name']            
            self._number_groupX.addButton(rX)
            layoutX.addWidget(rX)

            rY = QtGui.QRadioButton(str(i) + ': ' + var['name'])
            rY.var_ind = i
            rY.var_name = var['name']
            self._number_groupY.addButton(rY)
            layoutY.addWidget(rY)               

        self._button_XY_appl = QtWidgets.QPushButton('Apply')
        self._button_XY_cancl = QtWidgets.QPushButton('Cancel')        
        self._button_XY_appl.clicked.connect(self.handle_button_XY_appl_cancl_clicked)
        self._button_XY_cancl.clicked.connect(self.handle_button_XY_appl_cancl_clicked)

        layoutX.addWidget(self._button_XY_appl)
        layoutY.addWidget(self._button_XY_cancl)

        self._XY_widget = widget
        print('Clicked XY show')        
        self._XY_widget.show()
        print('Clicked XY end')

    def XY_group_clicked(self,btn):
        #print(self.sender().text())
        print('Hallo' + str(btn.text()),btn.var_ind)
        #if(self.sender() == self._number_groupX):
        #    print('X-Axis')
        #    self._number_groupX.pyqtgraph['ind_x'] = btn.var_ind
        #if(self.sender() == self._number_groupY):
        #    print('Y-Axis')
        #    self._number_groupY.pyqtgraph['ind_y'] = btn.var_ind            
        
    def handle_button_XY_appl_cancl_clicked(self):
        ind_x = self._number_groupX.checkedButton().var_ind
        ind_y = self._number_groupY.checkedButton().var_ind
        name_x = self._number_groupX.checkedButton().var_name
        name_y = self._number_groupY.checkedButton().var_name       
        print(ind_x,ind_y)
        if(self.sender() == self._button_XY_appl):
            self._number_groupX.pyqtgraph['ind_x'] = ind_x
            self._number_groupY.pyqtgraph['ind_y'] = ind_y
            streamx_txt = 'X Data: ' + name_x + ' (' + str(ind_x) + ')'            
            self._number_groupY.pyqtgraph['itemX'].setText(0,streamx_txt)
            streamy_txt = 'Y Data: ' + name_y + ' (' + str(ind_y) + ')'
            self._number_groupY.pyqtgraph['itemY'].setText(0,streamy_txt)            
            self._XY_widget.close()            
        if(self.sender() == self._button_XY_cancl):
            self._XY_widget.close()


        
class pyqtgraphWidget(QtWidgets.QWidget):
    """
    
    Widget to plot data

    """
    def __init__(self, datastream = None, logging_level = logging.INFO):
        """
        
        Args:

        """
        QtWidgets.QWidget.__init__(self)
        if(datastream == None):
            self.Datastream = pymqdatastream.DataStream(name = 'plotxy', logging_level=logging_level)
        else:
            self.Datastream = datastream
            
        list_status = []
        self.color_ind = 0
        # Datastream stuff
        self.datastream_subscribe = DataStreamChoosePlotWidget(self.Datastream,hide_myself = True, stream_type='pubstream')
        # Connect the close button to a different function
        self.datastream_subscribe.button_close.disconnect()
        self.datastream_subscribe.button_close.clicked.connect(self.handle_streams)
        self.datastream_subscribe.button_close.setText('Hide')

        # The pyqtgraph stuff
        self.pyqtgraph_layout = pg.GraphicsLayoutWidget()
        self.pyqtgraph_axes = self.pyqtgraph_layout.addPlot()
        self.pyqtgraph_leg = self.pyqtgraph_axes.addLegend()
        #self.pyqtgraph_axes.setTitle("Title")
        self.pyqtgraph_axes.setLabel('left', "Y Axis")
        self.pyqtgraph_axes.setLabel('bottom', "X Axis")

        # 
        self.button_streams = QtWidgets.QPushButton('Streams', self)
        self.button_streams.clicked.connect(self.handle_streams)

        self.button_close = QtWidgets.QPushButton('Close', self)
        self.button_close.clicked.connect(self.handle_close)                

        # Layout
        self.graph_layout = QtWidgets.QHBoxLayout()
        self.button_layout = QtWidgets.QVBoxLayout()
        self.button_layout.setAlignment(QtCore.Qt.AlignTop)

        self.graph_layout.addLayout(self.button_layout)        
        self.graph_layout.addWidget(self.pyqtgraph_layout)
        
        self.button_layout.addWidget(self.button_streams)
        self.button_layout.addWidget(self.button_close)
        
        
        layout = QtWidgets.QVBoxLayout()
        #layout.addWidget(self.splitter)
        layout.addLayout(self.graph_layout)


        # update the figure once in a while
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_plot)
        timer.start(25)
        self.update_timer = timer
        
        self.setLayout(layout)
        

    def update_plot(self):
        """
        The main function of the module: Here all subscribed substreams are plotted
        """
        if(self.Datastream.pyqtgraph['plot_stream']):
            # Load data and plot
            FLAG_CHANGED = False
            for i,stream in enumerate(self.Datastream.Streams):
                if(stream.stream_type == 'substream'):
                    # No plotting of this stream
                    if(stream.pyqtgraph['plot_data'] == False):
                        if(not stream.pyqtgraph_line == None):
                            self.pyqtgraph_axes.removeItem(stream.pyqtgraph_line)
                            stream.pyqtgraph_line = None
                            #stream.pyqtgraph_line.setData(x=[],y=[], pen=stream.pyqtgraph['color'])
                            stream.pyqtgraph_npdata['ind_end'] = 0
                            stream.pyqtgraph_npdata['ind_start'] = 0
                            FLAG_CHANGED = True
                            
                        # Get rid of accumulated data
                        while(len(stream.deque) > 0):
                            data = stream.deque.pop()

                    # Plotting of this stream                            
                    else:
                        ind_x = stream.pyqtgraph['ind_x']
                        ind_y = stream.pyqtgraph['ind_y']                        
                        # Create a new line object for the stream
                        if(stream.pyqtgraph_line == None):
                            FLAG_CHANGED = True
                            print('None')
                            sname = stream.name + ' x: ' + stream.variables[ind_x]['name'] +  ' y:' + stream.variables[ind_y]['name']
                            stream.pyqtgraph_line = pg.PlotDataItem( pen=stream.pyqtgraph['color'],name = sname)
                            li = self.pyqtgraph_axes.addItem(stream.pyqtgraph_line,name= 'test')
                            #self.pyqtgraph_axes.clear()

                            
                        # Finally get the data
                        while(len(stream.deque) > 0):
                            data = stream.deque.pop()
                            plot_data = data['data']
                            time_plot_data = data['info']['ts']
                            ind_start = stream.pyqtgraph_npdata['ind_start']
                            ind_end = stream.pyqtgraph_npdata['ind_end']
                            for n in range(len(plot_data)):
                                stream.pyqtgraph_cmod += 1
                                if(stream.pyqtgraph_cmod >= stream.pyqtgraph_nplot):
                                    stream.pyqtgraph_cmod = 0
                                    stream.pyqtgraph_npdata['time'][stream.pyqtgraph_npdata['ind_end']] = time_plot_data
                                    stream.pyqtgraph_npdata['x'][stream.pyqtgraph_npdata['ind_end']] = plot_data[n][ind_x]
                                    stream.pyqtgraph_npdata['y'][stream.pyqtgraph_npdata['ind_end']] = plot_data[n][ind_y]
                                    ind_end += 1
                                    if( (ind_end - ind_start ) >= stream.pyqtgraph['buf_tilesize']):
                                        ind_start += 1

                                    xd = stream.pyqtgraph_npdata['x'][ind_start:ind_end].copy()
                                    yd = stream.pyqtgraph_npdata['y'][ind_start:ind_end].copy()

                                    # Test for xlim mode
                                    if(stream.pyqtgraph['mode'] == 'xl'):
                                        if(any((xd[-1] - xd) > stream.pyqtgraph['xl'])):
                                            ind = (xd[-1] - xd) < stream.pyqtgraph['xl']
                                            xd = xd[ind]
                                            yd = yd[ind]
                                            
                                    elif(stream.pyqtgraph['mode'] == 'xr'):
                                        # Reset if difference is larger than 'xl'
                                        if((xd[-1] - stream.pyqtgraph['xrs'])  > stream.pyqtgraph['xl']):
                                            stream.pyqtgraph['xrs'] = xd[-1]

                                        self.pyqtgraph_axes.setXRange(stream.pyqtgraph['xrs'],stream.pyqtgraph['xrs']+stream.pyqtgraph['xl'])
                                    # finally set the data for the line
                                    stream.pyqtgraph_line.setData(x=xd,y=yd, pen=stream.pyqtgraph['color'])


                                    # check for a buffer overflow
                                    if(ind_end == stream.pyqtgraph['bufsize'] ):
                                        stream.pyqtgraph_npdata['time'][0:stream.pyqtgraph['buf_tilesize']] = stream.pyqtgraph_npdata['time'][-stream.pyqtgraph['buf_tilesize']:]
                                        stream.pyqtgraph_npdata['x'][0:stream.pyqtgraph['buf_tilesize']] = stream.pyqtgraph_npdata['x'][-stream.pyqtgraph['buf_tilesize']:]
                                        stream.pyqtgraph_npdata['y'][0:stream.pyqtgraph['buf_tilesize']] = stream.pyqtgraph_npdata['y'][-stream.pyqtgraph['buf_tilesize']:]

                                        ind_end = stream.pyqtgraph['buf_tilesize']
                                        ind_start = 0

                                    stream.pyqtgraph_npdata['ind_start'] = ind_start
                                    stream.pyqtgraph_npdata['ind_end'] = ind_end
            
            if(FLAG_CHANGED):
                print('FLAG_CHANGED!!!')
                self.pyqtgraph_axes.clear()
                self.pyqtgraph_leg.close()                
                self.pyqtgraph_leg = self.pyqtgraph_axes.addLegend()
                nplot = 0
                xaxis_title = ' '
                yaxis_title = ' '                
                for i,stream in enumerate(self.Datastream.Streams):
                    if(stream.stream_type == 'substream'):
                        # No plotting of this stream
                        if(stream.pyqtgraph['plot_data'] == True):
                            li = self.pyqtgraph_axes.addItem(stream.pyqtgraph_line)
                            nplot += 1
                            ind_x = stream.pyqtgraph['ind_x']
                            ind_y = stream.pyqtgraph['ind_y']
                            xaxis_title = stream.variables[ind_x]['name'] + ' [' + stream.variables[ind_x]['unit'] + ']'
                            yaxis_title = stream.variables[ind_y]['name'] + ' [' + stream.variables[ind_y]['unit'] + ']'
                            


                # Only one plot, so we can easily set x/y-axes text
                #if(nplot == 1):
                if(True):
                    self.pyqtgraph_axes.setLabel('bottom', xaxis_title)                    
                    self.pyqtgraph_axes.setLabel('left', yaxis_title)                            
                            
                    



    def handlePlot(self):
        print('Plotting Streams...')
        #self.plot_streams = True

    def handle_streams(self):
        """
        Show/hide stream subscribe/plot widget
        """
        if(self.sender() == self.datastream_subscribe.button_close):
            #self.graph_layout.replaceWidget(self.datastream_subscribe,self.button_streams)
            self.button_layout.addWidget(self.button_streams)
            self.button_layout.removeWidget(self.button_close)
            self.button_layout.removeWidget(self.datastream_subscribe)                                    
            self.datastream_subscribe.hide()
            self.button_streams.show()
            self.button_close.show()
        else:
            #self.graph_layout.replaceWidget(self.button_streams,self.datastream_subscribe)
            self.button_layout.removeWidget(self.button_streams)
            self.button_layout.removeWidget(self.button_close)
            self.button_layout.addWidget(self.datastream_subscribe)                        
            self.button_streams.hide()
            self.button_close.hide()            
            self.datastream_subscribe.show()


    def handle_close(self):
        """
        Closes the widget
        """
        print('Closing!')
        self.datastream_subscribe.close()
        self.update_timer.stop()                
        self.Datastream.close()
        print('Closed Datastream!')
        self.close()
        

            


class pyqtgraphMainWindow(QtWidgets.QMainWindow):
    def __init__(self, datastream = None, logging_level = logging.INFO):
        QtWidgets.QMainWindow.__init__(self)
        mainMenu = self.menuBar()
        self.setWindowTitle("Python Zeromq Datastream_PlotXY")
        self.setWindowIcon(QtGui.QIcon('logo/pymqdatastream_logo_v0.2.svg.png'))
        extractActionA = QtWidgets.QAction("&Add Graph", self)
        extractActionA.setShortcut("Ctrl+A")
        extractActionA.setStatusTip('Adding a new graph')
        extractActionA.triggered.connect(self.add_graph)
        extractAction = QtWidgets.QAction("&Quit", self)
        extractAction.setShortcut("Ctrl+Q")
        extractAction.setStatusTip('Closing the program')
        extractAction.triggered.connect(self.close_application)        

        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(extractAction)
        graphMenu = mainMenu.addMenu('&Graphs')
        graphMenu.addAction(extractActionA)        
        
        self.statusBar()

        # Add the pyqtgraphWidget
        self.pyqtgraphs = []
        mainwidget = QtWidgets.QWidget(self)        
        self.layout = QtWidgets.QVBoxLayout(mainwidget)
        self.pyqtgraphwidget = pyqtgraphWidget(datastream = datastream, logging_level = logging_level)
        self.layout.addWidget(self.pyqtgraphwidget)
        self.pyqtgraphs.append(self.pyqtgraphwidget)
        self.logging_level = logging_level

        
        mainwidget.setFocus()
        self.setCentralWidget(mainwidget)
        #self.show()

    def add_graph(self,datastream = None):
        print('Adding graph!')
        pyqtgraphwidget = pyqtgraphWidget( datastream = datastream, logging_level = self.logging_level )        
        self.pyqtgraphs.append(pyqtgraphwidget)
        self.layout.addWidget(pyqtgraphwidget)

    def close_application(self):
        print('Goodbye!')
        self.pyqtgraphwidget.update_timer.stop()        
        self.close()        



# If run from the command line
if __name__ == "__main__":

    datastream_help = 'Subscribe to datastream with address e.g. -d tcp://192.168.178.97:18055'
    stream_help = 'Plots stream of address: e.g. -pd e47e9e56-ae34-11e6-8b71-00247ee0ea87::tcp://127.0.0.1:28736@tcp://127.0.0.1:18055'            
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--datastream', '-d', nargs = '?', default = False, help=datastream_help)
    parser.add_argument('--plot_stream', '-pd', nargs = '+', action = 'append', help=stream_help)
    args = parser.parse_args()

    logging_level = logging.INFO
    if(args.verbose == None):
        logging_level = logging.CRITICAL        
    elif(args.verbose == 1):
        logging_level = logging.INFO
    elif(args.verbose >= 2):
        print('Debug logging level')
        logging_level = logging.DEBUG


    logger.setLevel(logging_level)
    
    datastream = None
    print('Hallo',args.plot_stream)
    if(args.plot_stream != None):
        num_streams = len(args.plot_stream)
        logger.debug('main: creating a datastream')        
        datastream = pymqdatastream.DataStream(name = 'plotxy', logging_level=logging_level)        
        for sp in args.plot_stream:
            if(len(sp) == 1 or len(sp) == 3):
                logger.debug('main: Plotting stream: ' + str(sp))
                saddress = sp[0]
                good_address = pymqdatastream.check_stream_address_str(saddress)
                logger.debug('main: Address good?: ' + str(good_address))
                if(good_address):
                    stream = datastream.subscribe_stream(saddress)
                    stream.pyqtgraph = {}
                    if(len(sp) == 3):
                        ind_x = int(sp[1])
                        ind_y = int(sp[2])
                    else:
                        ind_x = 0
                        ind_y = 1

                    stream.pyqtgraph['ind_x'] = ind_x
                    stream.pyqtgraph['ind_y'] = ind_y
                    stream.pyqtgraph['plot_data'] = True
                    datastream.pyqtgraph = {}
                    datastream.pyqtgraph['plot_stream'] = True
            else:
                logger.warning('Wrong number of arguments')
                

    else:
        logger.warning('Need an address for the stream, e.g.: ' + stream_help)


    app = QtWidgets.QApplication(sys.argv)
    window = pyqtgraphMainWindow(datastream = datastream, logging_level = logging_level)
    window.show()
    sys.exit(app.exec_())
