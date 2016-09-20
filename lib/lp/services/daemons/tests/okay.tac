# Copyright 2011-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
This TAC is used for the TacTestSetupTestCase.test_pidForNotRunningProcess
test case in test_tachandler.py.  It simply starts up correctly.
"""

__metaclass__ = type

from twisted.application import service
from zope.component import getUtility

from lp.services.database.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.services.daemons import readyservice
from lp.services.scripts import execute_zcml_for_scripts


execute_zcml_for_scripts()

application = service.Application('Okay')

# Service that announces when the daemon is ready
readyservice.ReadyService().setServiceParent(application)

# Do some trivial database work that will show up in an SQL debug log.
store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
store.execute("SELECT 1").get_one()
