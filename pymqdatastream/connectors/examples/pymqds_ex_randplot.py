#!/usr/bin/env python3
import time
import numpy as np
import logging
import os,sys
import argparse
import pymqdatastream
#import pymqdatastream.connectors.test.pymqds_rand.RandDataStream as RandDataStream
import pymqdatastream.connectors.test.pymqds_rand as pymqds_rand
import multiprocessing
from PyQt5 import QtCore, QtGui, QtWidgets
import pymqdatastream.connectors.pyqtgraph.pymqds_plotxy as pymqds_plotxy
from pymqdatastream.connectors.pyqtgraph import pyqtgraphDataStream

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqdatastream_rand')
logger.setLevel(logging.INFO)
# TODO: http://stackoverflow.com/questions/367586/generating-random-text-strings-of-a-given-pattern
famstr = 'pymqds_ex_randplot'


def start_pymqds_plotxy(addresses):
    """
    
    Start a pymqds_plotxy session
    
    """

    print('AFDFS')
    print(addresses)
    logging_level = logging.DEBUG
    #datastream = pymqdatastream.DataStream(name = 'plotxy', logging_level=logging_level)
    datastream = pyqtgraphDataStream(name = 'plotxy', logging_level=logging_level)
    datastream2 = pyqtgraphDataStream(name = 'plotxy', logging_level=logging_level)    
    for addr in addresses:
        stream = datastream.subscribe_stream(addr)
        datastream.init_stream_settings(stream,plot_data = True)
        stream = datastream2.subscribe_stream(addr)
        datastream2.init_stream_settings(stream,plot_data = True)        

        

    datastream.plot_datastream(True)
    datastream.set_plotting_mode(mode='cont')
    
    datastream2.plot_datastream(True)
    datastream2.set_plotting_mode(mode='xr',xl=10)
    
    app = QtWidgets.QApplication([])
    plotxywindow = pymqds_plotxy.pyqtgraphMainWindow(datastream=datastream)
    plotxywindow.add_graph(datastream=datastream2)
    plotxywindow.show()
    sys.exit(app.exec_())    
    print('FSFDS')    




if __name__ == '__main__':
    # For different loggers see also:
    # http://stackoverflow.com/questions/8837615/different-levels-of-logging-in-python
    address_datastream_help = 'Create a pymqdatastream Datastream to publish the data over a network, no argument take standard address, otherwise specify zeromq compatible address e.g. tcp://192.168.178.10'            
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--address', '-a', nargs = '?', default = False, help=address_datastream_help)        
    args = parser.parse_args()
    if(args.verbose == None):
        logger.info('logging level: CRITICAL')
        logging_level = logging.CRITICAL
    elif(args.verbose == 1):
        logger.info('logging level: INFO ')        
        logging_level = logging.INFO
    elif(args.verbose >= 2):
        logger.info('logging level: DEBUG ')
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO


    logger.setLevel(logging_level)
    pymqdatastream.logger.setLevel(logging_level)

    address = None    
    print('Args address:',args.address)
    # Create datastream? 
    if(args.address != False):
        if(args.address == None):        
            logger.debug('Creating a pymqdatastream at standard address')
        else:
            logger.debug('Creating a pymqdatastream at address: ' + str(args.publish_datastream))
            address = args.address

    RDS = pymqds_rand.RandDataStream(address = address, name = 'random',logging_level = logging_level)
    RDS.add_random_stream()

    streams = []
    stream_addrs = []
    for i in range(2):
        stream = RDS.add_random_stream(dt = 0.1,num_elements = 10)
        streams.append(stream)
        stream_addrs.append(RDS.get_stream_address(stream))


    # Multiprocessing test
    multiprocessing.set_start_method('spawn',force=True)        
    plotxyprocess = multiprocessing.Process(target =start_pymqds_plotxy, args = (stream_addrs,))
    plotxyprocess.start()        


    while(True):
        time.sleep(1)
        print('harr')
