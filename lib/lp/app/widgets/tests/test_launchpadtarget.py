# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import doctest

from zope.interface import Interface

from lazr.restful.fields import Reference

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.launchpadtarget import LaunchpadTargetWidget
from lp.registry.vocabularies import (
    DistributionVocabulary,
    DistributionSourcePackageVocabulary,
    ProductVocabulary,
    )
from lp.soyuz.model.binaryandsourcepackagename import (
    BinaryAndSourcePackageNameVocabulary,
    )
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

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are setup and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsInstance(
            self.widget.distribution_widget.context.vocabulary,
            DistributionVocabulary)
        self.assertIsInstance(
            self.widget.product_widget.context.vocabulary,
            ProductVocabulary)
        self.assertIsInstance(
            self.widget.package_widget.context.vocabulary,
            BinaryAndSourcePackageNameVocabulary)

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were setup.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIs(None, getattr(self.widget, 'distribution_widget', None))
        self.assertIs(None, getattr(self.widget, 'package_widget', None))
        self.assertIs(None, getattr(self.widget, 'product_widget', None))
