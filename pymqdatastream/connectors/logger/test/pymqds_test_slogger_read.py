#!/usr/bin/env python3
import pymqdatastream
import logging

slogfile = pymqdatastream.slogger.LoggerFile('test.ubjson','rb',logging_level = logging.DEBUG)
slogfile.read()


print(slogfile.loggerstreams[-1].data)
