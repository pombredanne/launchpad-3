#! /usr/bin/python2.4 -i

# This is designed to be used as follows:
#
#   python -i harness.py
#
# At that point, you will have the Launchpad Storm classes, all interface
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
    dbuser = None

import transaction

from zope.component import getUtility
from zope.configuration import xmlconfig

from canonical.launchpad.scripts import execute_zcml_for_scripts

print 'execute_zcml_for_scripts()...'
execute_zcml_for_scripts()
print 'xmlconfig.file()...'
xmlconfig.file('script.zcml', execute=True)

#
# setup connection to the db
#
#from canonical.lp import initZopeless
#transactionmgr = initZopeless(dbuser=dbuser)

def switch_db_user(dbuser, commit_first=True):
    global transactionmgr
    if commit_first:
        transactionmgr.commit()
    else:
        transactionmgr.abort()
    transactionmgr.uninstall()
    transactionmgr = initZopeless(dbuser=dbuser)

#
# We don't really depend on everything from canonical.launchpad.database and
# canonical.launchpad.interfaces, but it's good to have this available in the
# namespace.
#
# pylint: disable-msg=W0614,W0401
from canonical.launchpad.database import *
from canonical.launchpad.interfaces import *
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.mail import create_mail_for_directoryMailBox
from canonical.launchpad.testing.systemdocs import (
    create_initialized_view, create_view)

from zope.interface.verify import verifyObject

import readline
import rlcompleter
readline.parse_and_bind('tab: complete')

# Mimic the real interactive interpreter's loading of any $PYTHONSTARTUP file.
print 'Reading $PYTHONSTARTUP...'
startup = os.environ.get('PYTHONSTARTUP')
if startup:
    execfile(startup)

# Bring in useful bits of Storm.
from storm.locals import *
from storm.expr import *
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, AUTH_STORE, MASTER_FLAVOR,
        SLAVE_FLAVOR, DEFAULT_FLAVOR)

print 'Initializing storm...'
store_selector = getUtility(IStoreSelector)
store = store_selector.get(MAIN_STORE, MASTER_FLAVOR)

# Let's get a few handy objects going.
if dbuser == 'launchpad':
    print 'Creating a few handy objects...'
    d = Distribution.get(1)
    p = Person.get(1)
    ds = DistroSeries.get(1)
    prod = Product.get(1)
    proj = Project.get(1)
    b2 = Bug.get(2)
    b1 = Bug.get(1)
    s = Specification.get(1)
    q = Question.get(1)

# Having a factory instance is handy.
print 'Creating the factory...'
factory = LaunchpadObjectFactory()
