#!/usr/bin/env python3
import time
import numpy as np
import json
import logging
import threading
import os,sys
import argparse
import random
import string
import pymqdatastream


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqdatastream_math_operator')
logger.setLevel(logging.DEBUG)


class MathOpDataStream(pymqdatastream.DataStream):
    def __init__(self, **kwargs):
        """
        """
        funcname = '.__init__()'
        super(MathOpDataStream, self).__init__(**kwargs)
        uuid = self.uuid
        uuid.replace('DataStream','MathOpDataStream')
        self.uuid = uuid
        self.name = 'math_operator'
        self.thread = []
        self.thread_queues = []

    def sum(self,stream):
        """ Calculates the sum of the stream


        """
        funcname = '.sum()'
        # Check if its a remote stream, if yes, subscribe and connect
        self.logger.debug(funcname)

        # Subscribe to stream if sucessfull continue, otherwise return immidiately
        ret = self.subscribe_stream(stream)

        if(ret == False):
            self.logger.info('Could not connect to stream, doing nothing')
            return
        else:
            self.logger.info('Could connect to stream')
            rawdatastream = self.Streams[-1]
            
        # TODO: Check if the variables have the correct type
        timevar = pymqdatastream.StreamVariable(name = 'unix time',datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'sum data',datatype = 'float')
        variables = [timevar,datavar]
        name = 'sum (' + rawdatastream.name + ')'
        self.create_pub_stream(name=name,variables=variables, statistic = True)
        sumstream = self.Streams[-1]

        self.thread_queues.append(pymqdatastream.queue.Queue)
        print('Starting thread')
        self.thread.append(threading.Thread(target=self.do_sum,args = (rawdatastream,sumstream,self.thread_queues[-1])))
        self.thread[-1].daemon = True
        self.thread[-1].start()

    def do_sum(self,stream,pubstream,queue):
        """
        
        """

        dt = 0.01
        ysum = 0


        
        while(True):
            while(len(stream.deque) > 0):
                stream_data = stream.deque.pop()
                data = stream_data['data']
                x_data = []
                y_data = []
                for n in range(len(data)):
                    ysum += data[n][1]
                    y_data.append(ysum)
                    
                pubstream.pub_data([x_data,y_data])


            time.sleep(dt)        


    def running_mean_std(self,stream, n_avg = 4):
        """
        Calculates the running mean/standard deviation of n points of stream
        """
        funcname = '.running_mean_std()'
        # Check if its a remote stream, if yes, subscribe and connect
        self.logger.debug(funcname)

        # Subscribe to stream if sucessfull continue, otherwise return immidiately
        ret = self.subscribe_stream(stream)

        if(ret == False):
            self.logger.info('Could not connect to stream, doing nothing')
            return
        else:
            self.logger.info('Could connect to stream')
            rawdatastream = self.Streams[-1]
            
        # TODO: Check if the variables have the correct type
        timevar = pymqdatastream.StreamVariable(name = 'unix time',datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'mean data',datatype = 'float')
        variables = [timevar,datavar]
        name = 'rmean (' + rawdatastream.name + ')'
        self.create_pub_stream(name=name,variables=variables, statistic = True)
        meanstream = self.Streams[-1]

        
        timevar = pymqdatastream.StreamVariable(name = 'unix time',datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'std data',datatype = 'float')
        variables = [timevar,datavar]
        name = 'rm_pstd (' + rawdatastream.name + ')'
        self.create_pub_stream(name=name,variables=variables, statistic = True)
        stdstream_plus = self.Streams[-1]

        variables = [timevar,datavar]
        name = 'rm_mstd (' + rawdatastream.name + ')'
        self.create_pub_stream(name=name,variables=variables, statistic = True)
        stdstream_minus = self.Streams[-1]        


        self.thread_queues.append(pymqdatastream.queue.Queue)
        print('Starting thread')
        self.thread.append(threading.Thread(target=self.do_running_mean,args = (rawdatastream,[meanstream,stdstream_plus,stdstream_minus],self.thread_queues[-1],n_avg)))
        self.thread[-1].daemon = True
        self.thread[-1].start()

    def do_running_mean(self,stream,pubstream,queue,n_avg):
        """
        
        """

        dt = 0.01
        y_data = np.zeros(n_avg)
        x_data = np.zeros(n_avg)
        ind_data_std = 0


            
        while(True):
            while(len(stream.deque) > 0):
                stream_data = stream.deque.pop()
                data = stream_data['data']
                for n in range(len(data)):
                    x_data[ind_data_std] = data[n][0]
                    y_data[ind_data_std] = data[n][1]                    
                    ind_data_std += 1
                    if(ind_data_std >= n_avg): # Array full, calc the mean, std
                        dmean = y_data.mean()
                        dstd = y_data.std()                        
                        xmean = x_data.mean()
                        pubstream[0].pub_data([xmean,dmean])
                        pubstream[1].pub_data([xmean,dmean + dstd])
                        pubstream[2].pub_data([xmean,dmean - dstd])                        
                        # Shift the data by one
                        x_data[0:-1] = x_data[1:]                        
                        y_data[0:-1] = y_data[1:]
                        ind_data_std = n_avg - 2

            time.sleep(dt)


    def calc_poly(self,stream, poly):
        """
        Calculates a polynom from the input data
        """
        funcname = '.calc_poly()'
        # Check if its a remote stream, if yes, subscribe and connect
        self.logger.debug(funcname)
        # Subscribe to stream if sucessfull continue,
        # otherwise return immidiately
        if(isinstance(stream,pymqdatastream.Stream)):
            ret = self.subscribe_stream(stream)
        elif(isinstance(stream,str)):
            ret = self.subscribe_stream(address = stream)
        else:
            self.logger.info('Stream is not of type datastream.stream ' \
                             + ' neither a str address')
            return                        

        if(ret == False):
            self.logger.info('Could not connect to stream, doing nothing')
            return
        else:
            self.logger.info('Could connect to stream')
            rawdatastream = self.Streams[-1]
            
        # TODO: Check if the variables have the correct type
        timevar = pymqdatastream.StreamVariable(name = 'unix time',\
                                            datatype = 'float')
        datavar = pymqdatastream.StreamVariable(name = 'poly data',\
                                            datatype = 'float')
        variables = [timevar,datavar]
        name = 'poly (' + rawdatastream.name + ')'
        self.create_pub_stream(name=name,variables=variables, statistic = True)
        polystream = self.Streams[-1]

        self.thread_queues.append(pymqdatastream.queue.Queue)
        self.thread.append(threading.Thread(target=self.do_poly,\
                                            args = (rawdatastream,\
                                                    polystream,\
                                                    self.thread_queues[-1],\
                                                    poly)))
        self.thread[-1].daemon = True
        self.thread[-1].start()



    def do_poly(self,stream,polystream,queue,poly):
        """
        
        """

        dt = 0.01
        
        while(True):
            while(len(stream.deque) > 0):
                stream_data = stream.deque.pop()
                data = stream_data[1]['data']
                data_poly = []
                for n in range(len(data)):
                    x_data = data[n][0]
                    y_data = data[n][1]
                    y_data = poly[0] + y_data * poly[1] + y_data * poly[2]**2
                    data_poly.append([x_data,y_data])
                    
                polystream.pub_data(data_poly)                    

            time.sleep(dt)        



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--running_mean', '-rmean')
    parser.add_argument('--polynom', '-poly')    
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()
    
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG       

    # Create a math operator datastream
    print(loglevel)
    MDS = MathOpDataStream(logging_level = loglevel)
    if(args.running_mean == None):
        print('No running mean')
    else:
        address = args.running_mean        
        MDS.running_mean_std(address)


    if(args.polynom == None):
        print('No polynom')
    else:
        address = args.polynom
        poly = [0.0,1/(56.0e-6*2000),0.0]
        MDS.calc_poly(address,poly)




    logger.setLevel(loglevel)
    pymqdatastream.logger.setLevel(loglevel)        


    while True:
        print('Sleeping')
        print(MDS.get_info_str('short'))
        time.sleep(10)        
