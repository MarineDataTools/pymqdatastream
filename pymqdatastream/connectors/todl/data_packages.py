from cobs import cobs
import numpy as np
import logging
import pymqdatastream.connectors.todl.ltc2442 as ltc2442

logger = logging.getLogger('todl_data_packages')
logger.setLevel(logging.DEBUG)

def decode_format31(data_str,device_info):
    """
    Converts raw data of the format 31
    """
    pass


def decode_format4(data_str,device_info):
    """

    Converts raw data of the format 4, which is popped from the deque
    given as argument 
    The data is sends in binary packages using the the consistent overhead
    byte stuffing (`COBS
    <https://en.wikipedia.org/wiki/Consistent_Overhead_Byte_Stuffing>`_)
    algorithm.
    After decoding cobs the binary data has the following content

    ==== ====
    Byte Usage
    ==== ====
    0    0xAE (Packet type)
    1    FLAG LTC (see comment)
    2    LTC COMMAND 0 (as send to the AD Converter)
    3    LTC COMMAND 1
    4    LTC COMMAND 2
    5    packet counter msb
    ...   
    9    packet counter lsb
    10   clock 10 khz msb
    ...    
    14   clock 10 khz lsb
    15   LTC2442 0 msb
    16   LTC2442 1 
    17   LTC2442 2 lsb 
    .    3 bytes per activated LTC2442

    ==== ====

    Maximum packet size: 17 + 8 * 3 = 41 Byte

    FLAG LTC: Every bit is dedicted to one of the eight physically
    available LTC2442 and is set to one if activated

    Args:
        deque:
        stream:
        dt: Time interval for polling [s]
    Returns:
        []: List of data

    """
    funcname = 'decode_format4'
    data_packets = []
    ind_ltcs = [0,0,0,0,0,0,0,0]
    nstreams = (max(device_info['channel_seq']) + 1)
    data_stream = [[] for _ in range(nstreams) ]    
    data_split = data_str.split(b'\x00')
    if(len(data_split) > 1):
        #print('data_str',data_str)
        #print('data_split',data_split)        
        if(len(data_split[-1]) == 0): # The last byte was a 0x00
           data_str = b''
        else:
           data_str = data_split[-1]
           data_split.pop() # remove last element           


        for data_cobs in data_split:
            # Timing
            ta = []    

            #print('Cobs data:')
            #print(data_cobs)
            try:
                #logger.debug(funcname + ': ' + data_decobs.encode('hex_codec'))
                if(len(data_cobs) > 3):
                    data_decobs = cobs.decode(data_cobs)
                    #print('decobs data:')
                    #print(data_decobs)
                    #print(data_decobs[0],type(data_decobs[0]))                            
                    packet_ident    = data_decobs[0]
                    #logger.debug(funcname + ': packet_ident ' + str(packet_ident))
                    if(packet_ident == 0xae):
                        #print('JA')
                        #packet_flag_ltc = ord(data_decobs[1]) # python2
                        packet_flag_ltc = data_decobs[1]
                        num_ltcs        = bin(packet_flag_ltc).count("1")
                        # Convert ltc flat bits into indices
                        # If this is slow, this is a hot cython candidate
                        for i in range(8):
                            ind_ltcs[i] = (packet_flag_ltc >> i) & 1

                        ind_ltc = ind_ltcs
                        packet_size = 5 + 5 + 5 + num_ltcs * 3
                        packet_com_ltc0 = data_decobs[2]
                        packet_com_ltc1 = data_decobs[3]
                        packet_com_ltc2 = data_decobs[4]
                        # Decode the command
                        #speed,channel = ltc2442.interprete_ltc2442_command([packet_com_ltc0,packet_com_ltc1,packet_com_ltc2],channel_naming=1)
                        speed,channel = ltc2442.interprete_ltc2442_command_test([packet_com_ltc0,packet_com_ltc1,packet_com_ltc2],channel_naming=1)                        
                        ind = 5
                        #logger.debug(funcname + ': ltc flag ' + str(packet_flag_ltc))
                        #logger.debug(funcname + ': Num ltcs ' + str(num_ltcs))
                        #logger.debug(funcname + ': Ind ltc '  + str(ind_ltc))
                        #logger.debug(funcname + ': channel '  + str(channel))
                        #logger.debug(funcname + ': packet_size ' + str(packet_size))
                        #logger.debug(funcname + ': len(data_cobs) ' + str(len(data_cobs)))
                        if(len(data_decobs) == packet_size):
                            packet_num_bin  = data_decobs[ind:ind+5]
                            packet_num      = int(packet_num_bin.hex(), 16) # python3
                            ind += 5
                            packet_time_bin  = data_decobs[ind:ind+5]
                            packet_time     = int(packet_time_bin.hex(), 16)/device_info['counterfreq']
                            data_list = [packet_num,packet_time]
                            data_packet = {'num':packet_num,'t':packet_time}
                            data_packet['type'] = 'L'                            
                            data_packet['spd'] = speed
                            data_packet['ch'] = channel
                            data_packet['ind'] = ind_ltcs
                            data_packet['V'] = [9999.99] * num_ltcs
                            ind += 5
                            #logger.debug(funcname + ': Packet number: ' + packet_num_bin.hex())
                            #logger.debug(funcname + ': Packet 10khz time ' + packet_time_bin.hex())
                            for n,i in enumerate(range(0,num_ltcs*3,3)):
                                data_ltc = data_decobs[ind+i:ind+i+3]
                                data_ltc += 0x88.to_bytes(1,'big') # python3
                                if(len(data_ltc) == 4):
                                    #conv = ltc2442.convert_binary(data_ltc,ref_voltage=4.096,Voff = 2.048)
                                    conv = ltc2442.convert_binary_fast(data_ltc,ref_voltage=4.096,Voff = 2.048)
                                    #print(conv)
                                    data_packet['V'][n] = conv
                                    # This could make trouble if the list is too short ...
                                    data_list.append(conv)
                                #else:
                                #    data_packet.append(9999.99)
                            data_stream[channel].append(data_list)
                            data_packets.append(data_packet)
                        else:
                            logger.debug(funcname + ': Wrong packet size, is:' + str(len(data_cobs)) + ' should: ' + str(packet_size) )
                            #print('data_cobs:',data_cobs)
                            #print('data_cecobs:',data_decobs)                            

            #except cobs.DecodeError:
            #    logger.debug(funcname + ': COBS DecodeError')
            except Exception as e:
                logger.debug(funcname + ': Error:' + str(e))                
                pass


    return [data_stream,data_packets,data_str]



# Pyro science data packages and formats
pyro_science_format1_fields = [{'name':'dphi','unit':'deg','datatype':'float'},
                               {'name':'O2','unit':'umul/l','datatype':'float'}]



