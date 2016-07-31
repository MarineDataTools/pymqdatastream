"""

The sam4log sends binary packages using the the consistent overhead
byte stuffing (`COBS
<https://en.wikipedia.org/wiki/Consistent_Overhead_Byte_Stuffing>`_)
algorithm.


"""

from numpy import *
import cobs

def random_data():
    rand_number = np.random.bytes(4)
    return rand_number
