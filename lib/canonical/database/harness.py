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
from canonical.lp import initZopeless
transactionmgr = initZopeless()

#
# get the database access classes ready
#
from canonical.launchpad.database import *

import readline
import rlcompleter
readline.parse_and_bind('tab: complete')

