# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from windmill.authoring import WindmillTestClient

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import TestCaseWithFactory

class TestTimelineGraph(TestCaseWithFactory):

    layer = RegistryWindmillLayer

    def setUp(self):
        self.client = WindmillTestClient('TimelineGraph')

    def test_timeline_graph(self):
        """Test timeline graph on /$project/+timeline-graph page."""

        self.client.open(
            url=u'http://launchpad.dev:8085/firefox/+timeline-graph')
        self.client.waits.forElement(id=u'spinner', timeout=u'20000')
        self.client.waits.forElementProperty(
            id=u'spinner',
            option=u'style.display|none',
            timeout=u'8000')
        link_xpath = '//div/a[@href="/firefox/trunk"]'

        # waits.forElement() is called multiple times because there
        # were sporadic errors where waits.forElement() would succeed but
        # the following assertNode() would fail 5% of the time.
        for i in range(5):
            self.client.waits.forElement(xpath=link_xpath)
        self.client.asserts.assertNode(xpath=link_xpath)

    def test_project_timeline_graph(self):
        """Test that the timeline graph loads on /$project page."""

        self.client.open(url=u'http://launchpad.dev:8085/firefox')

        self.client.waits.forElementProperty(
            id=u'timeline-loading',
            option=u'style.display|none',
            timeout=u'20000')
        self.client.waits.forElementProperty(
            id=u'timeline-iframe',
            option=u'style.display|block',
            timeout=u'8000')

    def test_series_timeline_graph(self):
        """Test that the timeline graph loads on /$project/$series page."""

        self.client.open(url=u'http://launchpad.dev:8085/firefox/trunk')

        self.client.waits.forElementProperty(
            id=u'timeline-iframe',
            option=u'style.display|block',
            timeout=u'8000')
        self.client.waits.forElement(id=u'timeline-loading', timeout=u'20000')

        self.client.waits.forElementProperty(
            id=u'timeline-loading',
            option=u'style.display|none')

    def test_all_series_timeline_graph(self):
        """Test that the timeline graph loads on /$project/+series page."""

        self.client.open(url=u'http://launchpad.dev:8085/firefox/+series')

        self.client.waits.forElement(
            id=u'timeline-loading',
            option=u'style.display|none',
            timeout=u'20000')
        self.client.waits.forElementProperty(
            id=u'timeline-iframe',
            option=u'style.display|block',
            timeout=u'8000')

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
