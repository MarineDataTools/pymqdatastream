0.7.9:
	- todl_pymqds:
	  - Changed time base to unix time in the netCDF format of the TODL
	  - Changed time calculation from interpolation to polyfit in netCDF file
	  - Changed variable names, t_ is renamed cnt10ks to maked more clear that the variable is simply a counter
	  - Added compression to netCDF variables
	  - Added more data fields in Pyro science oxygen	  
	- todl_gui:
	  - Corrected average display of ADC
	  - Added average display for Pyro Science

0.7.1:
	- Re-Added GPS functionality

0.7.2:
	- Added conversion utility to netCDF4 (with command

0.7.3:
	- Reworked TODL for format 4

0.7.4:
	- Added pymqds_print for simple command line printing of pymqdatastreams
	- Stream queuelen = -1 added
	- Added Datastream.num_streams and Stream.number to uniquely number all streams (will be used as a replacement for the long uuid)
	- Possible to subscribe Stream with an address string like this 20@tcp://127.0.0.1:18055

0.7.5:	2018-03-20
	- reworked and improved pyqtgraph_plotxy (add_graph works, xy axes choose)
	- added frequency calculation of TODL
	2018-04-03
	- added logging_level_socket for finer logging control
	- changed pymqs_plotxy such that data is always saved, regardless if plotted or not
	2018-05-02
	- added timezone awareness (at the moment UTC)

0.7.6:	2018-05-09
        - made netCDF4 date computation aware of invalid data (checks
          if difference between increment of 10kHz counter and date in
          Stat packet is within range of 2 seconds, this is rough but
          good enough to remove the worst values)
	- todlfs_get_files can now extract a specific file, and not all at once

0.7.7:	2018-06-01
        - Added findspikes and todl_data_processing.py

