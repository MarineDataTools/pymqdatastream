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

    # Create a sending and a receiving datastream
    sendDS = pymqdatastream.DataStream(name = 'test_send', logging_level='DEBUG')
    recvDS = pymqdatastream.DataStream(name = 'test_reicv', logging_level='DEBUG')

    # Adding publisher sockets to the sending datastream and add variables
    sendDS.add_pub_socket()
    timevar = pymqdatastream.StreamVariable(name = 'unix time',unit = 'seconds',datatype = 'float')
    datavar = pymqdatastream.StreamVariable(name = 'random',datatype = 'float', unit = 'something')
    variables = [timevar,datavar]
    name = 'some_data'
    sendDS.add_pub_stream(socket = sendDS.sockets[-1],name=name,variables=variables)
    sendstream = sendDS.Streams[-1]
    num_elements = 3

    # Subscribe the stream
    recvstream = recvDS.subscribe_stream(sendstream)

    while True:
        time.sleep(1)
        print('Sending data')
        data_all = []        
        for n in range(num_elements):
            ti = time.time()
            rand_data = np.random.rand(1)[0]
            data = [ti, rand_data]
            data_all.append(data)

        # Sending the data
        sendstream.pub_data(data_all)

        time.sleep(1)
        print('Looking for data')
        ndata = len(recvstream.deque)
        print('Received ' + str(ndata) + ' packets:')
        for i in range(ndata):
            data_recv = recvstream.pop_data()
            print('Packet ' + str(i) + ' :' )
            print(data_recv)
            


