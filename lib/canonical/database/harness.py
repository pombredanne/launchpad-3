#
# This is designed to be used as follows:
#
#   python -i harness.py
#
# At that point, you will have the Launchpad SQLObject classes
# at your fingertips, connected to launchpad_test
#
import sys
sys.path.append('../sourcecode/zope/src/')
sys.path.append('../sourcecode/sqlobject/')
sys.path.append('../..')
sys.path.append('..')

#
# setup connection to the db
#
from sqlobject import connectionForURI
__connection__ = connectionForURI('postgres:///launchpad_test')
from canonical.database.sqlbase import *
SQLBase.initZopeless(__connection__)

#
# get the database access classes ready
#
import canonical.launchpad.database



