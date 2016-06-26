#!/usr/bin/env python3
import time
import numpy as np
import pymqdatastream



def reply_function(request):
    #reply = b'Hallo, this is a reply to the request' + str(request)
    reply = 'Hallo, this is a reply to the request: ' + request
    return reply


if __name__ == '__main__':

    # Create a sending and a receiving datastream
    sendDS = pymqdatastream.DataStream(name = 'test_send', \
                                       logging_level='DEBUG')
    recvDS = pymqdatastream.DataStream(name = 'test_reicv', \
                                       logging_level='DEBUG')
    
    # Create a reply stream
    stream = recvDS.create_rep_stream(socket_reply_function = reply_function)
    
    print(stream)
    
    reqstream = sendDS.subscribe_stream(stream)
    reply = reqstream.reqrep('Hallo')
    print('Reply',reply)

            

