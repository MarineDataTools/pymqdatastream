from setuptools import setup
import os

import sys

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
          scripts = ['pymqdatastream/connectors/test/pymqds_rand.py',\
                     'pymqdatastream/connectors/test/pymqds_bare.py',\
                     'pymqdatastream/connectors/test/pymqds_bare_reqrep.py',\
                     'pymqdatastream/connectors/basic/pymqds_scan.py',\
                     'pymqdatastream/connectors/math_operator/pymqds_math_op.py',\
                     'pymqdatastream/connectors/test/pymqds_test.py',\
                     'pymqdatastream/connectors/nmea/pymqds_NMEA0183.py',\
                     'pymqdatastream/connectors/qt/pymqds_qtoverview.py',\
                     'pymqdatastream/connectors/qt/pymqds_qtshowdata.py',\
                     'pymqdatastream/connectors/logger/pymqds_slogger.py',\
                     'pymqdatastream/connectors/logger/pymqds_gui_slogger.py'],
          entry_points={ 'console_scripts': ['NMEA0183grabber=pymqdatastream.connectors.nmea.NMEA0183grabber:main',\
          'pymqds_query=pymqdatastream:query',\
          'pymqds_scan=pymqdatastream.connectors.basic.pymqds_scan:main',\
          'pymqds_qtshowdata=pymqdatastream.connectors.qt.pymqds_qtshowdata:main',\
          'pymqds_plotxy=pymqdatastream.connectors.pyqtgraph.pymqds_plotxy:main',\
          'pymqds_sam4log=pymqdatastream.connectors.sam4log.pymqds_sam4log:main',\
          'pymqds_gui_sam4log=pymqdatastream.connectors.sam4log.pymqds_gui_sam4log:main',\
          'pymqds_test_slogger=pymqdatastream.connectors.logger.pymqds_slogger:test'], },
          package_data = {'microrider':['data/*.DAT'],'':['VERSION']},
          zip_safe=False)

else:
    print('pymqdatastream supports python > 3.4 only ... ')
