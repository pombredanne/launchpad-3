# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.testing.doctestunit import DocTestSuite
from zope.component import getUtility
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestSetup
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.testing import layers

def setUp(test):
    test.globs['getUtility'] = getUtility
    login(ANONYMOUS)

def test_suite():
    suite = DocTestSuite('canonical.launchpad.database.project', setUp=setUp)
    suite.layer = layers.LaunchpadFunctional
    return suite
