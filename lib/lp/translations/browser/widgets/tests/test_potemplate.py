# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the POTemplate widgets."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )

from lp.app.errors import UnexpectedFormData
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.translations.browser.potemplate import IPOTemplateEditForm
from lp.translations.browser.widgets.potemplate import (
    POTemplateAdminSourcePackageNameWidget,
    POTemplateEditSourcePackageNameWidget,
    )
from lp.translations.interfaces.potemplate import IPOTemplate


class TestPOTemplateEditSourcePackageNameWidget(
    WithScenarios, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    scenarios = [
        ("spn_picker", {
            "features": {},
            "interface": IPOTemplate,
            }),
        ("dsp_picker", {
            "features": {u"disclosure.dsp_picker.enabled": u"on"},
            "interface": IPOTemplateEditForm,
            }),
        ]

    def setUp(self):
        super(TestPOTemplateEditSourcePackageNameWidget, self).setUp()
        if self.features:
            self.useFixture(FeatureFixture(self.features))

    def makeWidget(self, potemplate, form=None):
        field = self.interface["sourcepackagename"]
        bound_field = field.bind(potemplate)
        request = LaunchpadTestRequest(form=form)
        return POTemplateEditSourcePackageNameWidget(
            bound_field, bound_field.vocabulary, request)

    def test_productseries(self):
        potemplate = self.factory.makePOTemplate()
        widget = self.makeWidget(potemplate)
        self.assertIsNone(widget.getDistribution())
        self.assertEqual("", widget.distribution_name)

    def test_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        potemplate = self.factory.makePOTemplate(distroseries=distroseries)
        widget = self.makeWidget(potemplate)
        self.assertEqual(distroseries.distribution, widget.getDistribution())
        self.assertEqual(
            distroseries.distribution.name, widget.distribution_name)


class TestPOTemplateAdminSourcePackageNameWidget(
    WithScenarios, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    scenarios = [
        ("spn_picker", {
            "features": {},
            "interface": IPOTemplate,
            }),
        ("dsp_picker", {
            "features": {u"disclosure.dsp_picker.enabled": u"on"},
            "interface": IPOTemplateEditForm,
            }),
        ]

    def setUp(self):
        super(TestPOTemplateAdminSourcePackageNameWidget, self).setUp()
        if self.features:
            self.useFixture(FeatureFixture(self.features))

    def makeWidget(self, potemplate, form=None):
        field = self.interface["sourcepackagename"]
        bound_field = field.bind(potemplate)
        request = LaunchpadTestRequest(form=form)
        return POTemplateAdminSourcePackageNameWidget(
            bound_field, bound_field.vocabulary, request)

    def test_distroseries_id(self):
        potemplate = self.factory.makePOTemplate()
        distroseries = self.factory.makeDistroSeries()
        form = {
            "field.distroseries": "%s/%s" % (
                distroseries.distribution.name, distroseries.name),
            }
        widget = self.makeWidget(potemplate, form=form)
        self.assertEqual("field.distroseries", widget.distroseries_id)

    def test_getDistribution(self):
        potemplate = self.factory.makePOTemplate()
        distroseries = self.factory.makeDistroSeries()
        form = {
            "field.distroseries": "%s/%s" % (
                distroseries.distribution.name, distroseries.name),
            }
        widget = self.makeWidget(potemplate, form=form)
        self.assertEqual(distroseries.distribution, widget.getDistribution())

    def test_getDistribution_missing_field(self):
        distroseries = self.factory.makeDistroSeries()
        potemplate = self.factory.makePOTemplate(distroseries=distroseries)
        widget = self.makeWidget(potemplate, form={})
        self.assertEqual(distroseries.distribution, widget.getDistribution())

    def test_getDistribution_non_existent_distroseries(self):
        potemplate = self.factory.makePOTemplate()
        form = {"field.distroseries": "not-a-distribution/not-a-series"}
        self.assertRaises(
            UnexpectedFormData,
            lambda: (
                self.makeWidget(potemplate, form=form).getDistribution().name))


load_tests = load_tests_apply_scenarios
