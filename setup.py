from setuptools import setup
import os

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
                 'pymqdatastream/connectors/pyqtgraph/pymqds_plotxy.py',\
                 'pymqdatastream/connectors/basic/pymqds_scan.py',\
                 'pymqdatastream/connectors/sam4log/pymqds_sam4log.py',\
                 'pymqdatastream/connectors/sam4log/pymqds_gui_sam4log.py',\
                 'pymqdatastream/connectors/math_operator/pymqds_math_op.py',\
                 'pymqdatastream/connectors/test/pymqdatastream_test.py',\
                 'pymqdatastream/connectors/nmea/pymqds_NMEA0183.py',\
                 'pymqdatastream/connectors/qt/pymqds_qtoverview.py',\
                 'pymqdatastream/connectors/qt/pymqds_qtshowdata.py',\
                 'pymqdatastream/connectors/logger/pymqds_slogger.py',\
                 'pymqdatastream/connectors/logger/pymqds_gui_slogger.py'],
      entry_points={ 'console_scripts': ['NMEA0183logger=pymqdatastream.connectors.nmea.NMEA0183grabber:main',\
      'pymqds_test_slogger=pymqdatastream.connectors.logger.pymqds_slogger:test'], },
      package_data = {'microrider':['data/*.DAT'],'':['VERSION']},
      zip_safe=False)
