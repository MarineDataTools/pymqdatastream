import sys
import argparse
import numpy as np
import pylab as pl
import netCDF4
import logging
import pymqdatastream.connectors.todl.todl_data_processing as todl_data_processing

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('todl_quickview')
logger.setLevel(logging.DEBUG)


def main():
    usage_str = 'todl_quikview todldata.nc'
    desc = 'Makes a quick view of the todl netCDF file: ' + usage_str
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('filename', help= 'The filename of the todl netcdf file')
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--count', '-c', action='store_true')    


    args = parser.parse_args()
    # Print help and exit when no arguments are given
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)


    fname  = args.filename
    if(args.count == False):
        timeax = True
    else:
        timeax = False
        
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG


        
    nc = netCDF4.Dataset(fname)
    # Try to read ADC data
    try:    
        nca = nc.groups['adc']
    except:
        nca = None
        pass

    if(nca is not None):
        try:
            cnt10ks_ch1 = nca.variables['cnt10ks_ch1'][:]
            time_ch1 = netCDF4.num2date(nca.variables['time_ch1'][:],units=nca.variables['time_ch1'].units)
            f1 = 1/(np.diff(cnt10ks_ch1).mean())
            V_ch1 = nca.variables['V_adc1_ch1'][:]
            FLAG_CH1=True
            print('Found ch1 ADC data')            
        except:
            FLAG_CH1=False            
            pass

        try:     
            cnt10ks_ch2 = nca.variables['cnt10ks_ch2'][:]
            time_ch2 = netCDF4.num2date(nca.variables['time_ch2'][:],units=nca.variables['time_ch2'].units)
            f2 = 1/(np.diff(cnt10ks_ch2).mean())    
            V_ch2 = nca.variables['V_adc1_ch2'][:]
            FLAG_CH2=True
            print('Found ch2 ADC data')
        except:
            FLAG_CH2=False            
            pass            

    # Read in PyroScience data
    try:
        ncp = nc.groups['pyro']
        cnt10ks_p = ncp.variables['cnt10ks_pyro'][:]
        time_p = netCDF4.num2date(ncp.variables['time'][:],units = ncp.variables['time'].units)
        fp = 1/(np.diff(cnt10ks_p).mean())    
        phi = ncp.variables['phi'][:]
        FLAG_PYRO=True
        print('Found Pyro data')        
    except:
        FLAG_PYRO=False
        

    # Read in IMU
    try:
        FLAG_IMU = True        
        nci = nc.groups['imu']
        cnt10ks_imu = nci.variables['cnt10ks_imu'][:]
        time_imu = netCDF4.num2date(nci.variables['time'][:],units=nci.variables['time'].units)        
        fi = 1/(np.diff(cnt10ks_imu).mean())    
        accx = nci.variables['accx'][:]
        accy = nci.variables['accy'][:]
        accz = nci.variables['accz'][:]
        gyrox = nci.variables['gyrox'][:]
        gyroy = nci.variables['gyroy'][:]
        gyroz = nci.variables['gyroz'][:]
        magx = nci.variables['magx'][:]
        magy = nci.variables['magy'][:]
        magz = nci.variables['magz'][:]
        print('Found IMU data')                
    except Exception as e:
        print(e)
        FLAG_IMU = False

    if FLAG_CH1:
        V_ch1_pl = np.asarray(V_ch1[:])
        print('Despiking ch1')
        spikes_ch1 = todl_data_processing.findspikes(cnt10ks_ch1,V_ch1_pl,.1)
        #V_ch1_pl = np.ma.masked_where(spikes_ch1 == 1,V_ch1_pl)
        print('Plotting ADC ch 1')
        pl.figure(1)
        pl.clf()
        pl.subplot(1,1,1)
        if(timeax):
            x_ch1 = time_ch1
        else:
            x_ch1 = cnt10ks_ch1
            
        pl.plot(x_ch1,V_ch1_pl)
        pl.title('V_adc0_ch1; Freq:' + str(f1.round(2)))
        pl.xlabel('t [s]')
        pl.ylabel('U [V]')        

    if FLAG_CH2:        
        V_ch2_pl = np.asarray(V_ch2[:])
        print('Despiking ch2')
        spikes_ch2 = todl_data_processing.findspikes(cnt10ks_ch2,V_ch2_pl,.1)
        V_ch2_pl = np.ma.masked_where(spikes_ch2 == 1,V_ch2_pl)

        pl.figure(2)
        pl.clf()
        pl.subplot(1,1,1)
        if(timeax):
            x_ch2 = time_ch2
        else:
            x_ch2 = cnt10ks_ch2
        pl.plot(x_ch2,V_ch2_pl)
        pl.title('V_adc0_ch2; Freq:' + str(f2.round(2)))
        pl.xlabel('t [s]')
        pl.ylabel('U [V]')    
        pl.draw()

    #ind_bad1 = (V_ch1_pl < 0.0) | (V_ch1_pl > 5.0)
    #V_ch1_pl = np.ma.masked_where(ind_bad1,V_ch1_pl)

    #ind_bad2 = (V_ch2_pl < 0.0) | (V_ch2_pl > 5.0)
    #V_ch2_pl = np.ma.masked_where(ind_bad2,V_ch2_pl)    

    # Plot Firesting data
    if FLAG_PYRO:
        print('Plotting Pyro')
        pl.figure(3)
        pl.clf()
        if(timeax):
            x_pyro = time_p
        else:
            x_pyro = cnt10ks_p

        pl.plot(x_pyro,phi)

        pl.title('Firesting data; Freq:' + str(fp.round(2)))
        pl.draw()

    # Plot IMU data
    if FLAG_IMU:
        print('Plotting IMU')
        pl.figure(4)
        pl.clf()
        pl.subplot(3,1,1)
        if(timeax):
            x_imu = time_imu
        else:
            x_imu = cnt10ks_imu   
        pl.plot(x_imu,accx,'o')
        pl.plot(x_imu,accy,'o')
        pl.plot(x_imu,accz,'o')        
        pl.title('Acceleration IMU; Freq:' + str(fi.round(2)))
        pl.legend(('x','y','z'))    

        pl.subplot(3,1,2)
        pl.plot(x_imu,gyrox,'o')
        pl.plot(x_imu,gyroy,'o')
        pl.plot(x_imu,gyroz,'o')
        pl.title('Gyro IMU; Freq:' + str(fi.round(2)))
        pl.legend(('x','y','z'))
    
        pl.subplot(3,1,3)
        pl.plot(x_imu,magx,'o')
        pl.plot(x_imu,magy,'o')
        pl.plot(x_imu,magz,'o')
        pl.title('MAG IMU; Freq:' + str(fi.round(2)))
        pl.legend(('x','y','z'))    
        pl.draw()    


    




    pl.show()
