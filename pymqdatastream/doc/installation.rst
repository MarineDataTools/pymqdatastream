Pymqdatastream installation
===========================


Debian
------

To be written.

Windows 10
----------

Developer
_________

* Download git for Windows `here <https://git-scm.com/download/win>`_ .
* Clone the pymqdatastream source code by pasting the command into the
  git bash (Version used here: 2.14.1-64bit):
  
  .. code:: bash
   
     git clone https://github.com/MarineDataTools/pymqdatastream.git pymqdatastream.git
     cd pymqdatastrea.git

   

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


