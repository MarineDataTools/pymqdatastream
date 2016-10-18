#!/usr/bin/env python3
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import json
import logging
import pymqdatastream
import datetime

# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
# Setup logging module
logger = logging.getLogger('qt_service')
logger.setLevel(logging.DEBUG)


def addParent(parent, column, title, data):
    item = QtWidgets.QTreeWidgetItem(parent, [title])
    item.setData(column, QtCore.Qt.UserRole, data)
    item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
    item.setExpanded(False)
    return item


def addChild(parent, column, title, data):
    item = QtWidgets.QTreeWidgetItem(parent, [title])
    item.setData(column, QtCore.Qt.UserRole, data)
    #item.setCheckState(column, QtCore.Qt.Unchecked)
    return item

def print_dict(d,indent=0):
    ind = '     ' * indent
    for n,item in enumerate(d.items()):
        if isinstance(item[1],dict):
            print('dict',item[0])
            print_dict(item[1])
        elif isinstance(item[1],list):
            print('list',item[0])
            for nl,iteml in enumerate(item[1]):
                if(isinstance(iteml,dict)):
                    print_dict(iteml)
                else:
                    print(ind,'item',item[0],'data:',item[1])
        else:
            print(ind,'item',item[0],'data:',item[1])


class DataStreamStatusViewWidget(QtWidgets.QWidget):
    """

    A widget showing a qtree of the datastream object


    """
    def __init__(self,status_list):
        QtWidgets.QWidget.__init__(self)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.treeWidget = QtWidgets.QTreeWidget()
        self.treeWidget.setHeaderHidden(True)
        self.populate_with_status(status_list)
        self.layout.addWidget(self.treeWidget)        

    def populate_with_status(self,status_list):
        self.treeWidget.clear()
        for status in status_list:
            datastream_remote = pymqdatastream.create_datastream_from_info_dict(status)
            datastream_name = datastream_remote.get_name_str(strtype = 'simple_newline')
            status_tree = self.addParent(self.treeWidget.invisibleRootItem(), 0, datastream_name, 'data Clients')
            self.tree_from_datastream_status_dict(status_tree,status)

    def tree_from_datastream_status_dict(self,parent,d):
        '''
        Creates a Qt Tree from a datastream status dictionary
        '''
        column = 0 
        for n,item in enumerate(d.items()):
            treeitem = self.addParent(parent, column, item[0], 'data Type ' + str(n))
            if isinstance(item[1],dict):
                #print('dict',item[0])
                self.tree_from_datastream_status_dict(treeitem,item[1])
            elif isinstance(item[1],list):
                #print('list',item[0])
                for nl,iteml in enumerate(item[1]):
                    if(isinstance(iteml,dict)):
                        #if('num' in iteml):
                        if True:
                            name = str(nl)
                            if('stream_type' in iteml):
                                name += ' (' + iteml['stream_type'] 
                                if(iteml['stream_type'] == 'control'):
                                    name += '@' + iteml['socket']['address']
                                    
                                name += ')'
                            treeitemd = self.addParent(treeitem, column, name, 'data Type ' + str(n))
                            self.tree_from_datastream_status_dict(treeitemd,iteml)
                        #else:
                        #    self.tree_from_datastream_status_dict(treeitem,iteml)
                    else:
                        #print('item',item[0],'data:',item[1])
                        treedata = self.addChild(treeitem, column, str(iteml), 'data Type ' + str(n))
            else:
                treedata = self.addChild(treeitem, column, str(item[1]), 'data Type ' + str(n))

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



class DataStreamAddresslist(QtWidgets.QWidget):
    """
    Choose list of addresses addresslist
    This has to be completed
    """
    def __init__(self,addresses = []):
        QtWidgets.QWidget.__init__(self)
        self.layout = QtWidgets.QGridLayout(self)
        self.address_dialog = QtWidgets.QInputDialog(self)
        self.addr_table = QtWidgets.QTableWidget()
        self.addr_table.setColumnCount(1)
        self.addr_table.horizontalHeader().setStretchLastSection(True)
        #self.addr_table.itemChanged.connect(self.update_address_list) 

        self.addresses = addresses
        print('Hallo addresses',self.addresses)
        self.populate_table_from_address_list()
        # Buttons
        self.button_apply = QtWidgets.QPushButton('Apply', self)
        self.button_close = QtWidgets.QPushButton('Close', self)        
        self.button_new = QtWidgets.QPushButton('Add', self)
        self.button_del = QtWidgets.QPushButton('Delete', self)        
        self.button_new.clicked.connect(self.new_address)
        self.button_del.clicked.connect(self.del_address)
        self.button_close.clicked.connect(self.clicked_close)
        self.button_apply.clicked.connect(self.update_address_list)                
        # Layout
        self.layout.addWidget(self.button_new,0,0)
        self.layout.addWidget(self.button_del,0,1)                        
        self.layout.addWidget(self.button_apply,0,2)
        self.layout.addWidget(self.button_close,0,3)        
        self.layout.addWidget(self.addr_table,1,0,2,4)

    def new_address(self):
        rowPosition = self.addr_table.rowCount()
        self.addr_table.insertRow(rowPosition)
        self.addr_table.setItem(rowPosition,
                            0, QtWidgets.QTableWidgetItem( 'tcp://' ))

    def del_address(self):
        #rowPosition = self.addr_table.rowCount()
        #self.addr_table.removeRow(rowPosition-1)
        print(self.addr_table.selectedIndexes())
        print(self.addr_table.selectedIndexes()[0].row())
        for item in self.addr_table.selectedItems():
            ind = self.addr_table.indexFromItem(item)
            row = ind.row()
            self.addr_table.removeRow(row)
            #self.update_address_list()

    def populate_table_from_address_list(self):
        self.addr_table.clear()
        for addr in self.addresses:
            rowPosition = self.addr_table.rowCount()
            self.addr_table.insertRow(rowPosition)
            self.addr_table.setItem(rowPosition,
                                    0, QtWidgets.QTableWidgetItem( addr ))        

    def update_address_list(self):
        logger.debug('updating list')
        self.addresses = []
        rows = self.addr_table.rowCount()
        for row in range(rows):
            item = self.addr_table.item(row,0)
            text = str(item.text())
            self.addresses.append(text)

        print(self.addresses)

    def clicked_close(self):
        self.close()

    def get_addresses(self):
        return self.addresses  
        
        


        
class DataStreamSubscribeWidget(QtWidgets.QWidget):
    """ This widget allows to subscribe to remote Streams by clicking on the stream
    hide_myself: bool, does not show the datastream
    Args:
        Datastream: datastream object
        Hide_myself: bool, hides the own datastream object [default=False]
        show_statistic: Showing some statistics
        update_subscribed_streams: update the subscribed streams, useful in combination with show_statistics = True
        stream_type: Types of streams to show (subscription is still only to pubstreams)
        multiple_subscription: Allows to subscribe a stream more than once [default True]
    """
    def __init__(self,Datastream,hide_myself = False, show_statistics = False, update_subscribed_streams = False, stream_type = None, multiple_subscription=True, statistic=True):
        QtWidgets.QWidget.__init__(self)
        funcname = self.__class__.__name__ + '.__init__()'
        logger.debug(funcname)
        self.Datastream = Datastream
        self.layout = QtWidgets.QGridLayout(self)
        self.show_statistics = show_statistics
        self._statistic = statistic
        self.update_subscribed_streams = update_subscribed_streams
        self.multiple_subscription = multiple_subscription
        if( not(isinstance(stream_type,list))) :
            stream_type = [stream_type,]

        self.stream_type = stream_type
        # Address list
        #self.address_list = pymqdatastream.standard_datastream_control_addresses
        self.address_list = [ pymqdatastream.standard_datastream_control_address ]

        # Check if the address of the local datastream is in the list, if yes, remove it
        if(hide_myself):
            for i,addr in enumerate(self.address_list):
                if(addr == self.Datastream.address):
                    self.address_list.pop(i)
                    break

        # Tree
        self.treeWidget = QtWidgets.QTreeWidget()
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.itemClicked.connect(self.handleItemChanged)
        # Subscribed Tree
        self.treeWidgetsub = QtWidgets.QTreeWidget()
        self.treeWidgetsub.setHeaderHidden(True)
        self.treeWidgetsub.itemClicked.connect(self.handleItemChangedsub)
        #
        self.info_stream = QtWidgets.QPlainTextEdit()
        self.info_stream.setReadOnly(True)
        self.info_streamsub = QtWidgets.QPlainTextEdit()
        self.info_streamsub.setReadOnly(True)        
        # Buttons
        self.button_settings   = QtWidgets.QPushButton('Settings', self)  
        self.button_addresses   = QtWidgets.QPushButton('Addresses', self)
        self.button_update     = QtWidgets.QPushButton('Update', self)
        self.button_subscribe  = QtWidgets.QPushButton('Subscribe', self)
        self.button_unsubscribe= QtWidgets.QPushButton('Unsubscribe', self)
        self.button_close      = QtWidgets.QPushButton('Close', self)          
        self.button_subscribe.setEnabled(False)
        self.button_unsubscribe.setEnabled(False)

        self.button_layout0 = QtWidgets.QHBoxLayout()
        self.button_layout0.addWidget(self.button_update)
        self.button_layout0.addWidget(self.button_addresses)
        self.button_layout0.addWidget(self.button_settings)
        self.button_layout0.addWidget(self.button_close)                

        self.button_addresses.clicked.connect(self.open_address_widget)
        self.button_update.clicked.connect(self.handle_update_clicked)
        self.button_settings.clicked.connect(self.handle_settings_clicked)        
        self.button_subscribe.clicked.connect(self.handle_subscribe_clicked)
        self.button_unsubscribe.clicked.connect(self.handle_unsubscribe_clicked)
        self.button_close.clicked.connect(self.handle_close_clicked)
        # labels
        self._label_datastreams = QtWidgets.QLabel('Datastreams')
        # layout
        self.layout.addLayout(self.button_layout0,0,0,1,2)        
        self.layout.addWidget(self.treeWidget,1,0)
        self.layout.addWidget(self.treeWidgetsub,1,1)
        self.layout.addWidget(self.info_stream,2,0)
        self.layout.addWidget(self.info_streamsub,2,1)
        self.layout.addWidget(self.button_subscribe,3,0)
        self.layout.addWidget(self.button_unsubscribe,3,1)
        #self.layout.addWidget(self.button_close,4,1)        


        self.unsubscribe_item = None

        # Fill the list with datastream objects
        #remote_datastreams = self.query_datastreams(self.address_list[0:2])
        remote_datastreams = self.query_datastreams(self.address_list)
        self.populate_with_datastreams(remote_datastreams)

        # Define some signals, these list can be filled with functions which
        # TODO: This could be updated/improved by using Signals/Blinker
        self.signal_newstream = []
        self.signal_remstream = []                

        # update the figure once in a while
        if(self.update_subscribed_streams):
            logger.debug(funcname + ": Starting update timer")       
            timer = QtCore.QTimer(self)
            timer.timeout.connect(self.update_subscribed_stream_statistics)
            timer.start(100)


    def open_address_widget(self):
        """
        """
        # Address widget
        self.addresses = DataStreamAddresslist(self.address_list)
        self.addresses.show()


    def query_datastreams(self,addresses):
        """
        Queries a list of addresses and returns datastream objects
        """
        funcname = self.__class__.__name__ + '.query_datastreams()'
        list_status = []
        datastreams_remote = []
        addresses = pymqdatastream.treat_address(addresses)
        for address in addresses:
            logger.debug(funcname + ': Address:' + address)
            [ret,reply_dict] = self.Datastream.get_datastream_info(address,dt_wait=0.01)
            #logger.debug(funcname + ': Reply_dict:' + str(reply_dict))
            if(ret):
                datastream_remote = pymqdatastream.create_datastream_from_info_dict(reply_dict)
                try:
                    list_status.append(reply_dict)
                    datastreams_remote.append(datastream_remote)
                    #logger.debug(funcname + ": Reply:" + str(datastream_remote))
                except Exception as e :
                    logger.debug(funcname + ": Exception:" + str(e))       
                    logger.debug(funcname + ": Could not decode reply:" + str(reply_dict))


        return datastreams_remote


    def populate_with_datastreams(self,datastream_list, data_type = None, variables = None):
        """
        
        Args:
            datastream_list:
            stream_type:
            data_type:
            variables:

        """

        # Check if the datastream has the asked stream types and remove
        # streams not fitting from list
            
        # Dont remove any stream
        if(self.stream_type[0] == None):
            pass
        else:
            datastream_list_filter = []
            for dstream in datastream_list:
                break_loop = False
                for stype in self.stream_type:
                    for i,stream in enumerate(dstream.Streams):
                        if(stream.stream_type == stype):
                            break_loop = True
                            datastream_list_filter.append(dstream)
                            break

                    if(break_loop):
                        break

                                
            datastream_list = datastream_list_filter

        # Finally populate the list
        self.treeWidget.clear()
        for dstream in datastream_list:
            datastream_name = dstream.get_name_str(strtype = 'simple_newline')
            status_tree = addParent(self.treeWidget.invisibleRootItem(), 0, datastream_name, 'data Clients')
            for i,stream in enumerate(dstream.Streams):
                for stype in self.stream_type:
                    if((stream.stream_type == stype) | (stype == None)):
                        name = str(i) + ' ' + stream.name
                        stream_item = addChild(status_tree, 0, name, 'data Clients')
                        stream_item.stream = stream


    def populate_subscribed_with_streams(self):
        #self.treeWidgetsub.clear()
        root = self.treeWidgetsub.invisibleRootItem()        
        for i,stream in enumerate(self.Datastream.Streams):
            # Loop over existing items and check if the stream
            # has already an item
            child_count = root.childCount()
            column = 0
            has_item = False
            for j in range(child_count):
                item = root.child(j)
                if(item.stream == stream):
                    has_item = True

            if(has_item):
                continue
            
            if(stream.stream_type == 'substream'):
                name = str(i) + ' ' + stream.name
                if(self.show_statistics):
                    stream_item = addParent(self.treeWidgetsub, 0, name, 'data Clients')
                    stream_item.setExpanded(True)
                    num_recv = stream.socket.statistic['packets_received']
                    stat_name = str(num_recv) + ' received'
                    stat_item = addChild(stream_item, 0, stat_name, 'data Clients')
                else:
                    stream_item = addChild(self.treeWidgetsub, 0, name, 'data Clients')

                stream_item.stream = stream

                
    def update_subscribed_stream_statistics(self):
        root = self.treeWidgetsub.invisibleRootItem()
        child_count = root.childCount()
        for i in range(child_count):
            item = root.child(i)
            stream = item.stream
            num_recv = stream.socket.statistic['packets_received']
            stat_name = str(num_recv) + ' received'            
            stat_item = item.child(0)
            stat_item.setText(0, stat_name)

            
    def handleItemChanged(self, item, column):
        """

        Handle if an item was changed. If a stream item was clicked show
        information about the stream

        """
        funcname = self.__class__.__name__ + '.handleItemChanged()'        
        try:
            uuid = item.stream.uuid
            info_txt = str(item.stream)
            info_txt = info_txt.replace(';','\n')
            self.info_stream.clear()
            self.info_stream.insertPlainText(info_txt)
            if(item.stream.stream_type == 'pubstream'):
                # Check if the stream was already subscribed
                if( self.multiple_subscription == False ):
                    print('JA1')
                    for stream in self.Datastream.Streams:
                        print('JA2')                        
                        if(stream.uuid == item.stream.uuid):
                            print('JA3')
                            #self.button_subscribe.setEnabled(False)
                            logger.debug(funcname + ': Stream has already been subscribed to')
                            self.button_subscribe.setEnabled(False)
                            return

                self.button_subscribe.setEnabled(True)
                self._subscribe_item = item
            else:
                self.button_subscribe.setEnabled(False)
                self._subscribe_item = None
        except Exception as e:
            self.button_subscribe.setEnabled(False)
            self._subscribe_item = None


    def handleItemChangedsub(self, item, column):
        """

        Handle if an item of the subscribed streams was clicked. Show
        information about the stream

        """

        try:
            item.stream
        except:
            return
        if(item != None):
            info_txt = str(item.stream)
            info_txt = info_txt.replace(';','\n')
            self.info_streamsub.clear()
            self.info_streamsub.insertPlainText(info_txt)
            self.unsubscribe_item = item
            self.button_unsubscribe.setEnabled(True)

    def handle_settings_clicked(self):
        '''
        
        Subscribe settings
    
        '''
        funcname = self.__class__.__name__ + '.handle_settings_clicked()'
        self._settings_widget = QtWidgets.QWidget()
        self._settings_widget.show()
        
            
    def handle_subscribe_clicked(self):
        '''
        
        Subscribes the stream in self._subscribe_item.stream

        '''
        funcname = self.__class__.__name__ + '.handle_subscribe_clicked()'
            
        substream = self.Datastream.subscribe_stream(self._subscribe_item.stream,statistic=self._statistic)
        if(substream != None):
            logger.debug(funcname + ': Could connect to socket')
            self.populate_subscribed_with_streams()
            # Call the function in signal_list with the new stream as argument
            for func in self.signal_newstream:
                print('Hallo!!!')
                func(substream)        

        if( self.multiple_subscription == False ):
            self.button_subscribe.setEnabled(False)
            
        self.populate_subscribed_with_streams()

        
    def handle_unsubscribe_clicked(self):
        funcname = self.__class__.__name__ + '.handle_unsubscribe_clicked()'
        logger.debug(funcname + ':' + str(self.unsubscribe_item.stream))
        self.Datastream.rem_stream(self.unsubscribe_item.stream)
        # Call the function in signal_list with the to be removed stream as argument
        for func in self.signal_remstream:
            func(self.unsubscribe_item.stream)

        root = self.treeWidgetsub.invisibleRootItem()
        root.removeChild(self.unsubscribe_item)            
        self.unsubscribe_item = None
        self.info_streamsub.clear()
        button_enable = False
        self.button_unsubscribe.setEnabled(button_enable)
        #self.populate_subscribed_with_streams()

        
    def handle_update_clicked(self):
        self.treeWidget.clear()
        # Try to get a new address list from Addresslistwidget
        try:
            self.address_list = self.addresses.get_addresses()
            print('Got data:',self.address_list)
        except Exception as e:
            print(str(e) + ' no addresslistwidget')
        # Fill the list with datastream objects
        remote_datastreams = self.query_datastreams(self.address_list)
        self.populate_with_datastreams(remote_datastreams)

    def handle_close_clicked(self):
        self.close()



class DataStreamShowTextDataWidget(QtWidgets.QWidget):
    """
    
    This widget displays the data of a subscribed stream in a text widget

    """
    def __init__(self,stream,blockcount = 20000,oformat = 'csv'):
        QtWidgets.QWidget.__init__(self)
        self.blockcount = blockcount
        
        # Processing function
        if(oformat == 'raw'): 
            self.data2str = self.data2str_raw
        elif(oformat == 'csv'): 
            self.data2str = self.data2str_csv

        # Widgets
        self.stream_data = QtWidgets.QPlainTextEdit()
        self.stream_data.setMaximumBlockCount(self.blockcount)
        self.stream_data.setReadOnly(True)

        self.button_con = QtWidgets.QPushButton('Disconnect', self)
        self.button_con.clicked.connect(self.disconnect_stream)
        self.button_clr = QtWidgets.QPushButton('Clear', self)
        self.button_clr.clicked.connect(self.clear_data)        

        label_str = stream.name + '\n' + stream.socket.address
        self.stream_label = QtWidgets.QLabel(label_str)

        # Layout
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.addWidget(self.stream_label,0,0,1,2)
        self.layout.addWidget(self.stream_data,1,0,1,2)
        self.layout.addWidget(self.button_con,2,0)
        self.layout.addWidget(self.button_clr,2,1)        
        
        # The stream 
        self.stream = stream
        # timer to read the data of the stream
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.read_data)
        self.timer.start(25)

        self.stream_data.clear()

        
    def disconnect_stream(self):
        print('Disconnect ...')        
        self.stream.disconnect_substream()
        self.button_con.setText('Connect')
        self.button_con.clicked.disconnect()
        self.button_con.clicked.connect(self.connect_stream)
        self.timer.stop()

    def connect_stream(self):
        print('Connect ...')
        self.stream.reconnect_substream()
        self.button_con.setText('Disconnect')
        self.button_con.clicked.connect(self.disconnect_stream)
        self.timer.start(25)


    def clear_data(self):
        self.stream_data.clear()
        
    def read_data(self):
        # Load data and plot
        while(len(self.stream.deque) > 0):
            data = self.stream.deque.pop()
            # Convert the data to a str
            data_str = self.data2str(data)
            self.stream_data.appendPlainText(data_str)
            #print(self.data2str_raw(data))


        self.stream_data.verticalScrollBar().setValue(
            self.stream_data.verticalScrollBar().maximum())

    def data2str_raw(self,data):
        return str(data)

    def data2str_csv(self,data):
        tstr = str(data[1]['time'])
        dstr = ''
        for i,d in enumerate(data[1]['data']):
            dstr += tstr
            dstr += ';'
            for j,dat in enumerate(d):
                dstr += str(dat)
                dstr += ';'

            dstr += '\n'
        #dstr += '\n'
        
        return dstr[:-1]






class DataStreamShowTableDataWidget(QtWidgets.QWidget):
    """
    
    This widget displays the data of a subscribed stream in a table widget

    """
    def __init__(self,stream, blockcount = 20000):
        QtWidgets.QWidget.__init__(self)
        self.blockcount = blockcount
        
        # Widgets
        self.stream_data = QtWidgets.QPlainTextEdit()
        self.stream_data.setMaximumBlockCount(self.blockcount)
        self.stream_data.setReadOnly(True)

        
        # The table widget
        header = ['n', 'sent time', 'recv time']
        self.stream_table = QtWidgets.QTableWidget()
        self.stream_table.setColumnCount(len(stream.variables) + 3)
        for i,var in enumerate(stream.variables):
            header.append('var ' + str(i) + '\n' + var['name'] + '\n[' + var['unit'] + ']')
            
        self.stream_table.setHorizontalHeaderLabels(header)
        self.stream_table.horizontalHeader().setStretchLastSection(True)

        
        self.button_con = QtWidgets.QPushButton('Disconnect', self)
        self.button_con.clicked.connect(self.disconnect_stream)
        self.button_clr = QtWidgets.QPushButton('Clear', self)
        self.button_clr.clicked.connect(self.clear_data)        

        label_str = stream.name + '\n' + stream.socket.address
        self.stream_label = QtWidgets.QLabel(label_str)
        
        
        # Layout
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.addWidget(self.stream_label,0,0,1,2)
        #self.layout.addWidget(self.stream_data,1,0,1,1)
        self.layout.addWidget(self.stream_table,1,0,1,2)        
        self.layout.addWidget(self.button_con,2,0)
        self.layout.addWidget(self.button_clr,2,1)        

        
        # The stream 
        self.stream = stream
        # timer to read the data of the stream
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.read_data)
        self.timer.start(25)
        self.stream_data.clear()

        
    def disconnect_stream(self):
        print('Disconnect ...')        
        self.stream.disconnect_substream()
        self.button_con.setText('Connect')
        self.button_con.clicked.disconnect()
        self.button_con.clicked.connect(self.connect_stream)
        self.timer.stop()

        
    def connect_stream(self):
        print('Connect ...')
        self.stream.reconnect_substream()
        self.button_con.setText('Disconnect')
        self.button_con.clicked.connect(self.disconnect_stream)
        self.timer.start(25)


    def clear_data(self):
        self.stream_table.clearContents()
        self.stream_table.setRowCount(0)            

        
    def read_data(self):
        # Load data and plot
        while(len(self.stream.deque) > 0):
            data = self.stream.deque.pop()
            sendtime = data['info']['ts']
            recvtime = data['info']['tr']
            sendtime_str = str(sendtime)
            recvtime_str = str(recvtime)
            n = data['info']['n']            

            for i,d in enumerate(data['data']):
                rowPosition = self.stream_table.rowCount()
                self.stream_table.insertRow(rowPosition)
                # Time
                self.stream_table.setItem(rowPosition,
                                0, QtWidgets.QTableWidgetItem( str(n) ))
                self.stream_table.setItem(rowPosition,
                                1, QtWidgets.QTableWidgetItem( sendtime_str ))
                self.stream_table.setItem(rowPosition,
                                2, QtWidgets.QTableWidgetItem( recvtime_str ))
                for j,dat in enumerate(d):
                    self.stream_table.setItem(rowPosition,
                                3+j, QtWidgets.QTableWidgetItem( str(dat) ))


        #self.stream_data.verticalScrollBar().setValue(self.stream_data.verticalScrollBar().maximum())

        
        
