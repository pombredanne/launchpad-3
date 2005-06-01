#
# This is designed to be used as follows:
#
#   python -i harness.py
#
# At that point, you will have the Launchpad SQLObject classes
# at your fingertips, connected to launchpad_test
#
import sys
sys.path.insert(0, '../sourcecode/zope/src/')
sys.path.insert(0, '../sourcecode/sqlobject/')
sys.path.insert(0, '../..')
sys.path.insert(0, '..')

#
# setup connection to the db
#
from canonical.lp import initZopeless
transactionmgr = initZopeless()

#
# get the database access classes ready
#
from canonical.launchpad.database import *

import readline
import rlcompleter
readline.parse_and_bind('tab: complete')

