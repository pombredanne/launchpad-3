# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=F0401

"""Unit tests for SourceListEntriesView."""

__metaclass__ = type
__all__ = ['TestBranchView', 'test_suite']

import unittest

from lp.testing import TestCaseWithFactory

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadFunctionalLayer

from lp.soyuz.browser.sourceslist import (
    SourcesListEntries, SourcesListEntriesView)

class TestDefaultSelectedSeries(TestCaseWithFactory):
    """Ensure that default selected series set from user-agent."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.distribution = self.factory.makeDistribution(name='ibuntu')
        self.series = [
            self.factory.makeDistroRelease(name="feasty", version='9.04'),
            self.factory.makeDistroRelease(name="getsy", version='10.09'),
            self.factory.makeDistroRelease(name="ibix", version='11.04'),
        ]
        self.entries = SourcesListEntries(
            self.distribution, 'http://example.com/my/archive',
            self.series)

    def testDefaultToUserAgentSeries(self):
        # The distroseries version found in the user-agent header will
        # be selected by default.

        # Ubuntu version 10.09 in the user-agent should display as getsy
        view = SourcesListEntriesView(
            self.entries,
            LaunchpadTestRequest(
                HTTP_USER_AGENT='Mozilla/5.0 '
                                '(X11; U; Linux i686; en-US; rv:1.9.0.10) '
                                'Gecko/2009042523 Ubuntu/10.09 (whatever) '
                                'Firefox/3.0.10'))
        view.initialize()

        self.assertEqual(u'getsy', view.default_series_name)

        # Ubuntu version 9.04 in the user-agent should display as feasty
        view = SourcesListEntriesView(
            self.entries,
            LaunchpadTestRequest(
                HTTP_USER_AGENT='Mozilla/5.0 '
                                '(X11; U; Linux i686; en-US; rv:1.9.0.10) '
                                'Gecko/2009042523 Ubuntu/9.04 (whatever) '
                                'Firefox/3.0.10'))
        view.initialize()

        self.assertEqual(u'feasty', view.default_series_name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
