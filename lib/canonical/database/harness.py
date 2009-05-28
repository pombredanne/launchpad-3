# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Scripts for starting a Python prompt with Launchpad initialized.

The scripts provide an interactive prompt with the Launchpad Storm classes,
all interface classes and the zope3 CA-fu at your fingertips, connected to
launchpad_dev or your LP_DBNAME environment variable (if you have one set).
One uses Python, the other iPython.
"""

__metaclass__ = type
__all__ = ['python', 'ipython']

# This has setup.py scripts.  It is usually installed via buildout.
#

#
import os
import sys

import transaction

from zope.component import getUtility
from zope.configuration import xmlconfig

from canonical.launchpad.scripts import execute_zcml_for_scripts

#
# We don't really depend on everything from canonical.launchpad.database and
# canonical.launchpad.interfaces, but it's good to have this available in the
# namespace.
#
# pylint: disable-msg=W0614,W0401
from canonical.launchpad.database import *
from canonical.launchpad.interfaces import *
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.launchpad.testing.mail import create_mail_for_directoryMailBox
from canonical.launchpad.testing.systemdocs import (
    create_initialized_view, create_view)

from zope.interface.verify import verifyObject

import readline
import rlcompleter

# Bring in useful bits of Storm.
from storm.locals import *
from storm.expr import *
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, AUTH_STORE, MASTER_FLAVOR,
        SLAVE_FLAVOR, DEFAULT_FLAVOR)


def switch_db_user(dbuser, commit_first=True):
    global transactionmgr
    if commit_first:
        transactionmgr.commit()
    else:
        transactionmgr.abort()
    transactionmgr.uninstall()
    transactionmgr = initZopeless(dbuser=dbuser)


def _get_locals():
    if len(sys.argv) > 1:
        dbuser = sys.argv[1]
    else:
        dbuser = None
    print 'execute_zcml_for_scripts()...'
    execute_zcml_for_scripts()
    print 'xmlconfig.file()...'
    xmlconfig.file('script.zcml', execute=True)
    readline.parse_and_bind('tab: complete')
    # Mimic the real interactive interpreter's loading of any $PYTHONSTARTUP file.
    print 'Reading $PYTHONSTARTUP...'
    startup = os.environ.get('PYTHONSTARTUP')
    if startup:
        execfile(startup)
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
    res = {}
    res.update(locals())
    res.update(globals())
    del res['_get_locals']
    return res


def python():
    import code
    code.interact(banner='', local=_get_locals())


def ipython():
    import IPython.ipapi
    IPython.ipapi.launch_new_instance(_get_locals())
