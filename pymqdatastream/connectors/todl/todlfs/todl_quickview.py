import sys
import argparse
import numpy as np
import pylab as pl
import netCDF4
import logging

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('todl_quickview')
logger.setLevel(logging.DEBUG)

def main():
    usage_str = 'todl_quikview todldata.nc'
    desc = 'Makes a quick view of the todl netCDF file: ' + usage_str
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('filename', help= 'The filename of the todl netcdf file')
    parser.add_argument('--verbose', '-v', action='count')

    args = parser.parse_args()
    # Print help and exit when no arguments are given
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)


    fname  = args.filename

    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.INFO
    elif(args.verbose > 1):
        loglevel = logging.DEBUG


        
    nc = netCDF4.Dataset(fname)
    nca = nc.groups['adc']
    t_ch1 = nca.variables['t_ch1'][:]
    t_ch2 = nca.variables['t_ch2'][:]
    f1 = 1/(np.diff(t_ch1).mean())
    f2 = 1/(np.diff(t_ch2).mean())    
    V_ch1 = nca.variables['V_adc0_ch1'][:]
    V_ch2 = nca.variables['V_adc0_ch2'][:]


    ncp = nc.groups['pyro']
    t_p = ncp.variables['t_pyro']
    fp = 1/(np.diff(t_p).mean())    
    phi = ncp.variables['phi']


    V_ch1_pl = np.asarray(V_ch1[:])
    V_ch2_pl = np.asarray(V_ch2[:])

    ind_bad1 = (V_ch1_pl < 0.0) | (V_ch1_pl > 5.0)
    V_ch1_pl = np.ma.masked_where(ind_bad1,V_ch1_pl)

    ind_bad2 = (V_ch2_pl < 0.0) | (V_ch2_pl > 5.0)
    V_ch2_pl = np.ma.masked_where(ind_bad2,V_ch2_pl)    

    pl.figure(1)
    pl.clf()
    pl.subplot(2,1,1)
    pl.plot(t_ch1,V_ch1_pl)
    pl.title('V_adc0_ch1; Freq:' + str(f1.round(2)))
    pl.xlabel('t [s]')
    pl.ylabel('U [V]')

    pl.subplot(2,1,2)
    pl.plot(t_ch2,V_ch2_pl)
    pl.title('V_adc0_ch2; Freq:' + str(f2.round(2)))
    pl.xlabel('t [s]')
    pl.ylabel('U [V]')    
    pl.draw()


    pl.figure(2)
    pl.clf()
    pl.plot(t_p,phi)
    pl.title('Firesting data; Freq:' + str(fp.round(2)))
    pl.draw()    


    




    pl.show()
