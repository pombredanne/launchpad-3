#
# This is designed to be used as follows:
#
#   python -i harness.py
#
# At that point, you will have the Launchpad SQLObject classes, all interface
# classes and the zope3 CA-fu at your fingertips, connected to launchpad_dev
# or your LP_DBNAME environment variable (if you have one set).
#
import sys
sys.path.insert(0, '../sourcecode/zope/src/')
sys.path.insert(0, '../sourcecode/sqlobject/')
sys.path.insert(0, '../..')
sys.path.insert(0, '..')

from canonical.launchpad.scripts import execute_zcml_for_scripts
execute_zcml_for_scripts()

#
# setup connection to the db
#
from canonical.lp import initZopeless
transactionmgr = initZopeless()

#
# We don't really depend on everything from canonical.launchpad.database and
# canonical.launchpad.interfaces, but it's good to have this available in the
# namespace.
#
from canonical.launchpad.database import *
from canonical.launchpad.interfaces import *

import readline
import rlcompleter
readline.parse_and_bind('tab: complete')

