# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

import os
import logging
import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.signon.dbpolicy import SSODatabasePolicy
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import DatabaseFunctionalLayer


here = os.path.dirname(os.path.realpath(__file__))


def setUpWithSSODBPolicy(test):
    setUp(test)
    getUtility(IStoreSelector).push(SSODatabasePolicy())


def tearDownWithSSODBPolicy(test):
    tearDown(test)
    getUtility(IStoreSelector).pop()


def test_suite():
    filenames = sorted(filename for filename in os.listdir(here)
                       if filename.lower().endswith('.txt'))
    suite = unittest.TestSuite()
    for filename in filenames:
        if filename == 'openid-fetcher.txt':
            test = LayeredDocFileSuite(
                filename, stdout_logging=False,
                layer=DatabaseFunctionalLayer)
        else:
            test = LayeredDocFileSuite(
                filename, setUp=setUp, tearDown=tearDown,
                layer=DatabaseFunctionalLayer,
                stdout_logging_level=logging.WARNING)
        suite.addTest(test)
    # Run account.txt using the SSODatabasePolicy to make sure the operations
    # on IAccount can be done from the SSO too.
    suite.addTest(LayeredDocFileSuite(
        '../../launchpad/doc/account.txt', setUp=setUpWithSSODBPolicy,
        tearDown=tearDownWithSSODBPolicy, layer=DatabaseFunctionalLayer))
    return suite
