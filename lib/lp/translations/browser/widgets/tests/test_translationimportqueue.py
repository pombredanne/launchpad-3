# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the TranslationImportQueueEntry widget."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )

from lp.services.features.testing import FeatureFixture
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.translations.browser.translationimportqueue import (
    IEditTranslationImportQueueEntryDSP,
    )
from lp.translations.browser.widgets.translationimportqueue import (
    TranslationImportQueueEntrySourcePackageNameWidget,
    )
from lp.translations.interfaces.translationimportqueue import (
    IEditTranslationImportQueueEntry,
    )


class TestTranslationImportQueueEntrySourcePackageNameWidget(
    WithScenarios, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    scenarios = [
        ("spn_picker", {
            "features": {},
            "interface": IEditTranslationImportQueueEntry,
            }),
        ("dsp_picker", {
            "features": {u"disclosure.dsp_picker.enabled": u"on"},
            "interface": IEditTranslationImportQueueEntryDSP,
            }),
        ]

    def setUp(self):
        super(
            TestTranslationImportQueueEntrySourcePackageNameWidget,
            self).setUp()
        if self.features:
            self.useFixture(FeatureFixture(self.features))

    def makeWidget(self, entry, form=None):
        field = self.interface["sourcepackagename"]
        bound_field = field.bind(entry)
        request = LaunchpadTestRequest(form=form)
        return TranslationImportQueueEntrySourcePackageNameWidget(
            bound_field, bound_field.vocabulary, request)

    def test_productseries(self):
        productseries = self.factory.makeProductSeries()
        entry = self.factory.makeTranslationImportQueueEntry(
            productseries=productseries)
        widget = self.makeWidget(entry)
        self.assertIsNone(widget.getDistribution())
        self.assertEqual("", widget.distribution_name)

    def test_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        entry = self.factory.makeTranslationImportQueueEntry(
            distroseries=distroseries)
        widget = self.makeWidget(entry)
        self.assertEqual(distroseries.distribution, widget.getDistribution())
        self.assertEqual(
            distroseries.distribution.name, widget.distribution_name)


load_tests = load_tests_apply_scenarios
