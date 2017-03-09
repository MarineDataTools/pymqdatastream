"""


Supporting functions for the (`LTC2442
<http://www.linear.com/product/LTC2442>`_) converter.


"""



from numpy import *


# Channels
# From table 3 of the datasheet
# address = [SGL,ODD/SIGN,A2,A1,A0]
# channels = [CH0,CH1,CH2,CH3,COM]
channels = []
address  = []
address.append([0,0,0,0,0])
channels.append([+1,-1,0,0,0])
address.append([0,0,0,0,1])
channels.append([0,0,+1,-1,0])
address.append([0,1,0,0,0])
channels.append([-1,+1,0,0,0])
address.append([0,1,0,0,1])
channels.append([0,0,-1,+1,0])
address.append([1,0,0,0,0]) # 16, com mode
channels.append([+1,0,0,0,-1])
address.append([1,0,0,0,1]) # 17, com mode
channels.append([0,0,+1,0,-1])
address.append([1,1,0,0,0]) # 24, com mode
channels.append([0,+1,0,0,-1])
address.append([1,1,0,0,1]) # 25, com mode
channels.append([0,0,0,+1,-1])
# Speeds
# From table 4 of the datasheet
# [OSR3,OSR2,OSR1,OSR0,TWOX, Conversion speed (internal clock)]
# int   ltc2442_speed[] = {   30,   18,   16,  14,  12,  10,   8,   6,   4,   2,   31,  19,  17,  15,  13,  11,   9,   7,   5,   3};
# float ltc2442_freqs[] = {6.875,13.73, 27.5,  55, 110, 220, 439, 879,1760,3520,13.73,27.5,  55, 111, 220, 439, 879,1760,3520,7030}; 
modes = []
speeds = []
modes.append([0,0,0,0,0]) # 0
speeds.append(NaN)    # 'keep previous resolution'
# No latency modes
modes.append([0,0,0,1,0]) # 2
speeds.append(3.52e3)
modes.append([0,0,1,0,0]) # 4
speeds.append(1.76e3)
modes.append([0,0,1,1,0]) # 6
speeds.append(879)
modes.append([0,1,0,0,0]) # 8
speeds.append(439)
modes.append([0,1,0,1,0]) # 10
speeds.append(220)
modes.append([0,1,1,0,0]) # 12
speeds.append(110)
modes.append([0,1,1,1,0]) # 14
speeds.append(55)
modes.append([1,0,0,0,0]) # 16
speeds.append(27.5)
modes.append([1,0,0,1,0]) # 18
speeds.append(13.73)
modes.append([1,1,1,1,0]) # 30
speeds.append(6.875)
# Latency modes
modes.append([0,0,0,1,1]) # 3
speeds.append(7030)
modes.append([0,0,1,0,1]) # 5
speeds.append(3520)
modes.append([0,0,1,1,1]) # 7
speeds.append(1760)
modes.append([0,1,0,0,1]) # 9
speeds.append( 879)
modes.append([0,1,0,1,1]) # 11
speeds.append( 439)
modes.append([0,1,1,0,1]) # 13
speeds.append( 220)
modes.append([0,1,1,1,1]) # 15
speeds.append( 110)
modes.append([1,0,0,0,1]) # 17
speeds.append(  55)
modes.append([1,0,0,1,1]) # 19
speeds.append(27.5)
modes.append([1,1,1,1,1]) # 31
speeds.append(13.73)

# Create int numbers from the bit pattern defined
modesb = []
for m in modes:
    mb = 0
    for n,i in enumerate(m):
        if(i):
            mb += i<<(4-n)

    modesb.append(mb)
        
print('Modesb',modesb)

addressb = []
for m in address:
    mb = 0
    for n,i in enumerate(m):
        if(i):
            mb += i<<(4-n)

    addressb.append(mb)
        
print('Address',addressb)

modes = asarray(modes)

def random_data():
    rand_number = np.random.bytes(4)
    return rand_number

def interprete_ltc2442_command(command,channel_naming = 0):
    """
    
    
    LTC2442 command to human readable form ...

    Args:
       command: a list of bytes 
       channel_naming: The way the channels are named (0: standard; 1: SAM4LOG naming)
                       TODO: Explain what the difference is

    Returns:
       [speed,channels]: conversion speed in Hz, channels = [CH0,CH1,CH2,CH3,COM]
    
    
    """
    COM_ONE   = (command[0]>>7)     & 0x01 #
    COM_ZERO  = (command[0]>>6)     & 0x01 #
    EN        = (command[0]>>5)     & 0x01 #
    SGL       = (command[0]>>4)     & 0x01 #
    ODD       = (command[0]>>3)     & 0x01 #
    A2        = (command[0]>>2)     & 0x01 #
    A1        = (command[0]>>1)     & 0x01 #
    A0        = (command[0]>>0)     & 0x01 #
    OSR3      = (command[1]>>7)     & 0x01 #
    OSR2      = (command[1]>>6)     & 0x01 #
    OSR1      = (command[1]>>5)     & 0x01 #
    OSR0      = (command[1]>>4)     & 0x01 #
    TWOX      = (command[1]>>3)     & 0x01 #                    
    #print('COM_ONE ',COM_ONE)
    #print('COM_ZERO ',COM_ZERO)
    #print('EN ',EN)
    #print('SGL ',SGL)
    #print('ODD ',ODD)
    #print('A2 A1 A0 ',A2,A1,A0)
    #print('OSR3 OSR2 OSR1 OSR0 ',OSR3,OSR2,OSR1,OSR0)
    #print('TWOX ',TWOX)
    # Test which speed we have
    com       = [OSR3,OSR2,OSR1,OSR0,TWOX]
    com2      = asarray([com] * len(modes))
    tmp       = (modes ^ com2)
    ind_speed = where(sum(tmp,1) == 0)[0]
    #print('speeds',speeds[ind_speed])
    # Test which channels have been measured
    addr      = [SGL,ODD,A2,A1,A0]
    addr2     = asarray([addr] * 8)
    tmp       = ( address ^ addr2)
    ind_addr  = where(sum(tmp,1) == 0)[0]
    #print(channels[ind_addr])
    speed = speeds[ind_speed]
    channel = channels[ind_addr]
    if(channel_naming == 1):
        if(addr == [1,0,0,0,0]):
            return [speed,0]
        if(addr == [1,1,0,0,0]):
            return [speed,1]
        if(addr == [1,0,0,0,1]):
            return [speed,2]
        if(addr == [1,1,0,0,1]):
            return [speed,3]

    else:
        return [speed,channel]


def interprete_ltc2442_command_test(command,channel_naming = 0):
    """
    
    
    LTC2442 command to human readable form ...

    Args:
       command: a list of bytes 
       channel_naming: The way the channels are named (0: standard; 1: SAM4LOG naming)
                       TODO: Explain what the difference is

    Returns:
       [speed,channels]: conversion speed in Hz, channels = [CH0,CH1,CH2,CH3,COM]
    
    
    """
    # Test which speed we have
    com = command[1] >> 3
    for ind_speed,m in enumerate(modesb):
        if(com == m):
            break
    #print('speeds',speeds[ind_speed])
    # Test which channels have been measured    
    addr      = command[0] & 0x1F
    for ind_addr,m in enumerate(addressb):
        if(addr == m):
            break    
    speed = speeds[ind_speed]
    channel = channels[ind_addr]
    if(channel_naming == 1):
        if(addr == 16):
            return [speed,0]
        if(addr == 24):
            return [speed,1]
        if(addr == 17):
            return [speed,2]
        if(addr == 25):
            return [speed,3]

    else:
        return [speed,channel]    

    

    
def test_convert_binary():
    """

    Feeds convert_binary() with bit combinations documented in the datasheet

    """
    #test_7 = chr(0x2F) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    test_7 = b'\x2F\xFF\xFF\xFF'                                
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_7)    
    print('0.5 * VREF - 1LSB HEX:',hexstr)
    ret_test_7 = convert_binary(test_7)
    print('Voltage: ','{:2.20f}'.format(ret_test_7['V'][0]))
    print('\n\n')
    #test_8 = chr(0x28) + chr(0x00) + chr(0x00) + chr(0x00)
    test_8 = b'\x28\x00\x00\x00'                            
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_8)    
    print('0.5 * VREF  HEX:',hexstr    )
    ret_test_8 = convert_binary(test_8)
    print('Voltage: ','{:2.20f}'.format(ret_test_8['V'][0]))
    print('\n\n')
    #test_1 = chr(0x27) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    test_1 = b'\x27\xFF\xFF\xFF'                        
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_1)    
    print('0.25 * VREF - 1LSB HEX:',hexstr)
    ret_test_1 = convert_binary(test_1)
    print('Voltage: ','{:2.20f}'.format(ret_test_1['V'][0]))
    print('\n\n')
    #test_0 = chr(0x20) + chr(0) + chr(0) + chr(0)
    test_0 = b'\x20\x00\x00\x00'                    
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_0)    
    print('ZERO TEST HEX:',hexstr)
    ret_test_0 = convert_binary(test_0)
    print('Voltage: ','{:2.20f}'.format(ret_test_0['V'][0]))
    print('\n\n')
    #test_2 = chr(0x1F) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    test_2 = b'\x1F\xFF\xFF\xFF'                
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_2)    
    print('- 1LSB HEX:',hexstr)
    ret_test_2 = convert_binary(test_2)
    print('Voltage: ','{:2.20f}'.format(ret_test_2['V'][0]))
    print('\n\n')
    #test_6 = chr(0x18) + chr(0x00) + chr(0x00) + chr(0x00)
    test_6 = b'\x18\x00\x00\x00'            
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_6)    
    print('-0.25 * VREF HEX:',hexstr)
    ret_test_6 = convert_binary(test_6)
    print('Voltage: ','{:2.20f}'.format(ret_test_6['V'][0]))
    print('\n\n')
    #test_3 = chr(0x17) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    test_3 = b'\x17\xFF\xFF\xFF'
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_3)    
    print('-0.25 * VREF - 1LSB HEX:',hexstr)
    ret_test_3 = convert_binary(test_3)
    print('Voltage: ','{:2.20f}'.format(ret_test_3['V'][0]))
    print('\n\n')
    #test_4 = chr(0x10) + chr(0x00) + chr(0x00) + chr(0x00)
    test_4 = b'\x10\x00\x00\x00'    
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_4)    
    ret_test_4 = convert_binary(test_4)
    print('-0.5 * VREF HEX:',hexstr)
    print('Voltage: ','{:2.20f}'.format(ret_test_4['V'][0]))
    print('\n\n')
    #test_5 = chr(0x2F) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    test_5 = b'\x2F\xFF\xFF\xFF'        
    hexstr = '0x' + ''.join('{:02X}'.format(a) for a in test_5)    
    print('0.5 * VREF - 1LSB HEX:',hexstr)
    ret_test_5 = convert_binary(test_5)
    print('Voltage: ','{:2.20f}'.format(ret_test_5['V'][0]))
    print('\n\n'    )
    
def convert_binary(ad_raw,ref_voltage=5.0,Voff = 0, Vlarge = 9.9999, Vsmall = -9.9999):
    """ 

    Converts the LTC2442 binary data into voltage
    Input ad_raw has to be a 8 bit char

    Args:
       ad_raw: raw binary data as an binary array of length 4 
       ref_voltage: Reference voltage of (VREF in LTC2442 Datasheet)
       Voff: Offset voltage to be added to the result. 
       Vlarge: Output voltage if measured voltage is above ref_voltage [default:  9.9999]
       Vsmall: Output voltage if measured voltage is below ref_voltage [default: -9.9999]
    Returns:
       data_rec: recarray((1,), dtype=[('V', float64),('SIG', bool), ('DMY', bool),
                                     ('MSB', bool), ('FLAG_VALID', bool),])

    """
    # ADC binary status bits (LTC datasheet page 11)
    #  31   30   29   28   27  ...  0 ( ad_32bit  )
    #  07   06   05   04   03         ( ad_raw[0] )
    # /EOC  DMY  SIG  MSB          LSB
    #print('raw',ad_raw)
    ad_32bit = (ad_raw[0]<<24) | (ad_raw[1]<<16) | (ad_raw[2]<<8) | ad_raw[3]
    ad_data = ad_32bit & 0x0FFFFFFF
    notEOC  = (ad_raw[0]>>7)     & 0x01 # 
    DMY     = (ad_raw[0]>>6)     & 0x01 # 
    SIG     = (ad_raw[0]>>5)     & 0x01 # sign
    MSB     = (ad_raw[0]>>4)     & 0x01 # Most significant bit
    if((SIG == True) & (MSB == True)): # LTC datasheet page 11
       cons = 'Vin > 0.5 * Vref BAD'
       FLAG_VALID = False
       Vout = Vsmall
    if((SIG == True) & (MSB == False)): # LTC datasheet page 11
       cons = ' 0 <= Vin < 0.5 * Vref GOOD'
       FLAG_VALID = True
    if((SIG == False) & (MSB == True)): # LTC datasheet page 11
       cons = ' -0.5 * Vref < Vin < 0 GOOD'
       FLAG_VALID = True
    if((SIG == False) & (MSB == False)): # LTC datasheet page 11
       cons = 'Vin < -0.5 * Vref BAD'
       FLAG_VALID = False
       Vout = Vlarge       

    if(FLAG_VALID):
        refp = ref_voltage
        refm = 0.0
        Vref = 0.5 * (refp - refm)

        if(SIG == 1):
            bout_shift = - ad_data 
        else:
            bout_shift = (2**28) - ad_data

        Vout = 1.0 * bout_shift/(2**28) * Vref + Voff
        
    data_rec = recarray((1,), dtype=[('V', float64),('SIG', bool), ('DMY', bool),
                                     ('MSB', bool), ('FLAG_VALID', bool),])
    data_rec['V'] = Vout
    data_rec['SIG'] = SIG
    data_rec['DMY'] = DMY
    data_rec['MSB'] = MSB
    data_rec['FLAG_VALID'] = FLAG_VALID

    return data_rec


def convert_binary_fast(ad_raw,ref_voltage=5.0,Voff = 0, Vlarge = 9.9999, Vsmall = -9.9999, output_format=0):
    """ 

    Converts the LTC2442 binary data into voltage
    Input ad_raw has to be a 8 bit char

    Args:
       ad_raw: raw binary data as an binary array of length 4 
       ref_voltage: Reference voltage of (VREF in LTC2442 Datasheet)
       Voff: Offset voltage to be added to the result. 
       Vlarge: Output voltage if measured voltage is above ref_voltage [default:  9.9999]
       Vsmall: Output voltage if measured voltage is below ref_voltage [default: -9.9999]
       output_format: 0: Returns only the voltage, 1: Returns an numpy recarray
    Returns:
       V (output_format == 0): Voltage
       data_rec (output_format == 1): recarray((1,), dtype=[('V', float64),('SIG', bool), ('DMY', bool),
                                     ('MSB', bool), ('FLAG_VALID', bool),])

    """
    # ADC binary status bits (LTC datasheet page 11)
    #  31   30   29   28   27  ...  0 ( ad_32bit  )
    #  07   06   05   04   03         ( ad_raw[0] )
    # /EOC  DMY  SIG  MSB          LSB
    #print('raw',ad_raw)
    ad_32bit = (ad_raw[0]<<24) | (ad_raw[1]<<16) | (ad_raw[2]<<8) | ad_raw[3]
    ad_data = ad_32bit & 0x0FFFFFFF
    notEOC  = (ad_raw[0]>>7)     & 0x01 # 
    DMY     = (ad_raw[0]>>6)     & 0x01 # 
    SIG     = (ad_raw[0]>>5)     & 0x01 # sign
    MSB     = (ad_raw[0]>>4)     & 0x01 # Most significant bit
    if((SIG == True) & (MSB == True)): # LTC datasheet page 11
       #cons = 'Vin > 0.5 * Vref BAD'
       FLAG_VALID = False
       Vout = Vsmall
    if((SIG == True) & (MSB == False)): # LTC datasheet page 11
       #cons = ' 0 <= Vin < 0.5 * Vref GOOD'
       FLAG_VALID = True
    if((SIG == False) & (MSB == True)): # LTC datasheet page 11
       #cons = ' -0.5 * Vref < Vin < 0 GOOD'
       FLAG_VALID = True
    if((SIG == False) & (MSB == False)): # LTC datasheet page 11
       #cons = 'Vin < -0.5 * Vref BAD'
       FLAG_VALID = False
       Vout = Vlarge       

    if(FLAG_VALID):
        refp = ref_voltage
        refm = 0.0
        Vref = 0.5 * (refp - refm)

        if(SIG == 1):
            bout_shift = - ad_data 
        else:
            bout_shift = (2**28) - ad_data

        Vout = 1.0 * bout_shift/(2**28) * Vref + Voff


    if(output_format == 0):
        return Vout
    if(output_format == 1):
        data_rec = recarray((1,), dtype=[('V', float64),('SIG', bool), ('DMY', bool),
                                         ('MSB', bool), ('FLAG_VALID', bool),])
        data_rec['V'] = Vout
        data_rec['SIG'] = SIG
        data_rec['DMY'] = DMY
        data_rec['MSB'] = MSB
        data_rec['FLAG_VALID'] = FLAG_VALID

        return data_rec


if __name__ == '__main__':

    test_convert_binary()

