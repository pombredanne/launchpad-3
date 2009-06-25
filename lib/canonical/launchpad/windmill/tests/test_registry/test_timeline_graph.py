# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


def test_timeline_graph():
    """Test that the timeline graph loads."""

    client = WindmillTestClient('TimelineGraph')
    client.open(url=u'http://launchpad.dev:8085/firefox')

    client.waits.forElement(id=u'timeline-loading', timeout=u'20000')
    client.waits.forElementProperty(
        id=u'timeline-iframe',
        option=u'style.display|block',
        timeout=u'8000')
    client.asserts.assertProperty(
        id=u'timeline-loading',
        validator=u'style.display|none')

    client.open(url=u'http://launchpad.dev:8085/firefox/+timeline-graph')
    client.waits.forElement(id=u'spinner', timeout=u'20000')
    client.waits.forElementProperty(
        id=u'spinner',
        option=u'style.display|none',
        timeout=u'8000')
    client.asserts.assertNode(xpath='//div/a[@href="/firefox/trunk"]')
