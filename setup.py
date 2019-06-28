from setuptools import setup
import os

import sys


# Requires (TODO put it into a proper requirement list)
# psutil
# zeromq
# serial

if sys.version_info >= (3,4):

    ROOT_DIR='pymqdatastream'
    with open(os.path.join(ROOT_DIR, 'VERSION')) as version_file:
        version = version_file.read().strip()

    setup(name='pymqdatastream',
          version=version,
          description='Realtime datastreaming interface based on the zeromq library',
          url='https://github.com/MarineDataTools/pymqdatastream/',
          author='Peter Holtermann',
          author_email='peter.holtermann@systemausfall.org',
          license='GPLv03',
          packages=['pymqdatastream'],
          scripts = ['pymqdatastream/connectors/test/pymqds_bare.py',\
                     'pymqdatastream/connectors/test/pymqds_bare_reqrep.py',\
                     'pymqdatastream/connectors/math_operator/pymqds_math_op.py',\
                     'pymqdatastream/connectors/test/pymqds_test.py',\
                     'pymqdatastream/connectors/nmea/pymqds_NMEA0183.py',\
                     'pymqdatastream/connectors/logger/pymqds_slogger.py',\
                     'pymqdatastream/connectors/todl/todlfs/todlfs_read_device.sh',\
                     'pymqdatastream/connectors/logger/pymqds_gui_slogger.py'],
          entry_points={ 'console_scripts': ['NMEA0183grabber=pymqdatastream.connectors.nmea.NMEA0183grabber:main',\
          'pymqds_query=pymqdatastream:query',\
          'pymqds_scan=pymqdatastream.connectors.basic.pymqds_scan:main',\
          'pymqds_print=pymqdatastream.connectors.basic.pymqds_print:main',\
          'pymqds_gps=pymqdatastream.connectors.nmea.pymqds_nmea0183_gui:main',\
          'pymqds_rand=pymqdatastream.connectors.test.pymqds_rand:main',\
          'pymqds_qtshowdata=pymqdatastream.connectors.qt.pymqds_qtshowdata:main',\
          'pymqds_qtoverview=pymqdatastream.connectors.qt.pymqds_qtoverview:main',\
          'pymqds_plotxy=pymqdatastream.connectors.pyqtgraph.pymqds_plotxy:main',\
          'todl=pymqdatastream.connectors.todl.pymqds_todl:main',\
          'todl_gui=pymqdatastream.connectors.todl.pymqds_gui_todl:main',\
          'todl_datatool=pymqdatastream.connectors.todl.todl_data_tool:main',\
          'todl_rawtonc=pymqdatastream.connectors.todl.pymqds_todl:todlraw_to_netCDF',\
          'todl_quickview=pymqdatastream.connectors.todl.todlfs.todl_quickview:main',\
          'todlfs_get_files=pymqdatastream.connectors.todl.todlfs.todlfs_get_files:todlfs_get_files',\
          'todlfs_list=pymqdatastream.connectors.todl.todlfs.todlfs_get_files:todlfs_list',\
          'pymqds_test_slogger=pymqdatastream.connectors.logger.pymqds_slogger:test'], },
          package_data = {'microrider':['data/*.DAT'],'':['VERSION'],'todl_gui':['connectors/todl/todl_config.yaml']},
          zip_safe=False)

else:
    print('pymqdatastream supports python > 3.4 only ... ')
