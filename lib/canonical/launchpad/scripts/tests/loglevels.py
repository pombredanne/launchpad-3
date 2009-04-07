# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Parse logging command line arguments and output some log messages.

Used by test_logger.txt.
"""

__metaclass__ = type
__all__ = []

# Fix path so imports work.
import sys, os, os.path
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir,
    ))

# Monkey patch time.gmtime to make our tests easier to read.
import time
def fake_gmtime(ignored_seconds):
    # 1985-12-21 13:45:55
    return (1985, 12, 21, 13, 45, 55, 5, 355, 0)
time.gmtime = fake_gmtime

from optparse import OptionParser

from canonical.launchpad.scripts.logger import *

parser = OptionParser()
logger_options(parser)

options, args = parser.parse_args()

if len(args) > 0:
    print "Args: %s" % repr(args)

log = logger(options, 'loglevels')

log.error("This is an error")
log.warn("This is a warning")
log.info("This is info")
log.debug("This is debug")
log.log(DEBUG2, "This is debug2")
log.log(DEBUG3, "This is debug3")
log.log(DEBUG4, "This is debug4")
log.log(DEBUG5, "This is debug5")
log.log(DEBUG6, "This is debug6")
log.log(DEBUG7, "This is debug7")
log.log(DEBUG8, "This is debug8")
log.log(DEBUG9, "This is debug9")

