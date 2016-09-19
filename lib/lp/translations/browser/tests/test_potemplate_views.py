# Copyright 2011-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module doc."""

__metaclass__ = type

from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )

from lp.services.features.testing import FeatureFixture
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view
from lp.translations.browser.potemplate import (
    POTemplateAdminView,
    POTemplateEditView,
    )


class TestPOTemplateEditViewValidation(WithScenarios, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    scenarios = [
        ("spn_picker", {"features": {}}),
        ("dsp_picker", {
            "features": {u"disclosure.dsp_picker.enabled": u"on"},
            }),
        ]

    def setUp(self):
        super(TestPOTemplateEditViewValidation, self).setUp()
        if self.features:
            self.useFixture(FeatureFixture(self.features))

    def _makeData(self, potemplate, **kwargs):
        """Create form data for the given template with some changed values.

        The attributes are only those considered by the validate method.
        """
        attributes = [
            'distroseries', 'sourcepackagename', 'productseries',
            'name', 'translation_domain']
        data = dict(
            [(name, getattr(potemplate, name)) for name in attributes])
        data.update(**kwargs)
        return data

    def test_field_names_productseries(self):
        # A product series template has one set of field names that include
        # the template name.
        potemplate = self.factory.makePOTemplate()
        view = POTemplateEditView(potemplate, LaunchpadTestRequest())
        self.assertContentEqual(
            ['name', 'translation_domain', 'description', 'priority',
             'path', 'iscurrent', 'owner'],
            view.field_names)

    def test_field_names_sourcepackage(self):
        # A sourcepackage template has two more fields compared to the
        # product series templates.
        sourcepackage = self.factory.makeSourcePackage()
        potemplate = self.factory.makePOTemplate(
            distroseries=sourcepackage.distroseries,
            sourcepackagename=sourcepackage.sourcepackagename)
        view = POTemplateEditView(potemplate, LaunchpadTestRequest())
        self.assertContentEqual(
            ['name', 'translation_domain', 'description', 'priority',
             'path', 'iscurrent', 'sourcepackagename', 'languagepack'],
            view.field_names)

    def test_detects_invalid_names(self):
        # A template name must be satisfying the valid_name constraint.
        invalid_name = 'name!'
        potemplate = self.factory.makePOTemplate()
        data = self._makeData(potemplate, name=invalid_name)
        view = POTemplateEditView(potemplate, LaunchpadTestRequest())
        view.validate(data)
        self.assertEqual(
            [html_escape(
                u'Template name can only start with lowercase letters a-z '
                u'or digits 0-9, and other than those characters, can only '
                u'contain "-", "+" and "." characters.')],
            view.errors)

    def test_detects_name_clash_on_name_change(self):
        # A template name may not already be used.
        existing_name = self.factory.getUniqueString()
        existing_potemplate = self.factory.makePOTemplate(name=existing_name)
        series = existing_potemplate.productseries
        potemplate = self.factory.makePOTemplate(productseries=series)

        view = POTemplateEditView(potemplate, LaunchpadTestRequest())
        data = self._makeData(potemplate, name=existing_name)
        view.validate(data)
        self.assertEqual([u'Name is already in use.'], view.errors)

    def test_detects_domain_clash_on_domain_change(self):
        # A translation domain may not already be used.
        existing_domain = self.factory.getUniqueString()
        existing_potemplate = self.factory.makePOTemplate(
            translation_domain=existing_domain)
        series = existing_potemplate.productseries
        potemplate = self.factory.makePOTemplate(productseries=series)

        view = POTemplateEditView(potemplate, LaunchpadTestRequest())
        data = self._makeData(potemplate, translation_domain=existing_domain)
        view.validate(data)
        self.assertEqual([u'Domain is already in use.'], view.errors)

    def test_detects_name_clash_on_sourcepackage_change(self):
        # Detect changing to a source package that already has a template of
        # the same name.
        sourcepackage = self.factory.makeSourcePackage()
        existing_potemplate = self.factory.makePOTemplate(
            sourcepackage=sourcepackage)
        potemplate = self.factory.makePOTemplate(
            distroseries=sourcepackage.distroseries,
            name=existing_potemplate.name)

        view = POTemplateEditView(potemplate, LaunchpadTestRequest())
        data = self._makeData(
            potemplate, sourcepackagename=sourcepackage.sourcepackagename)
        view.validate(data)
        self.assertEqual(
            [u'Source package already has a template with that same name.'],
            view.errors)

    def test_detects_domain_clash_on_sourcepackage_change(self):
        # Detect changing to a source package that already has a template with
        # the same translation domain.
        sourcepackage = self.factory.makeSourcePackage()
        existing_potemplate = self.factory.makePOTemplate(
            sourcepackage=sourcepackage)
        potemplate = self.factory.makePOTemplate(
            distroseries=sourcepackage.distroseries,
            translation_domain=existing_potemplate.translation_domain)

        view = POTemplateEditView(potemplate, LaunchpadTestRequest())
        data = self._makeData(
            potemplate, sourcepackagename=sourcepackage.sourcepackagename)
        view.validate(data)
        self.assertEqual(
            [u'Source package already has a template with that same domain.'],
            view.errors)

    def test_change_sourcepackage(self):
        # Changing the source package is honoured.
        distroseries = self.factory.makeDistroSeries()
        potemplate = self.factory.makePOTemplate(distroseries=distroseries)
        dsp = self.factory.makeDSPCache(distroseries=distroseries)
        form = {
            'field.name': potemplate.name,
            'field.distroseries': distroseries.name,
            'field.sourcepackagename': dsp.sourcepackagename.name,
            'field.actions.change': 'Change',
            }
        with celebrity_logged_in('rosetta_experts'):
            view = create_initialized_view(potemplate, '+edit', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(
            dsp.sourcepackagename.name, potemplate.sourcepackagename.name)


class TestPOTemplateAdminViewValidation(TestPOTemplateEditViewValidation):

    def test_detects_name_clash_on_productseries_change(self):
        # Detect changing to a productseries that already has a template of
        # the same name.
        template_name = self.factory.getUniqueString()
        existing_potemplate = self.factory.makePOTemplate(name=template_name)
        new_series = existing_potemplate.productseries
        potemplate = self.factory.makePOTemplate(name=template_name)

        view = POTemplateAdminView(potemplate, LaunchpadTestRequest())
        data = self._makeData(potemplate, productseries=new_series)
        view.validate(data)
        self.assertEqual(
            [u'Series already has a template with that same name.'],
            view.errors)

    def test_detects_domain_clash_on_productseries_change(self):
        # Detect changing to a productseries that already has a template with
        # the same translation domain.
        translation_domain = self.factory.getUniqueString()
        existing_potemplate = self.factory.makePOTemplate(
            translation_domain=translation_domain)
        new_series = existing_potemplate.productseries
        potemplate = self.factory.makePOTemplate(
            translation_domain=translation_domain)

        view = POTemplateAdminView(potemplate, LaunchpadTestRequest())
        data = self._makeData(potemplate, productseries=new_series)
        view.validate(data)
        self.assertEqual(
            [u'Series already has a template with that same domain.'],
            view.errors)

    def test_detects_no_sourcepackage_or_productseries(self):
        # Detect if no source package or productseries was selected.
        potemplate = self.factory.makePOTemplate()

        view = POTemplateAdminView(potemplate, LaunchpadTestRequest())
        data = self._makeData(
            potemplate,
            distroseries=None, sourcepackagename=None, productseries=None)
        view.validate(data)
        self.assertEqual(
            [u'Choose either a distribution release series or a project '
             u'release series.'], view.errors)

    def test_detects_sourcepackage_and_productseries(self):
        # Detect if no source package or productseries was selected.
        potemplate = self.factory.makePOTemplate()
        sourcepackage = self.factory.makeSourcePackage()

        view = POTemplateAdminView(potemplate, LaunchpadTestRequest())
        data = self._makeData(
            potemplate,
            distroseries=sourcepackage.distroseries,
            sourcepackagename=sourcepackage.sourcepackagename,
            productseries=potemplate.productseries)
        view.validate(data)
        self.assertEqual(
            [u'Choose a distribution release series or a project '
             u'release series, but not both.'], view.errors)

    def test_change_from_sourcepackage(self):
        # Changing the source package the template comes from is honoured.
        distroseries = self.factory.makeDistroSeries()
        dsp = self.factory.makeDSPCache(distroseries=distroseries)
        potemplate = self.factory.makePOTemplate(
            distroseries=distroseries, sourcepackagename=dsp.sourcepackagename)
        from_dsp = self.factory.makeDSPCache(distroseries=distroseries)
        form = {
            'field.name': potemplate.name,
            'field.distroseries': '%s/%s' % (
                distroseries.distribution.name, distroseries.name),
            'field.sourcepackagename': dsp.sourcepackagename.name,
            'field.from_sourcepackagename': from_dsp.sourcepackagename.name,
            'field.actions.change': 'Change',
            }
        with celebrity_logged_in('rosetta_experts'):
            view = create_initialized_view(potemplate, '+admin', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(
            dsp.sourcepackagename.name, potemplate.sourcepackagename.name)
        self.assertEqual(
            from_dsp.sourcepackagename.name,
            potemplate.from_sourcepackagename.name)


load_tests = load_tests_apply_scenarios
