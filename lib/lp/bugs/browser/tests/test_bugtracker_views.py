# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugTracker views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtracker import IBugTrackerSet
from lp.registry.interfaces.person import IPersonSet
from lp.testing import (
    login,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view
from lp.testing.matchers import IsConfiguredBatchNavigator
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestBugTrackerSetView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_trackers_are_batch_navigators(self):
        trackers = getUtility(IBugTrackerSet)
        view = create_initialized_view(trackers, name='+index')
        matcher = IsConfiguredBatchNavigator('tracker', 'trackers')
        self.assertThat(view.active_trackers, matcher)
        self.assertThat(view.inactive_trackers, matcher)

    def test_page_is_batched(self):
        active_tracker1 = self.factory.makeBugTracker()
        active_tracker2 = self.factory.makeBugTracker()
        inactive_tracker1 = self.factory.makeBugTracker()
        inactive_tracker2 = self.factory.makeBugTracker()
        admin = getUtility(IPersonSet).find(ADMIN_EMAIL).any()
        with person_logged_in(admin):
            inactive_tracker1.active = False
            inactive_tracker2.active = False
        trackers = getUtility(IBugTrackerSet)
        url = (canonical_url(trackers) +
            "/+index?active_batch=1&inactive_batch=1")
        browser = self.getUserBrowser(url)
        content = browser.contents
        # XXX RobertCollns 20100919 bug=642504. The support for multiple batches
        # isn't complete and the id for the nav links gets duplicated.
        #self.assertEqual('next',
        #    find_tag_by_id(content, 'upper-batch-nav-batchnav-next')['class'])
        #self.assertEqual('next',
        #    find_tag_by_id(content, 'lower-batch-nav-batchnav-next')['class'])
        # Instead we check the string appears.
        self.assertTrue('upper-batch-nav-batchnav-next' in content)

