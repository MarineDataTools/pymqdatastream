#!/usr/bin/env python3
import time
import logging
import os,sys
import argparse
import pymqdatastream
import pymqdatastream.connectors.math_operator.pymqdatastream_math_operator as pymqdatastream_math_operator
import pymqdatastream.connectors.test.pymqdatastream_rand as pymqdatastream_rand

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('pymqdatastream_test')
logger.setLevel(logging.INFO)

if __name__ == '__main__':
    # For different loggers see also:
    # http://stackoverflow.com/questions/8837615/different-levels-of-logging-in-python
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()
    if(args.verbose == None):
        logger.setLevel(logging.CRITICAL)
        pymqdatastream.logger.setLevel(logging.CRITICAL)
    elif(args.verbose == 1):
        logger.setLevel(logging.INFO)
        pymqdatastream.logger.setLevel(logging.INFO)
    elif(args.verbose == 2):
        logger.setLevel(logging.DEBUG)
        pymqdatastream.logger.setLevel(logging.DEBUG)        

    RDS = pymqds_rand.RandDataStream(name = 'random_test')
    RDS.add_random_stream(dt = 0.1,num_elements = 5)

    if(False):
        for i in range(1):
            RDS.add_random_stream(dt = 0.04,num_elements = 40)

        for i in range(1):
            RDS.add_sine_stream(dt = 0.02, f = 2, num_elements = 20)

        for i in range(1):
            RDS.add_random_str_stream(dt = 0.5, num_elements = 5)


    # Add a math_operator
    MDS = pymqdatastream_math_operator.MathOpDataStream(name = 'random_std', logging_level = 'DEBUG')
    #MDS.subscribe_stream(RDS.Streams[2])
    MDS.running_mean_std(RDS.Streams[1],n_avg = 100)
    
    while True:
        time.sleep(1)
        print('Schnarch')

