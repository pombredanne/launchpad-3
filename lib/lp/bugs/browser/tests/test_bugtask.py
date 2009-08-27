# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import unittest

from zope.testing.doctest import DocTestSuite

from canonical.launchpad.ftests import login
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer

from lp.bugs.browser import bugtask
from lp.bugs.browser.bugtask import BugTasksAndNominationsView
from lp.testing import TestCaseWithFactory


class TestBugTasksAndNominationsView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugTasksAndNominationsView, self).setUp()
        login('foo.bar@canonical.com')
        self.bug = self.factory.makeBug()
        self.view = BugTasksAndNominationsView(self.bug, None)

    def test_current_user_affected_status(self):
        self.failUnlessEqual(
            None, self.view.current_user_affected_status)
        self.view.context.markUserAffected(self.view.user, True)
        self.failUnlessEqual(
            True, self.view.current_user_affected_status)
        self.view.context.markUserAffected(self.view.user, False)
        self.failUnlessEqual(
            False, self.view.current_user_affected_status)

    def test_current_user_affected_js_status(self):
        self.failUnlessEqual(
            'null', self.view.current_user_affected_js_status)
        self.view.context.markUserAffected(self.view.user, True)
        self.failUnlessEqual(
            'true', self.view.current_user_affected_js_status)
        self.view.context.markUserAffected(self.view.user, False)
        self.failUnlessEqual(
            'false', self.view.current_user_affected_js_status)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBugTasksAndNominationsView))
    suite.addTest(DocTestSuite(bugtask))
    suite.addTest(LayeredDocFileSuite(
        'bugtask-target-link-titles.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
