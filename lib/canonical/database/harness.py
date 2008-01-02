#! /usr/bin/python2.4 -i

# This is designed to be used as follows:
#
#   python -i harness.py
#
# At that point, you will have the Launchpad SQLObject classes, all interface
# classes and the zope3 CA-fu at your fingertips, connected to launchpad_dev
# or your LP_DBNAME environment variable (if you have one set).
#
import os
import sys
#sys.path.insert(0, '../sourcecode/zope/src/')
#sys.path.insert(0, '../sourcecode/sqlobject/')
sys.path.insert(0, '../..')
#sys.path.insert(0, '..')

if len(sys.argv) > 1:
    dbuser = sys.argv[1]
else:
    dbuser = 'launchpad'

from zope.component import getUtility
from canonical.launchpad.scripts import execute_zcml_for_scripts
execute_zcml_for_scripts()

#
# setup connection to the db
#
from canonical.lp import initZopeless
transactionmgr = initZopeless(dbuser=dbuser)

#
# We don't really depend on everything from canonical.launchpad.database and
# canonical.launchpad.interfaces, but it's good to have this available in the
# namespace.
#
from canonical.launchpad.database import *
from canonical.launchpad.interfaces import *

from zope.interface.verify import verifyObject

import readline
import rlcompleter
readline.parse_and_bind('tab: complete')

# Mimic the real interactive interpreter's loading of any $PYTHONSTARTUP file.
startup = os.environ.get('PYTHONSTARTUP')
if startup:
    execfile(startup)


#
# Let's get a few handy objects going
#
if dbuser == 'launchpad':
    d = Distribution.get(1)
    p = Person.get(1)
    ds = DistroSeries.get(1)
    prod = Product.get(1)
    proj = Project.get(1)
    b2 = Bug.get(2)
    b1 = Bug.get(1)
    s = Specification.get(1)
    q = Question.get(1)
