#!/usr/bin/env python
import sys
import os
import pymqdatastream
import logging

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


if __name__ == '__main__':
    addresses = pymqdatastream.standard_datastream_control_addresses
    datastreams_remote = query_datastreams(addresses,verbosity=200)

    if(len(datastreams_remote)>0):
        print('Datastreams:')
        for i,rdatastream in enumerate(datastreams_remote):
            print(rdatastream.get_info_str('short'))
