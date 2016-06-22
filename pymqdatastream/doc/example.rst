Example usage
=============


Pupstream/substream example
---------------------------

This example (connectors/test/pymqds_bare.py) creates a datastream object and
two "substream" streams one sending and one receiving the data


.. include:: ../connectors/test/pymqds_bare.py
   :literal:



reqstream/repstream example
---------------------------

Here two datastreams with a request/reply pattern are shown. Note that
you have to write your own "process_request" function.
  



            



