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
    V_ch1 = nca.variables['V_adc0_ch1']
    V_ch2 = nca.variables['V_adc0_ch2']

    pl.figure(1)
    pl.clf()
    pl.subplot(2,1,1)
    pl.plot(t_ch1,V_ch1)
    pl.title('V_adc0_ch1')
    pl.xlabel('t [s]')
    pl.ylabel('U [V]')

    pl.subplot(2,1,2)
    pl.plot(t_ch1,V_ch2)
    pl.title('V_adc0_ch2')
    pl.xlabel('t [s]')
    pl.ylabel('U [V]')    
    pl.draw()
    pl.show()
