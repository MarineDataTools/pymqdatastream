from cobs import cobs
import numpy as np
import logging
import pymqdatastream.connectors.todl.ltc2442 as ltc2442
import traceback # For debugging purposes
import sys
import datetime
import pynortek # Needed to convert Nortek binary data

logger = logging.getLogger('todl_data_packages')
logger.setLevel(logging.DEBUG)

def parse_firesting_data(data_str,unit_convert = True):
    # Packet of the form
    #U3<;00000021667825;RMR1 3 0 13 2 11312 1183226 864934 417122 -300000 -300000 518 106875 -1 -1 0 85383
    #                               S  phi    umol   mbar   asat  ext T   int T   amp amblig P Hum adc oxy
    if(unit_convert):
        fac = 1/1000.
    else:
        fac = 1.0
    data_pyro   = data_str.split(' ')    
    data_stat     = float(data_pyro[4])                                        
    data_dphi     = float(data_pyro[5])*fac
    data_umol     = float(data_pyro[6])*fac
    data_mbar     = float(data_pyro[7])*fac
    data_asat     = float(data_pyro[8])*fac                        
    data_ext_temp = float(data_pyro[9])*fac                            
    data_int_temp = float(data_pyro[10])*fac
    data_sgn_int  = float(data_pyro[11])*fac
    data_amb_light= float(data_pyro[12])*fac
    data_press     = float(data_pyro[13])*fac
    data_hum      = float(data_pyro[14])*fac
    data_adc      = float(data_pyro[15])*fac
    #data_oxy      = float(data_pyro[16])
    data_packet = {'type':'O'}
    data_packet['phi']  = data_dphi 
    data_packet['umol'] = data_umol
    data_packet['mbar'] = data_mbar
    data_packet['asat'] = data_asat
    data_packet['ext_temp'] = data_ext_temp
    data_packet['int_temp'] = data_int_temp
    data_packet['sgn_int']  = data_sgn_int
    data_packet['sgn_amb_light'] = data_amb_light
    data_packet['sgn_press'] = data_press
    data_packet['sgn_hum'] = data_hum
    return data_packet
    
    

def decode_format31(data_str_split,device_info):
    """
    Converts raw data of the format 31
    """
    funcname = '.decode_format31()'
    data_packets = []    
    for line in data_str_split:
        if(len(line)>3):
            try:
                data_split = line.split(';')
                packet_type = data_split[0]
                # LTC2444 packet
                if(packet_type == 'L'):
                    #packet_cnt10k_old = packet_cnt10k
                    packet_cnt10k = int(data_split[1])/device_info['counterfreq']
                    packet_num = int(data_split[2])
                    channel = int(data_split[3])
                    ad_data = data_split[4:]
                    # Fill the data list
                    data_list = [packet_num,packet_cnt10k]
                    # Fill the data packet dictionary
                    data_packet = {}
                    data_packet = {'num':packet_num,'cnt10ks':packet_cnt10k}
                    data_packet['type'] = 'L'                                
                    data_packet['ch'] = channel
                    data_packet['V'] = [9999.99] * len(device_info['adcs'])
                    for n,i in enumerate(device_info['adcs']):
                        n = int(n)
                        # Test if we have data at all
                        if(len(ad_data[n]) > 0):
                            V = float(ad_data[n])
                        else:
                            V = -9.0

                        data_packet['V'][n] = V
                        data_list.append(V)
                        data_packets.append(data_packet)
                        ##data_stream[channel].append(data_list)

                        # Time and counter information
                elif(packet_type == 'T'):
                    pass

                # IMU Information
                elif(packet_type == 'A'):
                    #A;00000021667084;00000000103737;+40.9;-0.09180;-0.02295;-1.01172;-0.05344;-1.02290;-0.63359;0.000000;0.000000;0.000000
                    packet_cnt10k = int(data_split[1])/device_info['counterfreq']
                    packet_num = int(data_split[2])
                    T = float(data_split[3])
                    accx = float(data_split[4])
                    accy = float(data_split[5])
                    accz = float(data_split[6])
                    gyrox = float(data_split[7])
                    gyroy = float(data_split[8])
                    gyroz = float(data_split[9])
                    magx = float(data_split[10])
                    magy = float(data_split[11])
                    magz = float(data_split[12])                                                                
                    #aux_data_stream[0].append([packet_num,packet_cnt10k,T,accx,accy,accz,gyrox,gyroy,gyroz])
                    data_packet = {'num':packet_num,'cnt10ks':packet_cnt10k}
                    data_packet['type'] = 'A'
                    data_packet['T'] = T
                    data_packet['acc'] = [accx,accy,accz]
                    data_packet['gyro'] = [gyrox,gyroy,gyroz]
                    data_packet['mag'] = [magx,magy,magz]                                
                    data_packets.append(data_packet)

                # Status
                # Stat;2000.01.14 07:07:33;Fr:31;1965398;6440195;St:1;Sh:1;Lg:0;SD:0;
                elif('Stat' in packet_type):
                    data_packet = {'type':'Stat'}
                    tstr = data_split[1]
                    data_packet['date']   = datetime.datetime.strptime(tstr, '%Y.%m.%d %H:%M:%S')
                    data_packet['date_str']   = tstr
                    data_packet['format'] = int(data_split[2].split(':')[1])
                    data_packet['cnt10ks']      = float(data_split[3])/device_info['counterfreq']
                    data_packet['cnt32k']    = int(data_split[4])
                    data_packet['start']  = int(data_split[5].split(':')[1])
                    data_packet['show']   = int(data_split[6].split(':')[1])
                    data_packet['log']    = int(data_split[7].split(':')[1])
                    data_packet['sd']     = int(data_split[8].split(':')[1])
                    if(len(data_split[9]) > 1):
                        data_packet['filename'] = data_split[9]
                    else:
                        data_packet['filename'] = None

                    #print('Status!',data_packet)
                    data_packets.append(data_packet)

                # Pyroscience packet
                elif('U3' in packet_type):
                    # Packet of the form
                    #U3<;00000021667825;RMR1 3 0 13 2 11312 1183226 864934 417122 -300000 -300000 518 106875 -1 -1 0 85383
                    #                               S  phi    umol   mbar   asat  ext T   int T   amp amblig P Hum adc oxy
                    if("RMR1 3 0" in data_split[2]):
                        data_pyro   = data_split[2].split(' ')                                    
                        if(len(data_pyro) > 4):
                            packet_cnt10k = int(data_split[1])/device_info['counterfreq']
                            packet_num    = 0
                            data_packet   = parse_firesting_data(data_split[2])
                            data_packet['num'] = packet_num
                            data_packet['cnt10ks'] = packet_cnt10k
                            data_packets.append(data_packet)                                    

            except Exception as e:
                logger.debug(funcname + ':' + str(e) + ' ' + str(line))
                traceback.print_exc(file=sys.stdout)


    return data_packets


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

    FLAG LTC: Every bit is dedicated to one of the eight physically
    available LTC2442 and is set to one if activated

    Args:
        deque:
        stream:
        dt: Time interval for polling [s]
    Returns:
        []: List of data

    """
    funcname = '.decode_format4()'    
    data_packets = []
    ind_ltcs = [0,0,0,0,0,0,0,0]
    nstreams = (max(device_info['channel_seq']) + 1)
    #data_stream = [[] for _ in range(nstreams) ]    
    data_split = data_str.split(b'\x00') # Packets are separated by 0x00
    err_packet = 0
    cobs_err_packet = 0
    ind_bad = []
    ind_bad0 = 0
    good_packet = 0    
    if(len(data_split) > 1):
        #print('data_str',data_str)
        #print('data_split',data_split)        
        if(len(data_split[-1]) == 0): # The last byte was a 0x00
           data_str = b''
        else:
           data_str = data_split[-1]
           data_split.pop() # remove last element           


        for data_cobs in data_split:
            ind_bad0 += len(data_cobs)
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
                    # LTC2442 packet
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
                            packet_cnt10k_bin  = data_decobs[ind:ind+5]
                            packet_cnt10ks     = int(packet_cnt10k_bin.hex(), 16)/device_info['counterfreq']
                            data_list = [packet_num,packet_cnt10ks]
                            data_packet = {'num':packet_num,'cnt10ks':packet_cnt10ks}
                            data_packet['type'] = 'L'     
                            data_packet['spd'] = speed
                            data_packet['ch'] = channel
                            data_packet['ind'] = ind_ltcs
                            data_packet['V'] = [9999.99] * num_ltcs
                            ind += 5
                            #logger.debug(funcname + ': Packet number: ' + packet_num_bin.hex())
                            #logger.debug(funcname + ': Packet 10khz time ' + packet_cnt10k_bin.hex())
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
                            #data_stream[channel].append(data_list)
                            data_packets.append(data_packet)
                            good_packet += 1
                        else:
                            # Peter temporary
                            logger.debug(funcname + ': Wrong packet size, is:' + str(len(data_cobs)) + ' should: ' + str(packet_size) )
                            err_packet += 1
                            #input('fds')
                            ind_bad.append(ind_bad0)
                            #print('data_cobs:',data_cobs)
                            #print('data_decobs:',data_decobs)

                    elif(packet_ident == 0x53): # Status string packet 'S'
                        data_utf8       = data_decobs.decode(encoding='utf-8')
                        data_split = data_utf8.split(';')
                        data_packet = {'type':'Stat'}
                        tstr = data_split[1]
                        td_tmp                  = datetime.datetime.strptime(tstr, '%Y.%m.%d %H:%M:%S')
                        #https://stackoverflow.com/questions/7065164/how-to-make-an-unaware-datetime-timezone-aware-in-python
                        data_packet['date']     = td_tmp.replace(tzinfo = device_info['timezone'])    
                        data_packet['timestamp']= datetime.datetime.timestamp(data_packet['date'])
                        data_packet['date_str']  = tstr
                        data_packet['format']    = int(data_split[2].split(':')[1])
                        data_packet['cnt10ks']   = float(data_split[3])/device_info['counterfreq']
                        data_packet['cnt32k']    = int(data_split[4])
                        data_packet['start']     = int(data_split[5].split(':')[1])
                        data_packet['show']      = int(data_split[6].split(':')[1])
                        data_packet['log']       = int(data_split[7].split(':')[1])
                        data_packet['sd']        = int(data_split[8].split(':')[1])
                        if(len(data_split[9]) > 1):
                            data_packet['filename'] = data_split[9]
                        else:
                            data_packet['filename'] = None

                            #print('Status!',data_packet)
                        data_packets.append(data_packet)                        
                            
                    elif(packet_ident == 0xac): # ACC IMU packet
                        if(len(data_decobs) > 12):
                            ind = 1                            
                            packet_num_bin  = data_decobs[ind:ind+5]
                            packet_num      = int(packet_num_bin.hex(), 16) # python3, its unsigned, TODO check how to do that
                            ind += 5
                            packet_cnt10k_bin = data_decobs[ind:ind+5]
                            packet_cnt10ks     = int(packet_cnt10k_bin.hex(), 16)/device_info['counterfreq']
                            ind += 5
                            accx = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)/16384.
                            ind += 2
                            accy = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)/16384.
                            ind += 2
                            accz = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)/16384.
                            ind += 2
                            T    = int(data_decobs[ind:ind+2].hex(),16)
                            T    = T / 333.87 + 21.0
                            ind += 2                            
                            gyrox = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)
                            ind += 2
                            gyroy = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)
                            ind += 2
                            gyroz = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)
                            ind += 2
                            magx = int.from_bytes(data_decobs[ind:ind+2], byteorder = 'big',signed=False)
                            ind += 2
                            magy = int.from_bytes(data_decobs[ind:ind+2], byteorder = 'big',signed=False)
                            ind += 2
                            magz = int.from_bytes(data_decobs[ind:ind+2], byteorder = 'big',signed=False)
                            print(magz)
                            data_packet = {'num':packet_num,'cnt10ks':packet_cnt10ks}
                            data_packet['type'] = 'A'
                            data_packet['T'] = T
                            data_packet['acc'] = [accx,accy,accz]
                            data_packet['gyro'] = [gyrox,gyroy,gyroz]
                            data_packet['mag'] = [magx,magy,magz]
                            data_packets.append(data_packet)
                    elif((packet_ident == 0xbb) or (packet_ident == 0xbc)): # ACC IMU FIFO packet (slim version)
                        #print('FiFO',len(data_decobs))
                        package_size = 21
                        nsamples = (len(data_decobs) - 13)/package_size
                        try: # We need T to test for valid data in uneven datasets
                            Ttst
                        except:
                            Ttst = -100
                        if(abs(nsamples - int(nsamples)) > 0.01): # Don take data with wrong size, have to deal with that later...
                            print('Wrong size, trying to shift start',nsamples)
                            #print(data_decobs)
                            ind_T = 6 + 13 # 13 bytes header and then at the sixth position
                            if(Ttst > -100):
                                for nt in range(0,package_size-1): # Check 10 bytes and compare 2 calculated temperatures with "old" temperature are within a given offset, if thats the case, take the data as valid
                                    Ttst1    = int.from_bytes(data_decobs[nt+ind_T:nt+ind_T+2],byteorder='big',signed=True)
                                    Ttst1    = Ttst1 / 333.87 + 21.0
                                    Ttst2    = int.from_bytes(data_decobs[nt+ind_T+package_size:nt+ind_T+2+package_size],byteorder='big',signed=True)
                                    Ttst2    = Ttst2 / 333.87 + 21.0               
                                    #print('T',T,'nt',nt,'Ttst1',Ttst1,'Ttst2',Ttst2)
                                    dT1 = abs(Ttst - Ttst1)
                                    dT2 = abs(Ttst - Ttst2)                                    
                                    if((dT1 < 0.25) & (dT2 < 0.25)):
                                        #print(data_decobs[nt:],len(data_decobs[nt:]))
                                        data_decobs_new = data_decobs[:13] + data_decobs[13 + nt:]
                                        #print(data_decobs_new,len(data_decobs_new))
                                        nsamples_new = (len(data_decobs[nt:]) - 13)/package_size
                                        #print('Found good index by shifting start by',nt,nsamples_new)

                                        if(abs(nsamples_new - int(nsamples_new)) < 0.01): # Good now?
                                            nsamples = nsamples_new
                                            #data_decobs = data_decobs[nt:]
                                            data_decobs = data_decobs_new
                                            print('Found good index by shifting start by',nt,nsamples_new)

                                        break                                                                                    
                        if(abs(nsamples - int(nsamples)) > 0.01): # Don take data with wrong size, have to deal with that later...
                            print('Could not find good samples in package (wrong package size)')
                        else:
                            #print('Nsamples',nsamples)                        
                            #print(data_decobs)
                            #print('FiFO end')
                            T_all = []
                            accx_all = []
                            accy_all = []
                            accz_all = []
                            gyrox_all = []
                            gyroy_all = []
                            gyroz_all = []                        
                            magx_all = []
                            magy_all = []
                            magz_all = []
                            ind = 1                            
                            packet_num_bin  = data_decobs[ind:ind+5]
                            packet_num         = int.from_bytes(packet_num_bin,'big',signed=False)
                            ind += 5
                            packet_cnt10k_bin = data_decobs[ind:ind+5]
                            packet_cnt10ks     = int.from_bytes(packet_cnt10k_bin,'big',signed=False)/device_info['counterfreq']
                            ind += 5
                            packet_dt_cnt10k_bin = data_decobs[ind:ind+2]
                            packet_dt_cnt10ks     = int.from_bytes(packet_dt_cnt10k_bin,'big',signed=False)/device_info['counterfreq']
                            ind += 2
                            for nsa in range(int(nsamples)):
                                accx = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)/16384.
                                ind += 2
                                accy = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)/16384.
                                ind += 2
                                accz = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)/16384.
                                ind += 2
                                T    = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)
                                T    = T / 333.87 + 21.0
                                Ttst = T # Having the data for testing packages with wrong package size
                                ind += 2                            
                                gyrox = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)
                                ind += 2
                                gyroy = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)
                                ind += 2
                                gyroz = int.from_bytes(data_decobs[ind:ind+2],byteorder='big',signed=True)
                                ind += 2
                                magx = int.from_bytes(data_decobs[ind:ind+2],byteorder='little',signed=True)
                                ind += 2
                                magy = int.from_bytes(data_decobs[ind:ind+2],byteorder='little',signed=True)
                                ind += 2
                                magz = int.from_bytes(data_decobs[ind:ind+2],byteorder='little',signed=True)
                                ind += 2

                                #bits = 16
                                #if (magx & (1 << (bits - 1))) != 0: # twos complement and Little Endian format
                                #    magx = magx - (1 << bits)
                                #if (magy & (1 << (bits - 1))) != 0: # twos complement and Little Endian format
                                #    magy = magy - (1 << bits)
                                #if (magz & (1 << (bits - 1))) != 0: # twos complement and Little Endian format
                                #    magz = magz - (1 << bits)

                                prop = data_decobs[ind]
                                ind += 1

                                T_all.append(T)
                                accx_all.append(accx)
                                accy_all.append(accy)
                                accz_all.append(accz)
                                gyrox_all.append(gyrox)
                                gyroy_all.append(gyroy)
                                gyroz_all.append(gyroz)                   
                                magx_all.append(magx)
                                magy_all.append(magy)
                                magz_all.append(magz)                       

                            data_packet = {'num':packet_num,'cnt10ks':packet_cnt10ks,'dt_cnt10ks':packet_dt_cnt10ks}
                            if(packet_ident == 0xbb):
                                sensor_num = 0
                            if(packet_ident == 0xbc):
                                sensor_num = 1

                            data_packet['type'] = 'An'
                            data_packet['sensor'] = sensor_num
                            data_packet['T'] = T_all
                            data_packet['acc'] = [accx_all,accy_all,accz_all]
                            data_packet['gyro'] = [gyrox_all,gyroy_all,gyroz_all]
                            data_packet['mag'] = [magx_all,magy_all,magz_all]
                            #https://arduino.stackexchange.com/questions/18625/converting-three-axis-magnetometer-to-degrees
                            data_packet['heading_xy'] = np.arctan2(np.asarray(magx_all),np.asarray(magy_all))/np.pi * 180
                            data_packet['heading_xz'] = np.arctan2(np.asarray(magx_all),np.asarray(magz_all))/np.pi * 180
                            data_packet['heading_yz'] = np.arctan2(np.asarray(magy_all),np.asarray(magz_all))/np.pi * 180
                            data_packets.append(data_packet)
                        
                    elif(packet_ident == 0xA0): # U3
                        ind = 1                            
                        packet_num_bin      = data_decobs[ind:ind+5]
                        packet_num          = int(packet_num_bin.hex(), 16) # python3
                        ind += 5
                        packet_cnt10k_bin   = data_decobs[ind:ind+5]
                        packet_cnt10ks      = int(packet_cnt10k_bin.hex(), 16)/device_info['counterfreq']
                        ind += 5
                        packet_serial_data  = data_decobs[ind:]
                        adv_data = pynortek.convert_bin(packet_serial_data,apply_unit_factor = True)
                        #data_packet = {'num':packet_num,'cnt10ks':packet_cnt10ks}
                        #data_packet['type'] = 'ADV'
                        #data_packet.update(adv_data)
                        #data_packets.append(data_packet)                        
                        #print(data_packet)
                        #print('ind',ind,len(data_decobs))
                        #print('Serial data package',packet_num,packet_cnt10ks)                        
                        #print(packet_serial_data)                        
                        #print('Serial data package done')                        
                    elif(packet_ident == 0xf0): # Pyroscience firesting
                        #\xf0\x00\x00\x00\x01Y\x00\x00\x08\x8f\x03RMR1 3 0 13 2 153908 -867323 -634011 -305757 -300000 -300000 482 16785 -1 -1 0 -62587\r
                        if(len(data_decobs) > 12):
                            ind = 1                            
                            packet_num_bin  = data_decobs[ind:ind+5]
                            packet_num      = int(packet_num_bin.hex(), 16) # python3
                            ind += 5
                            packet_cnt10k_bin  = data_decobs[ind:ind+5]
                            packet_cnt10ks     = int(packet_cnt10k_bin.hex(), 16)/device_info['counterfreq']
                            data_list_O        = [packet_num,packet_cnt10ks]
                            data_utf8          = data_decobs[11:].decode(encoding='utf-8')
                            if("RMR1 3 0" in data_utf8):
                                data_pyro   = data_utf8.split(' ')
                                if(len(data_pyro) > 4):
                                    data_packet = parse_firesting_data(data_utf8)
                                    data_packet['num'] = packet_num
                                    data_packet['cnt10ks'] = packet_cnt10ks
                                    data_packets.append(data_packet)



            #except cobs.DecodeError:
            #    logger.debug(funcname + ': COBS DecodeError')
            except Exception as e:
                cobs_err_packet += 1
                # Peter temporary
                logger.debug(funcname + ': Error:' + str(e))
                #print('data_cobs:',data_cobs)
                #input('Fds')
                pass

    packet_err = {'type':'format4_log','num_err':err_packet,'num_cobs_err':cobs_err_packet,'num_good':good_packet,'ind_bad':ind_bad}
    data_packets.append(packet_err)
    return [data_packets,data_str]



# Pyro science data packages and formats
pyro_science_format1_fields = [{'name':'dphi','unit':'deg','datatype':'float'},
                               {'name':'O2','unit':'umul/l','datatype':'float'}]



