#!/usr/bin/env python3

#
#
try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except:
    from qtpy import QtCore, QtGui, QtWidgets


import sys
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
#logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)



class pyqtgraphDataStream(pymqdatastream.DataStream):
    """

    A child of a datastream with extensions for pyqtgraph plotting.

    """
    def __init__(self,*args,**kwargs):
        super(pyqtgraphDataStream, self).__init__(*args,**kwargs)
        self.line_colors = [QtGui.QColor(255,0,0),QtGui.QColor(0,255,0),QtGui.QColor(0,0,255),QtGui.QColor(255,0,255)]
        self.color_ind = 0
        self.pyqtgraph = {}        
        self.pyqtgraph['modes']           = ['continous','xlim','xreset']
        self.pyqtgraph['modes_short']     = ['cont','xl','xr']        
        self.pyqtgraph['plot_datastream'] = False
        self.pyqtgraph['flag_change']     = False        
        # Define the plotting mode
        try:
            self.pyqtgraph['mode']
        except:                    
            self.set_plotting_mode()
            
        try:
            self.pyqtgraph['xl']
        except:                                    
            self.pyqtgraph['xl'] = 10

        try:
            self.pyqtgraph['xrs']
        except:                                    
            self.pyqtgraph['xrs'] = None




        self.subscribe_stream_orig = self.subscribe_stream
        self.subscribe_stream  = self.subscribe_stream_pyqtgraph


    def init_stream_settings(self,stream,color = None, bufsize=500000, ind_x = 0, ind_y = 1, plot_data=False, plot_nth_point = 1):
        """

        Initialises the stream with standard settings for plotting if they
        dont already exist. Here nothing well be overwritten. Use
        set_stream_settings for an explicit setting.
        Args:
            stream:
            color:
            bufsize:

        """
        
        # TODO, this should be done in a general routine
        try:
            stream.pyqtgraph
        except:
            stream.pyqtgraph = {}

        # Color information?

        try:
            stream.pyqtgraph['color']
        except:
            if(color == None): # no            
                stream.pyqtgraph['color'] = self.line_colors[self.color_ind]
                self.color_ind += 1
                if(self.color_ind == len(self.line_colors)):
                    self.color_ind = 0
            else:
                stream.pyqtgraph['color'] = color

        # Test if we have already an ind_x/ind_y and a plot_data
        try:
            stream.pyqtgraph['ind_x']
            stream.pyqtgraph['ind_y']
        except:                    
            stream.pyqtgraph['ind_x'] = ind_x
            stream.pyqtgraph['ind_y'] = ind_y

        # Test if we have plot_data
        try:
            stream.pyqtgraph['plot_data']
        except:                    
            stream.pyqtgraph['plot_data'] = plot_data

        # Test if we have a line variable
        try:
            stream.pyqtgraph_line
        except:                    
            stream.pyqtgraph_line = None


        try:
            stream.pyqtgraph['nth_pt']
            stream.pyqtgraph['n_pt_recvd']
        except:                    
            stream.pyqtgraph['nth_pt'] = plot_nth_point
            stream.pyqtgraph['n_pt_recvd'] = 0            

        # Test if we have bufsize etc.
        try:
            stream.pyqtgraph['bufsize']
        except:
            stream.pyqtgraph['bufsize'] = int(bufsize*2)
            stream.pyqtgraph['buf_tilesize'] = bufsize
            bufsize = stream.pyqtgraph['bufsize']            
            stream.pyqtgraph_npdata = {'time':np.zeros((bufsize,)),'x':np.zeros((bufsize,)),'y':np.zeros((bufsize,)),'ind_start':0,'ind_end':0}


    def set_stream_settings(self,stream,color=None,ind_x = None,ind_y = None, plot_data = None, bufsize = None, plot_nth_point = None):
        """
        Sets the plotting settings of the stream
        """
        
        # TODO, this should be done in a general routine
        try:
            stream.pyqtgraph
        except:
            logger.warning('Initialise stream first with init_stream_settings')
            return

        # Color information?
        if(color == None): # No color, take standard color
            stream.pyqtgraph['color'] = self.line_colors[self.color_ind]
            self.color_ind += 1
            if(self.color_ind == len(self.line_colors)):
                self.color_ind = 0
        else:
            stream.pyqtgraph['color'] = color

        # Test if we have already an ind_x/ind_y and a plot_data
        if(ind_x != None):        
            stream.pyqtgraph['ind_x'] = ind_x
        if(ind_y != None):                    
            stream.pyqtgraph['ind_y'] = ind_y
        if(plot_data != None):
            stream.pyqtgraph['plot_data'] = plot_data
        if(bufsize != None):
            stream.pyqtgraph['bufsize'] = int(bufsize*2)
            stream.pyqtgraph['buf_tilesize'] = bufsize
            bufsize = stream.pyqtgraph['bufsize']
            stream.pyqtgraph_npdata = {'time':np.zeros((bufsize,)),'x':np.zeros((bufsize,)),'y':np.zeros((bufsize,)),'ind_start':0,'ind_end':0}


        if(plot_nth_point != None):
            stream.pyqtgraph['nth_pt'] = plot_nth_point

            
    def plot_stream(self,stream,plot_stream=False):
        """
        Defines if the stream is plotted
        """
        stream.pyqtgraph['plot_data'] = plot_stream

            
    def plot_datastream(self,plot_datastream=False):
        """
        Defines if the datastream is plotted
        """
        self.pyqtgraph['plot_datastream'] = plot_datastream

        
    def get_plot_datastream(self):
        """
        Defines if the datastream is plotted
        Returns:
            True/False for plotting/not plotting
        """
        return self.pyqtgraph['plot_datastream']

    def get_plot_modes(self,short=False):
        """
        Returns available plotting modes
        """
        if(short):
            modes = self.pyqtgraph['modes_short']
        else:
            modes = self.pyqtgraph['modes']
            
        return modes


    def subscribe_stream_pyqtgraph(self,*args,**kwargs):
        """
        """
        stream = self.subscribe_stream_orig(*args,**kwargs)
        self.init_stream_settings(stream, bufsize = 5000, plot_data = True, ind_x = 0, ind_y = 1, plot_nth_point = 1)
        return stream
        
            
    def set_plotting_mode(self,mode='cont',xl=None):
        """
        Defines the plotting modes
        Args:
            mode: The plotting modes ("cont": Continous, "xl": xlimit; plots the last data within the xlimits, "xr": Plots until xl is reached, then plot is cleared and started again)
            xl: Xlimit
        """
        logger.debug('set_plotting_mode()')
        # Check if we have the long version of mode, if yes get index and use short version
        for i,m in enumerate(self.pyqtgraph['modes']):
            if(m == mode):
                logger.debug('Long to short mode string ' + m)
                mode = self.pyqtgraph['modes_short'][i]
                break
        # cont mode
        if(mode == self.pyqtgraph['modes_short'][0]):
            logger.debug('Constant mode')
            self.pyqtgraph['mode'] = mode
            self.pyqtgraph['autorange'] = True
            self.pyqtgraph['xrs'] = None            
            return
        # xlim mode
        elif(mode == self.pyqtgraph['modes_short'][1]):
            logger.debug('Xlim mode')            
            if(xl == None):
                logger.warning('Specify xl for the "xl" mode, doing nothing now')
                return
            else:
                self.pyqtgraph['mode'] = mode
                self.pyqtgraph['xl'] = xl
                self.pyqtgraph['autorange'] = True                
                self.pyqtgraph['xrs'] = None                
        # x reset mode
        elif(mode == self.pyqtgraph['modes_short'][2]):
            logger.debug('xr mode')                        
            if(xl == None):
                logger.warning('Specify xl for the "xr" mode, doing nothing now')
                return
            else:
                self.pyqtgraph['mode'] = mode
                self.pyqtgraph['xl'] = xl
                self.pyqtgraph['autorange'] = True                
                self.pyqtgraph['xrs'] = None
                
            


def setup_stream_pyqtgraph(stream):
    """
    Adds data and information to stream needed to for plotting
    """
    pass
    

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

        # Plotting option widgets
        self.combo_plotmode = QtWidgets.QComboBox(self)
        self.combo_plotmode.addItems(self.Datastream.get_plot_modes())
        self.combo_plotmode.currentIndexChanged.connect(self._set_combo_mode)
        xll = QtWidgets.QLabel('X Limit')
        self.lined_xlim = QtWidgets.QLineEdit(self)
        self.lined_xlim.setEnabled(False)
        self.lined_xlim.returnPressed.connect(self._set_xlim)
        self.lined_xlim.setText(str(float(self.Datastream.pyqtgraph['xl'])))
        self.label_xlunit = QtWidgets.QLabel('[]')        
        self.layout_options = QtWidgets.QVBoxLayout()
        self.layout_options.addWidget(self.combo_plotmode)
        self.layout_options.addWidget(xll)
        self.layout_options.addWidget(self.lined_xlim)
        self.layout_options.addWidget(self.label_xlunit)

        
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
            self.Datastream.pyqtgraph['plot_datastream'] = True
            
        self.line_colors = [QtGui.QColor(255,0,0),QtGui.QColor(0,255,0),QtGui.QColor(0,0,255),QtGui.QColor(255,0,255)]
        
        self.color_ind = 0

        self.handle_button_subscribed()
        self.update_button_plot_stream(self.button_plot)
        #.pyqtgraph['ind_x']

    def _set_combo_mode(self):
        """
        """
        print('Hallo setting to mode:',self.combo_plotmode.currentText())
        mode = str(self.combo_plotmode.currentText())
        self.Datastream.set_plotting_mode(mode=mode,xl=10)
        if((mode == self.Datastream.pyqtgraph['modes'][1]) or (mode == self.Datastream.pyqtgraph['modes'][2])):
            self.lined_xlim.setEnabled(True)
            self._set_xlim()
        else:
            self.lined_xlim.setEnabled(False)

    def _set_xlim(self):
        """
        """
        xlim = self.lined_xlim.text()
        try:
            self.Datastream.pyqtgraph['xl'] = float(xlim)
            logger.info("Setting xlim to, " + str(xlim) + ".")            
        except ValueError:
            logger.info("Please select a number, " + str(xlim) + " is not valid.")
                         

    def handle_button_plot_stream(self):
        sender = self.sender()
        if(self.Datastream.pyqtgraph['plot_datastream'] == False):
            self.Datastream.pyqtgraph['plot_datastream'] = True
            sender.setText('Pause Plot')
        else:
            self.Datastream.pyqtgraph['plot_datastream'] = False
            sender.setText('Plot Streams')


    def update_button_plot_stream(self,button):
        if(self.Datastream.pyqtgraph['plot_datastream'] == False):
            button.setText('Plot Streams')
        else:
            button.setText('Pause Plot')            


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
            return


    def handle_unsubscribe_clicked_setup(self):
        """
        Grey out plotting setup, if the stream was unsubscribed
        """
        pass

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
                # Create a plot every nth point option
                label_nplot = QtGui.QLabel('Plot every nth point')
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, [])
                self.treeWidgetsub.setItemWidget(grandchilditem, 0 , label_nplot)                
                spin_nplot = QtGui.QSpinBox()
                spin_nplot.setRange(1, 100000)
                spin_nplot.setValue(childitem.stream.pyqtgraph['nth_pt'])
                spin_nplot.valueChanged.connect(self.handle_plot_nth_point_changed)
                spin_nplot.pyqtgraph = childitem.stream.pyqtgraph
                

                
                grandchilditem = QtWidgets.QTreeWidgetItem(childitem, ['spin'])
                self.treeWidgetsub.setItemWidget(grandchilditem, 0 , spin_nplot)

            else:
                print('All here already')

    def handle_plot_nth_point_changed(self):
        """
        Changes the nth point 
        """
        spin_plot = self.sender()
        nth_point = spin_plot.value()
        logger.debug('Changing spin plot to' + str(nth_point))
        spin_plot.pyqtgraph['nth_pt'] = nth_point
        
        
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
        
        layoutH = QtWidgets.QHBoxLayout()  # layout for the central widget
        widget = QtWidgets.QWidget()  # central widget        
        widget.setLayout(layoutH)        
        layoutX = QtWidgets.QVBoxLayout()  # layout for the central widget
        layoutY = QtWidgets.QVBoxLayout()  # layout for the central widget
        widgetX = QtWidgets.QWidget()  # central widget        
        widgetX.setLayout(layoutX)
        widgetY = QtWidgets.QWidget()  # central widget        
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
            rX = QtWidgets.QRadioButton(str(i) + ': ' + var['name'])
            rX.var_ind = i
            rX.var_name = var['name']
            if(i == self._number_groupX.pyqtgraph['ind_x']):
                rX.toggle()

            self._number_groupX.addButton(rX)
            layoutX.addWidget(rX)

            rY = QtWidgets.QRadioButton(str(i) + ': ' + var['name'])
            rY.var_ind = i
            rY.var_name = var['name']
            if(i == self._number_groupY.pyqtgraph['ind_y']):
                rY.toggle()
                
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
        ind_x_old = self._number_groupX.pyqtgraph['ind_x']
        ind_y_old = self._number_groupY.pyqtgraph['ind_y']        
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
            # If something has changed, clear and set change flag
            if((ind_x != ind_x_old) or (ind_y != ind_y_old)):
                self.handle_button_plot_clear()
                self.Datastream.pyqtgraph['flag_change'] = True
                
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
        try: # Disconnect throws an error with pyqt4
            self.datastream_subscribe.button_close.disconnect()
        except:
            pass
        
        self.datastream_subscribe.button_close.clicked.connect(self.handle_streams)
        self.datastream_subscribe.button_close.setText('Hide')

        # The pyqtgraph stuff
        #self.pyqtgraph_layout = pg.GraphicsLayoutWidget()
        #self.pyqtgraph_axes = self.pyqtgraph_layout.addPlot()
        self.pyqtgraph_axes = pg.PlotWidget(name='plot')
        self.pyqtgraph_leg = self.pyqtgraph_axes.addLegend()
        #self.pyqtgraph_axes.setTitle("Title")
        self.pyqtgraph_axes.setLabel('left', "Y Axis")
        self.pyqtgraph_axes.setLabel('bottom', "X Axis")

        # 
        self.button_streams = QtWidgets.QPushButton('Streams', self)
        self.button_streams.clicked.connect(self.handle_streams)

        self.button_plot = QtWidgets.QPushButton('Plot', self)
        self.button_plot.clicked.connect(self.datastream_subscribe.handle_button_plot_stream)
        self.button_clear = QtWidgets.QPushButton('Clear', self)
        self.button_clear.clicked.connect(self.datastream_subscribe.handle_button_plot_clear)

        self.label_meas = QtWidgets.QLabel('X: ? Y: ?')        

        self.button_close = QtWidgets.QPushButton('Close', self)
        self.button_close.clicked.connect(self.handle_close)                

        # Layout
        self.graph_layout = QtWidgets.QGridLayout()
        self.button_layout = QtWidgets.QVBoxLayout()
        self.button_bottom_layout = QtWidgets.QHBoxLayout()        

        self.graph_layout.addLayout(self.button_layout,0,0)
        self.graph_layout.addLayout(self.button_bottom_layout,1,1)                
        #self.graph_layout.addWidget(self.pyqtgraph_layout)
        self.graph_layout.addWidget(self.pyqtgraph_axes,0,1)
        
        self.button_layout.addWidget(self.button_streams)
        self.button_layout.addWidget(self.button_plot)
        self.button_layout.addWidget(self.button_clear)
        self.button_layout_stretch = self.button_layout.addStretch()
        self.button_layout.addWidget(self.button_close)
        # Thue buttons at the bottom
        self.button_bottom_layout.addStretch()        
        self.button_bottom_layout.addWidget(self.label_meas)

        
        
        layout = QtWidgets.QVBoxLayout()
        #layout.addWidget(self.splitter)
        layout.addLayout(self.graph_layout)

        # Add a position label
        self.vb = self.pyqtgraph_axes.plotItem.vb
        proxy = pg.SignalProxy(self.pyqtgraph_axes.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.pyqtgraph_axes.scene().sigMouseMoved.connect(self.mouseMoved)        


        # update the figure once in a while
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_plot)
        #timer.start(25)
        timer.start(100)
        self.update_timer = timer
        
        self.setLayout(layout)
        self.datastream_subscribe.update_button_plot_stream(self.button_plot)
        

    def update_plot(self):
        """
        The main function of the module: Here all subscribed substreams are plotted
        """
        if(self.Datastream.pyqtgraph['plot_datastream']):
            # Load data and plot
            FLAG_CHANGED = self.Datastream.pyqtgraph['flag_change']
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
                            print('None, add Item')
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
                                stream.pyqtgraph['n_pt_recvd'] += 1                                
                                if(( stream.pyqtgraph['n_pt_recvd'] % stream.pyqtgraph['nth_pt'] ) == 0):
                                    stream.pyqtgraph_npdata['time'][stream.pyqtgraph_npdata['ind_end']] = time_plot_data
                                    stream.pyqtgraph_npdata['x'][stream.pyqtgraph_npdata['ind_end']] = plot_data[n][ind_x]
                                    stream.pyqtgraph_npdata['y'][stream.pyqtgraph_npdata['ind_end']] = plot_data[n][ind_y]
                                    ind_end += 1
                                    if( (ind_end - ind_start ) >= stream.pyqtgraph['buf_tilesize']):
                                        ind_start += 1

                                    xd = stream.pyqtgraph_npdata['x'][ind_start:ind_end].copy()
                                    yd = stream.pyqtgraph_npdata['y'][ind_start:ind_end].copy()

                                    # Test for continous mode
                                    if(self.Datastream.pyqtgraph['mode'] == 'cont'):
                                        # Enable autorange
                                        if(self.Datastream.pyqtgraph['autorange']):
                                            self.Datastream.pyqtgraph['autorange'] = False
                                            self.pyqtgraph_axes.enableAutoRange()
                                            
                                        
                                    # Test for xlim mode                                        
                                    elif(self.Datastream.pyqtgraph['mode'] == 'xl'):
                                        # Enable autorange
                                        if(self.Datastream.pyqtgraph['autorange']):
                                            self.Datastream.pyqtgraph['autorange'] = False
                                            self.pyqtgraph_axes.enableAutoRange()                                        
                                        if(any((xd[-1] - xd) > self.Datastream.pyqtgraph['xl'])):
                                            ind = (xd[-1] - xd) < self.Datastream.pyqtgraph['xl']
                                            xd = xd[ind]
                                            yd = yd[ind]
                                            
                                    elif(self.Datastream.pyqtgraph['mode'] == 'xr'):

                                        # Put some value if xrs has not been defined
                                        if(self.Datastream.pyqtgraph['xrs'] == None):
                                            self.Datastream.pyqtgraph['xrs'] = xd[-1]
                                        # Reset if difference is larger than 'xl'                                            
                                        if((xd[-1] - self.Datastream.pyqtgraph['xrs'])  > self.Datastream.pyqtgraph['xl']):
                                            self.Datastream.pyqtgraph['xrs'] = xd[-1]

                                        self.pyqtgraph_axes.setXRange(self.Datastream.pyqtgraph['xrs'],
                                                                      self.Datastream.pyqtgraph['xrs']+
                                                                      self.Datastream.pyqtgraph['xl'])
                                        

                                    # finally set the data for the line
                                    stream.pyqtgraph_line.setData(x=xd,y=yd, pen=stream.pyqtgraph['color'])


                                    # check for a buffer overflow
                                    if(ind_end == stream.pyqtgraph['bufsize'] ):
                                        #logger.debug('overflow')
                                        stream.pyqtgraph_npdata['time'][0:stream.pyqtgraph['buf_tilesize']] = stream.pyqtgraph_npdata['time'][-stream.pyqtgraph['buf_tilesize']:]
                                        stream.pyqtgraph_npdata['x'][0:stream.pyqtgraph['buf_tilesize']] = stream.pyqtgraph_npdata['x'][-stream.pyqtgraph['buf_tilesize']:]
                                        stream.pyqtgraph_npdata['y'][0:stream.pyqtgraph['buf_tilesize']] = stream.pyqtgraph_npdata['y'][-stream.pyqtgraph['buf_tilesize']:]

                                        ind_end = stream.pyqtgraph['buf_tilesize']
                                        ind_start = 0

                                    stream.pyqtgraph_npdata['ind_start'] = ind_start
                                    stream.pyqtgraph_npdata['ind_end'] = ind_end
            
            if(FLAG_CHANGED):
                print('FLAG_CHANGED!!!')
                FLAG_CHANGED = False
                self.Datastream.pyqtgraph['flag_change'] = False
                
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
                    self.datastream_subscribe.label_xlunit.setText(xaxis_title)
                            

    # http://stackoverflow.com/questions/17783428/how-to-draw-crosshair-and-plot-mouse-position-in-pyqtgraph
    def mouseMoved(self,evt):
        pos = (evt.x(),evt.y())
        if True:
            mousePoint = self.vb.mapSceneToView(evt)
            #self.label_meas.setText("<span style='font-size: 12pt'>x=%f, <span style='color: red'>y1=%f</span>" % (mousePoint.x(), mousePoint.y()))
            self.label_meas.setText("<span style='font-size: 8pt'>x=%f, y=%f</span>" % (mousePoint.x(), mousePoint.y()))
        

    def handlePlot(self):
        print('Plotting Streams...')
        #self.plot_streams = True

    def handle_streams(self):
        """
        Show/hide stream subscribe/plot widget
        """
        # Update the pause plot button
        self.datastream_subscribe.update_button_plot_stream(self.button_plot)
        self.datastream_subscribe.update_button_plot_stream(self.datastream_subscribe.button_plot)        
        if(self.sender() == self.datastream_subscribe.button_close):
            #self.graph_layout.replaceWidget(self.datastream_subscribe,self.button_streams)
            self.button_layout.addWidget(self.button_streams)
            self.button_layout.addWidget(self.button_plot)
            self.button_layout.addWidget(self.button_clear)            
            self.button_layout.addWidget(self.button_close)
            #self.button_layout.removeWidget(self.button_close)
            self.button_layout.removeWidget(self.datastream_subscribe)                                    
            self.datastream_subscribe.hide()
            self.button_streams.show()
            self.button_close.show()
            self.button_plot.show()
            self.button_clear.show()            
        else:
            #self.graph_layout.replaceWidget(self.button_streams,self.datastream_subscribe)
            self.button_layout.removeWidget(self.button_streams)
            self.button_layout.removeWidget(self.button_close)
            self.button_layout.removeWidget(self.button_plot)
            self.button_layout.removeWidget(self.button_clear)      
            self.button_layout.addWidget(self.datastream_subscribe)                        
            self.button_streams.hide()
            self.button_close.hide()
            self.button_plot.hide()
            self.button_clear.hide()                                    
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

def main():
    datastream_help = 'Subscribe to datastream with address e.g. -d tcp://192.168.178.97:18055'
    stream_help = 'Plots stream of address: e.g. -pd e47e9e56-ae34-11e6-8b71-00247ee0ea87::tcp://127.0.0.1:28736@tcp://127.0.0.1:18055'            
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    #parser.add_argument('--datastream', '-d', nargs = '?', default = False, help=datastream_help)
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
    datastream = pyqtgraphDataStream(name = 'plotxy', logging_level=logging_level)
    if(args.plot_stream != None):
        num_streams = len(args.plot_stream)
        logger.debug('main: creating a datastream')        
        
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
                    datastream.pyqtgraph['plot_datastream'] = True
            else:
                logger.warning('Wrong number of arguments')
                

    else:
        logger.warning('Need an address for the stream, e.g.: ' + stream_help)


    app = QtWidgets.QApplication(sys.argv)
    window = pyqtgraphMainWindow(datastream = datastream, logging_level = logging_level)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
