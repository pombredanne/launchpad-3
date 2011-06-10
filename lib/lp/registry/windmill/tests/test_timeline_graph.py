# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for timeline graph widget."""

__metaclass__ = type
__all__ = []

import unittest

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase


class TestTimelineGraph(WindmillTestCase):
    """Test timeline graph widget."""

    layer = RegistryWindmillLayer
    suite_name = 'TimelineGraph'

    def test_timeline_graph(self):
        """Test timeline graph on /$project/+timeline-graph page."""

        self.client.open(
            url=u'%s/firefox/+timeline-graph'
                % RegistryWindmillLayer.base_url)
        self.client.waits.forElement(id=u'spinner', timeout=u'20000')
        self.client.waits.forElementProperty(
            id=u'spinner',
            option=u'style.display|none',
            timeout=u'8000')
        link_xpath = '//div/a[@href="/firefox/trunk"]'

        self.client.waits.forElement(xpath=link_xpath)

    def test_project_timeline_graph(self):
        """Test that the timeline graph loads on /$project page."""

        self.client.open(url=u'%s/firefox' % RegistryWindmillLayer.base_url)

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

        self.client.open(url=u'%s/firefox/trunk'
                        % RegistryWindmillLayer.base_url)

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

        self.client.open(url=u'%s/firefox/+series'
                        % RegistryWindmillLayer.base_url)

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
