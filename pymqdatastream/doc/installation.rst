Pymqdatastream installation
===========================


Linux
-----


Debian Stretch (9) ADM64
________________________

On a freshly installed Debian stretch install the following packages:

* python3
* python3-setuptools
* python3-pip
* python3-numpy
* python3-ubjson
* python3-zmq
* python3-qtpy
* python3-serial
* python3-yaml
* python3-nmea2
* python3-netcdf4

The `COBS <https://pypi.python.org/pypi/cobs/>`_ package needs to be
installed using the pip installer. The following command install
pymqdatastream for one user in develop mode.

.. code:: bash

   pip3 install cobs
   
   git clone https://github.com/MarineDataTools/pymqdatastream.git pymqdatastream.git
   cd pymqdatastream.git
   python3 setup.py develop --user


Windows 10
----------

Developer
_________

* Download git for Windows `here <https://git-scm.com/download/win>`_ .
* Clone the pymqdatastream source code by pasting the command into the
  git bash (Version used here: 2.14.1-64bit):
  
  .. code:: bash
   
     git clone https://github.com/MarineDataTools/pymqdatastream.git pymqdatastream.git
     cd pymqdatastream.git

   

* `Download <https://www.anaconda.com/download/#download>`_ and
  install python using the Anaconda package (Version used here 4.4.0, 64 bit with python 3.6)

  * Install the pyserial package using the Anaconda Navigator
  * Install py-ubjson, cobs and pynmea2 with the Anaconda command prompt

    .. code:: bash
	      
       conda install -c conda-forge py-ubjson
       pip install cobs
       pip install -i https://pypi.anaconda.org/pypi/simple pynmea2
       
  * Open the Anaconda prompt, go to the cloned pymqdatastream.git
    directory and install it by

    .. code:: bash
   
       python setup.py develop


Testing
-------

Test the installation by creating a random datastream and displaying
the data with the Qt interface:


.. code:: bash
	      
   pymqds_rand &
   pymqds_qtshowdata


