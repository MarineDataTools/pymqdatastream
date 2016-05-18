#!/usr/bin/env python3
import time
import numpy as np
import json
import logging
import threading
import os,sys
import argparse
import pymqdatastream
import random
import string


if __name__ == '__main__':


    sendDS = pymqdatastream.DataStream(name = 'test_send', logging_level='DEBUG')
    recvDS = pymqdatastream.DataStream(name = 'test_reicv', logging_level='DEBUG')

    sendDS.add_pub_socket()
    timevar = pymqdatastream.StreamVariable(name = 'unix time',unit = 'seconds',datatype = 'float')
    datavar = pymqdatastream.StreamVariable(name = 'data',datatype = 'float')
    variables = [timevar,datavar]
    name = 'some_data'
    sendDS.add_pub_stream(socket = sendDS.sockets[-1],name=name,variables=variables)
    sendstream = sendDS.Streams[-1]
    num_elements = 3

    npack = 0

    recvstream = recvDS.subscribe_stream(sendstream)

    while True:
        time.sleep(1)
        print('Sending data')
        data_all = []        
        for n in range(num_elements):
            ti = time.time()
            chars = "".join( [random.choice(string.letters) for i in xrange(60)] )
            data = [ti, chars]
            data_all.append(data)

        # TODO: this should be done by the datastream object itself
        sendstream.pub_data(data_all)
        #npack +=1
        #ti = time.time()
        #data_dict = {'n':npack,'time':ti,'data':data_all}
        #data_json = json.dumps(data_dict).encode('utf-8')
        #sendstream.deque.appendleft(data_json)
        #sendstream.push_substream_data()

        time.sleep(1)
        print('Looking for data')
        ndata = len(recvstream.deque)
        print(ndata)
        for i in range(ndata):
            data_recv = recvstream.pop_data()
            print('Received:')
            print('Received:')
            print('Received:')            
            print(data_recv)
            


