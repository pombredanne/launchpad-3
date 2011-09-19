# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Scripts for starting a Python prompt with Launchpad initialized.

The scripts provide an interactive prompt with the Launchpad Storm classes,
all interface classes and the zope3 CA-fu at your fingertips, connected to
launchpad_dev or the database specified on the command line.
One uses Python, the other iPython.
"""

__metaclass__ = type
__all__ = ['python', 'ipython']

# This has setup.py scripts.  It is usually installed via buildout.
#

#
import os
import sys

from pytz import utc
import transaction

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.webapp import canonical_url

from lp.answers.model.question import Question
from lp.blueprints.model.specification import Specification
from lp.bugs.model.bug import Bug
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.registry.model.projectgroup import ProjectGroup
from lp.testing.factory import LaunchpadObjectFactory

from zope.interface.verify import verifyObject

import readline
import rlcompleter

# Bring in useful bits of Storm.
from storm.locals import *
from storm.expr import *
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR, SLAVE_FLAVOR, DEFAULT_FLAVOR)


def _get_locals():
    if len(sys.argv) > 1:
        dbuser = sys.argv[1]
    else:
        dbuser = None
    print 'execute_zcml_for_scripts()...'
    execute_zcml_for_scripts()
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
        proj = ProjectGroup.get(1)
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
