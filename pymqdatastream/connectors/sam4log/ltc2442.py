# Python functions to convert LTC2442 data to voltages
#
# Peter Holtermann


from numpy import *

def random_data():
    rand_number = np.random.bytes(4)
    return rand_number

def interprete_ltc2442_command(command):
    """
    LTC2442 command to human readable form ...
    """
    COM_ONE   = (ord(command[0])>>7)     & 0x01 #
    COM_ZERO  = (ord(command[0])>>6)     & 0x01 #
    EN        = (ord(command[0])>>5)     & 0x01 #
    SGL       = (ord(command[0])>>4)     & 0x01 #
    ODD       = (ord(command[0])>>3)     & 0x01 #
    A2        = (ord(command[0])>>2)     & 0x01 #
    A1        = (ord(command[0])>>1)     & 0x01 #
    A0        = (ord(command[0])>>0)     & 0x01 #
    OSR3      = (ord(command[1])>>7)     & 0x01 #
    OSR2      = (ord(command[1])>>6)     & 0x01 #
    OSR1      = (ord(command[1])>>5)     & 0x01 #
    OSR0      = (ord(command[1])>>4)     & 0x01 #
    TWOX      = (ord(command[1])>>3)     & 0x01 #                    
    print('COM_ONE ',COM_ONE)
    print('COM_ZERO ',COM_ZERO)
    print('EN ',EN)
    print('SGL ',SGL)
    print('ODD ',ODD)
    print('A2 A1 A0 ',A2,A1,A0)
    print('OSR3 OSR2 OSR1 OSR0 ',OSR3,OSR2,OSR1,OSR0)
    print('TWOX ',TWOX)
def test_convert_binary():
    """
    Feeds convert_binary with bit combinations documented in the datasheet
    """
    test_7 = chr(0x2F) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_7)    
    print('0.5 * VREF - 1LSB HEX:',hexstr)
    ret_test_7 = convert_binary(test_7)
    print('Voltage: ','{:2.20f}'.format(ret_test_7['V'][0]))
    print('\n\n')
    test_8 = chr(0x28) + chr(0x00) + chr(0x00) + chr(0x00)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_8)    
    print('0.5 * VREF  HEX:',hexstr    )
    ret_test_8 = convert_binary(test_8)
    print('Voltage: ','{:2.20f}'.format(ret_test_8['V'][0]))
    print('\n\n')
    test_1 = chr(0x27) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_1)    
    print('0.25 * VREF - 1LSB HEX:',hexstr)
    ret_test_1 = convert_binary(test_1)
    print('Voltage: ','{:2.20f}'.format(ret_test_1['V'][0]))
    print('\n\n')
    test_0 = chr(0x20) + chr(0) + chr(0) + chr(0)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_0)    
    print('ZERO TEST HEX:',hexstr)
    ret_test_0 = convert_binary(test_0)
    print('Voltage: ','{:2.20f}'.format(ret_test_0['V'][0]))
    print('\n\n')
    test_2 = chr(0x1F) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_2)    
    print('- 1LSB HEX:',hexstr)
    ret_test_2 = convert_binary(test_2)
    print('Voltage: ','{:2.20f}'.format(ret_test_2['V'][0]))
    print('\n\n')
    test_6 = chr(0x18) + chr(0x00) + chr(0x00) + chr(0x00)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_6)    
    print('-0.25 * VREF HEX:',hexstr)
    ret_test_6 = convert_binary(test_6)
    print('Voltage: ','{:2.20f}'.format(ret_test_6['V'][0]))
    print('\n\n')
    test_3 = chr(0x17) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_3)    
    print('-0.25 * VREF - 1LSB HEX:',hexstr)
    ret_test_3 = convert_binary(test_3)
    print('Voltage: ','{:2.20f}'.format(ret_test_3['V'][0]))
    print('\n\n')
    test_4 = chr(0x10) + chr(0x00) + chr(0x00) + chr(0x00)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_4)    
    ret_test_4 = convert_binary(test_4)
    print('-0.5 * VREF HEX:',hexstr)
    print('Voltage: ','{:2.20f}'.format(ret_test_4['V'][0]))
    print('\n\n')
    test_5 = chr(0x2F) + chr(0xFF) + chr(0xFF) + chr(0xFF)
    hexstr = '0x' + ''.join('{:02X}'.format(ord(a)) for a in test_5)    
    print('0.5 * VREF - 1LSB HEX:',hexstr)
    ret_test_5 = convert_binary(test_5)
    print('Voltage: ','{:2.20f}'.format(ret_test_5['V'][0]))
    print('\n\n'    )
    
def convert_binary(ad_raw,ref_voltage=5.0,Voff = 0, Vlarge = 9.9999, Vsmall = -9.9999):
    """ 

    Converts the LTC2442 binary data into voltage
    Input ad_raw has to be a 8 bit char

    Args:
       ad_raw: raw binary data as a char string ( python2 ) or binary ( python3 )
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
    ad_32bit = (ord(ad_raw[0])<<24) | (ord(ad_raw[1])<<16) | (ord(ad_raw[2])<<8) | ord(ad_raw[3])
    ad_data = ad_32bit & 0x0FFFFFFF
    notEOC  = (ord(ad_raw[0])>>7)     & 0x01 # 
    DMY     = (ord(ad_raw[0])>>6)     & 0x01 # 
    SIG     = (ord(ad_raw[0])>>5)     & 0x01 # sign
    MSB     = (ord(ad_raw[0])>>4)     & 0x01 # Most significant bit
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


if __name__ == '__main__':

    test_convert_binary()

