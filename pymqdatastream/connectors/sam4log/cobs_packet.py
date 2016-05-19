"""

The sam4log sends binary packages using the the consistent overhead
byte stuffing (`COBS
<https://en.wikipedia.org/wiki/Consistent_Overhead_Byte_Stuffing>`_)
algorithm.


Binary packet types
___________________

Packet types
++++++++++++
LTC2442 packet

==== ====
Byte Data
==== ====
0    0x01 (Packet type)
1    counter lsb
2    counter 
3    counter 
4    counter 
5    counter 
6    counter msb
7    clock 50 khz lsb
8    clock 50 khz 
9    clock 50 khz 
10   clock 50 khz 
11   clock 50 khz
12   clock 50 khz msb
13   LTC2442 addresses
14   LTC2442 0 lsb
15   LTC2442 0 
16   LTC2442 0 msb

==== ====


"""

from numpy import *
import cobs

def random_data():
    rand_number = np.random.bytes(4)
    return rand_number
