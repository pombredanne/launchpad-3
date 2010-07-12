# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.testing.doctestunit import DocTestSuite
from zope.component import getUtility
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.testing.layers import LaunchpadFunctionalLayer

def setUp(test):
    test.globs['getUtility'] = getUtility
    login(ANONYMOUS)

def test_suite():
    suite = DocTestSuite('lp.registry.model.projectgroup', setUp=setUp)
    suite.layer = LaunchpadFunctionalLayer
    return suite
