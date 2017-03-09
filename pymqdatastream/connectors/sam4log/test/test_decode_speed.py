import pymqdatastream.connectors.sam4log.pymqds_sam4log as pymqds_sam4log
import pymqdatastream.connectors.sam4log.data_packages as data_packages
import time

def test_speed():
    filename = '../data/data_test_format4.bin'
    data_file = open(filename,'rb')
    [VALID_HEADER,header_data] = pymqds_sam4log.find_sam4log_header(data_file)
    header_data = header_data.decode('utf-8')
    device_info = pymqds_sam4log.parse_device_info(header_data)                
    #print('Reading data',VALID_HEADER)
    data = data_file.read(10000)
    data2 = data[:]
    for i in range(100):
        data2 += data
    #print(data)
    # Decode the data
    t0 = time.time()
    [data_stream,data_packets,data_str] = data_packages.decode_format4(data2,device_info)
    t1 = time.time()
    dt = t1 - t0
    speed = dt/len(data_packets)
    print('Num packets',len(data_packets),'time needed',dt,'s per packet',speed)



if __name__ == '__main__':
    print('Hallo!')
    #t = timeit.timeit("test_speed()",setup="from __main__ import test_speed",number=10)
    #print(t)
    test_speed()
