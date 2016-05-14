pymqdatastream
==============

Pymqdatastream (Python/ZeroMQ/Datastream) is a ZeroMQ based software
to distribute and process realtime sensor data.

Pymqdatastream intends to be a software tool which makes it simple to
distribute manifold realtime sensor by providing a framework to
publisch/subscribe datastreams. The network transport relies on the 
`ZeroMQ <http://www.zeromq.org>`_ library. The individual sensors have to be
"connected" by writing a connector which is reading the sensor data
and using a pymqdatastream object to distribute it. The software
focusses on marine sensors as GPS, echo sounder and scientific data as
conductivity, temperature and depth data but is not limited to this
purpose.
