#!/usr/bin/env python
import sys
import os
import pymqdatastream
import logging
import argparse

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pydatastream_scan')
logger.setLevel(logging.INFO)

def query_datastreams(addresses,verbosity):
    """
    Queries a list of addresses and returns datastream objects
    """
    funcname = 'query_datastreams()'
    list_status = []
    datastreams_remote = []
    print('\n\n\n')
    Datastream = pymqdatastream.DataStream(name='scan')
    for address in addresses:
        logger.debug(funcname + ': Address:' + address)
        [ret,reply_dict] = Datastream.get_datastream_info(address,dt_wait=0.01)
        #logger.debug(funcname + ': Reply_dict:' + str(reply_dict))
        if(address == Datastream.address):
            if(verbosity > 1):
                print('This is myself')
        elif(ret):
            if(verbosity > 0):
                print('Found datastream at: ' + address)
                
            datastream_remote = pymqdatastream.create_datastream_from_info_dict(reply_dict)
            try:
                list_status.append(reply_dict)
                datastreams_remote.append(datastream_remote)
                #logger.debug(funcname + ": Reply:" + str(datastream_remote))
            except Exception as e :
                logger.debug(funcname + ": Exception:" + str(e))       
                logger.debug(funcname + ": Could not decode reply:" + str(reply_dict))
        else:
            if(verbosity > 0):
                print('No datastream at: ' + address)                


    return datastreams_remote


def query(address):
    """
    Queries the datastreams at given address

    Args:
        address
    """



    #Datastream = pymqdatastream.DataStream(name='scan')            
    #datastream = 


if __name__ == '__main__':
    datastream_help  = 'Query datastream with address e.g. -d tcp://192.168.178.97:18055'
    information_help = 'Print full information of each found datastream'
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--full_information', '-f', action='store_false', help = information_help)
    parser.add_argument('--datastream', '-d', nargs = '?', default = [], action='append', help=datastream_help)


    args = parser.parse_args()
    logging_level = logging.INFO
    if(args.verbose == None):
        logging_level = logging.CRITICAL        
    elif(args.verbose == 1):
        logging_level = logging.INFO
    elif(args.verbose >= 2):
        print('Debug logging level')
        logging_level = logging.DEBUG

    pymqdatastream.logger.setLevel(logging_level)        

    address = None    
    print('Args datastream:',args.datastream)
    if(len(args.datastream) != 0):
        address = []
        for addr in args.datastream:
            if(addr == None):
                address.append(None)
            else:
                print('Scanning for pymqdatastreams at address: ' + str(addr))
                #address = args.datastream
                address.append(addr)


    Datastream = pymqdatastream.DataStream(name='scan',logging_level = logging_level)
    #datastreams_remote = Datastream.query_datastreams(address)
    datastreams_remote = Datastream.query_datastreams_fast(address)
    # Print datastreams
    if(len(datastreams_remote)>0):
        print('Datastreams:')
        for i,rdatastream in enumerate(datastreams_remote):
            if(args.full_information):
                print(rdatastream.get_info_str('short'))
            else:
                print(rdatastream.get_info_str('standard'))
