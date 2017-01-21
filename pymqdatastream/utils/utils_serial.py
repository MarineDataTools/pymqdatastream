import serial
import sys
import os
import logging
import glob

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('utils_serial')
logger.setLevel(logging.DEBUG)


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system

        found here: http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    """
    FLAG_UNIXOID=True
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
        FLAG_UNIXOID=False
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            logger.debug("serial_ports(): Testing serial port " + str(port))
            if(FLAG_UNIXOID): # test if serial port has been locked
                ret = test_serial_lock_file(port,brutal=True)
            else:
                ret = False
                
            if(ret == False):
                logger.debug("serial_ports(): Opening serial port " + str(port))
                s = serial.Serial(port)
                s.close()
                result.append(port)
        #except (OSError, serial.SerialException):
        except Exception as e:
            logger.debug('serial_ports(): Exception:' + str(e))
            pass

    return result


def test_serial_lock_file(port, brutal = False):
    """
    Creates or removes a lock file for a serial port in linux
    Args:
       port: Device string
       brutal: Remove lock file if a nonexisting PID was found or no PID at all within the file
    Return:
       True if port is already in use, False otherwise
    """
    devicename = port.split('/')[-1]
    filename = '/var/lock/LCK..'+devicename
    print('serial_lock_file(): filename:' + str(filename))
    try:
        flock = open(filename,'r')
        pid_str = flock.readline()
        flock.close()
        print('test_serial_lock_file(): PID:' + pid_str)
        PID_EXIST=None
        try:
            pid = int(pid_str)
            PID_EXIST = psutil.pid_exists(pid)
            pid_ex = ' does not exist.'
            if(PID_EXIST):
                pid_ex = ' exists.'
            print('Process with PID:' + pid_str[:-1] + pid_ex)
        except Exception as e:
            print('No valid PID value' + str(e))

            
        if(PID_EXIST == True):
            return True
        elif(PID_EXIST == False):
            if(brutal == False):
                return True
            else: # Lock file with "old" PID
                print('Removing lock file, as it has a not existing PID')
                os.remove(filename)
                return False
        elif(PID_EXIST == None): # No valid PID value
            if(brutal):
                print('Removing lock file, as it no valid PID')
                os.remove(filename)
                return False
            else:
                return True
    except Exception as e:
        print('serial_lock_file():' + str(e))
        return False

    
def serial_lock_file(port,remove=False):
    """
    Creates or removes a lock file for a serial port in linux
    """
    devicename = port.split('/')[-1]
    filename = '/var/lock/LCK..'+devicename
    print('serial_lock_file(): filename:' + str(filename))
        
    if(remove == False):
        try:
            flock = open(filename,'w')
            lockstr = str(os.getpid()) + '\n'
            print('Lockstr:' + lockstr)
            flock.write(lockstr)
            flock.close()
        except Exception as e:
            print('serial_lock_file():' + str(e))
    else:
        try:
            print('serial_lock_file(): removing filename:' + str(filename))
            flock = open(filename,'r')
            line = flock.readline()
            print('data',line)
            flock.close()
            os.remove(filename)
        except Exception as e:
            print('serial_lock_file():' + str(e))
