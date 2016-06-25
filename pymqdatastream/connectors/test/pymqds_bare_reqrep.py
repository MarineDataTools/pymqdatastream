#!/usr/bin/env python3
import time
import numpy as np
import pymqdatastream



def reply_function(request):
    #reply = b'Hallo, this is a reply to the request' + str(request)
    reply = b'Hallo, this is a reply to the request'
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
    reqstream.socket.send_req(b'Hallo!')
    reply = reqstream.socket.get_rep() # This is with a poller, so it can block depending on dt_wait
    print('Reply',reply)

            

