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
                 'pymqdatastream/connectors/math_operator/pymqdatastream_math_operator.py',\
                 'pymqdatastream/connectors/test/pymqdatastream_test.py',\
                 'pymqdatastream/connectors/nmea/pymqdatastream_NMEA0183.py',\
                 'pymqdatastream/connectors/qt/pymqdatastream_qtoverview.py',\
                 'pymqdatastream/connectors/qt/pymqds_qtshowdata.py',\
                 'pymqdatastream/connectors/logger/pymqds_logger.py',\
                 'pymqdatastream/connectors/logger/pymqds_gui_logger.py',\
                 'pymqdatastream/connectors/rockland/microrider/pymqdatastream_uR_replay.py'],
      entry_points={ 'console_scripts': ['NMEA0183logger=pymqdatastream.connectors.nmea.NMEA0183grabber:main',\
      'pymqds_test_logger=pymqdatastream.connectors.logger.pymqds_logger:test'], },
      package_data = {'microrider':['data/*.DAT'],'':['VERSION']},
      zip_safe=False)
