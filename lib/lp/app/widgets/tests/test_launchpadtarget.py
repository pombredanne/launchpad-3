# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import doctest

from zope.interface import Interface

from lazr.restful.fields import Reference

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.launchpadtarget import LaunchpadTargetWidget
from lp.testing import TestCaseWithFactory


class LaunchpadTargetWidgetTestCase(TestCaseWithFactory):
    """Test the LaunchpadTargetWidget class."""

    layer = DatabaseFunctionalLayer
    doctest_opts = (
        doctest.NORMALIZE_WHITESPACE | doctest.REPORT_NDIFF |
        doctest.ELLIPSIS)

    def setUp(self):
        super(LaunchpadTargetWidgetTestCase, self).setUp()
        self.distribution, self.dsp = self.factory.makeDSPCache(
            distro_name='fnord', package_name='snarf')
        self.project = self.factory.makeProduct('pting')
        request = LaunchpadTestRequest()
        field = Reference(schema=Interface, title=u'target', required=True)
        field = field.bind(object())
        self.widget = LaunchpadTargetWidget(field, request)

    def test_template(self):
        # The render template is setup.
        self.assertTrue(
            self.widget.template.filename.endswith('launchpad-target.pt'),
            'Template was not setup.')

    def test_default_option(self):
        self.assertEqual('package', self.widget.default_option)
