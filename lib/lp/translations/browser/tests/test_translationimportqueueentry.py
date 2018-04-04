# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for translation import queue views."""

from datetime import datetime

from pytz import timezone
from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import ServiceUsage
from lp.services.features.testing import FeatureFixture
from lp.services.webapp import canonical_url
from lp.testing import (
    celebrity_logged_in,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.views import create_initialized_view
from lp.translations.browser.translationimportqueue import escape_js_string
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )


class TestTranslationImportQueueEntryView(WithScenarios, TestCaseWithFactory):
    """Tests for the queue entry review form."""

    layer = LaunchpadFunctionalLayer

    scenarios = [
        ("spn_picker", {"features": {}}),
        ("dsp_picker", {
            "features": {u"disclosure.dsp_picker.enabled": u"on"},
            }),
        ]

    def setUp(self):
        super(TestTranslationImportQueueEntryView, self).setUp(
            'foo.bar@canonical.com')
        if self.features:
            self.useFixture(FeatureFixture(self.features))
        self.queue = getUtility(ITranslationImportQueue)
        self.uploader = self.factory.makePerson()

    def _makeProductSeries(self):
        """Set up a product series for a translatable product."""
        product = self.factory.makeProduct()
        product.translations_usage = ServiceUsage.LAUNCHPAD
        return product.getSeries('trunk')

    def _makeEntry(self, productseries=None, distroseries=None,
                   sourcepackagename=None, filename=None, potemplate=None):
        if filename is None:
            filename = self.factory.getUniqueString() + '.pot'
        contents = self.factory.getUniqueString()
        entry = self.queue.addOrUpdateEntry(
            filename, contents, False, self.uploader,
            productseries=productseries, distroseries=distroseries,
            sourcepackagename=sourcepackagename, potemplate=potemplate)
        return removeSecurityProxy(entry)

    def test_import_target_productseries(self):
        # If the entry's attached to a ProductSeries, that's what
        # import_target returns.
        series = self._makeProductSeries()
        entry = self._makeEntry(productseries=series)
        view = create_initialized_view(entry, '+index')

        self.assertEqual(series, view.import_target)

    def test_import_target_sourcepackage(self):
        # If the entry has a DistroSeries and a SourcePackageName, the
        # import_target is the corresponding SourcePackage.
        series = self.factory.makeDistroSeries()
        packagename = self.factory.makeSourcePackageName()
        package = self.factory.makeSourcePackage(packagename, series)
        entry = self._makeEntry(
            distroseries=series, sourcepackagename=packagename)
        view = create_initialized_view(entry, '+index')

        self.assertEqual(package, view.import_target)

    def test_productseries_templates_link(self):
        # productseries_templates_link counts and, if appropriate links
        # to, the series' templates.
        series = self._makeProductSeries()
        entry = self._makeEntry(productseries=series)
        view = create_initialized_view(entry, '+index')

        # If there are no templates, there is no link.
        self.assertEqual("no templates", view.productseries_templates_link)

        # For one template, there is a link.  Its text uses the
        # singular.
        self.factory.makePOTemplate(productseries=series)
        self.assertIn('1 template', view.productseries_templates_link)
        self.assertNotIn('1 templates', view.productseries_templates_link)
        url = canonical_url(series, rootsite='translations') + '/+templates'
        self.assertIn(url, view.productseries_templates_link)

    def test_product_translatable_series(self):
        # If the entry belongs to a productseries, product_translatable_series
        # lists the product's translatable series.
        series = self._makeProductSeries()
        product = series.product
        entry = self._makeEntry(productseries=series)
        view = create_initialized_view(entry, '+index')

        # No translatable series.
        series_text = view.product_translatable_series
        self.assertEqual("Project has no translatable series.", series_text)

        # One translatable series.
        extra_series = self.factory.makeProductSeries(product=product)
        self.factory.makePOTemplate(productseries=extra_series)
        series_text = view.product_translatable_series
        self.assertIn("Project has translatable series:", series_text)
        # A link follows, and the sentence ends in a period.
        self.assertEqual('</a>.', series_text[-5:])

        # Two translatable series.
        extra_series = self.factory.makeProductSeries(product=product)
        self.factory.makePOTemplate(productseries=extra_series)
        series_text = view.product_translatable_series
        # The links to the series are separated by a comma.
        self.assertIn("</a>, <a ", series_text)
        # The sentence ends in a period.
        self.assertEqual('</a>.', series_text[-5:])

        # Many translatable series.  The list is cut short; there's an
        # ellipsis to indicate this.
        series_count = len(product.translatable_series)
        for counter in range(series_count, view.max_series_to_display + 1):
            extra_series = self.factory.makeProductSeries(product=product)
            self.factory.makePOTemplate(productseries=extra_series)
        series_text = view.product_translatable_series
        # The list is cut short.
        displayed_series_count = series_text.count('</a>')
        self.assertNotEqual(
            len(product.translatable_series), displayed_series_count)
        self.assertEqual(view.max_series_to_display, displayed_series_count)
        # The list of links ends with an ellipsis.
        self.assertEqual('</a>, ...', series_text[-9:])

    def test_status_change_date(self):
        # status_change_date describes the date of the entry's last
        # status change.
        series = self._makeProductSeries()
        entry = self._makeEntry(productseries=series)
        view = create_initialized_view(entry, '+index')

        # If the date equals the upload date, there's no need to show
        # anything.
        self.assertEqual('', view.status_change_date)

        # If there is a difference, there's a human-readable
        # description.
        UTC = timezone('UTC')
        entry.dateimported = datetime(year=2005, month=11, day=29, tzinfo=UTC)
        entry.date_status_changed = datetime(
            year=2007, month=8, day=14, tzinfo=UTC)
        self.assertEqual(
            "Last changed on 2007-08-14.", view.status_change_date)

    def test_initial_values_domain(self):
        # Without a given potemplate, a translation domain will be suggested
        # from the file name.
        series = self._makeProductSeries()
        entry = self._makeEntry(
            productseries=series, filename="My_Domain.pot")
        view = create_initialized_view(entry, '+index')

        self.assertEqual(
            "My_Domain", view.initial_values['translation_domain'])

    def test_initial_values_existing_domain(self):
        # With a given potemplate, its translation domain will be presented
        # as the initial value.
        domain = self.factory.getUniqueString()
        series = self._makeProductSeries()
        potemplate = self.factory.makePOTemplate(
            productseries=series, translation_domain=domain)
        entry = self._makeEntry(
            productseries=series, potemplate=potemplate)
        view = create_initialized_view(entry, '+index')

        self.assertEqual(domain, view.initial_values['translation_domain'])

    def test_initial_values_potemplate(self):
        # Without a given potemplate, a name will be suggested from the file
        # name. The name is converted to be suitable as a template name.
        series = self._makeProductSeries()
        entry = self._makeEntry(
            productseries=series, filename="My_Domain.pot")
        view = create_initialized_view(entry, '+index')

        self.assertEqual("my-domain", view.initial_values['name'])

    def test_initial_values_existing_potemplate(self):
        # With a given potemplate, its name will be presented
        # as the initial value.
        name = self.factory.getUniqueString()
        series = self._makeProductSeries()
        potemplate = self.factory.makePOTemplate(
            productseries=series, name=name)
        entry = self._makeEntry(
            productseries=series, potemplate=potemplate)
        view = create_initialized_view(entry, '+index')

        self.assertEqual(name, view.initial_values['name'])

    def test_change_sourcepackage(self):
        # Changing the source package is honoured.
        series = self.factory.makeDistroSeries()
        packagename = self.factory.makeSourcePackageName()
        potemplate = self.factory.makePOTemplate(
            distroseries=series, sourcepackagename=packagename)
        entry = self._makeEntry(
            distroseries=series, sourcepackagename=packagename,
            potemplate=potemplate)
        dsp = self.factory.makeDSPCache(distroseries=series)
        form = {
            'field.file_type': 'POT',
            'field.path': entry.path,
            'field.sourcepackagename': dsp.sourcepackagename.name,
            'field.name': potemplate.name,
            'field.translation_domain': potemplate.translation_domain,
            'field.languagepack': '',
            'field.actions.approve': 'Approve',
            }
        with celebrity_logged_in('rosetta_experts'):
            view = create_initialized_view(entry, '+index', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(
            dsp.sourcepackagename.name,
            entry.potemplate.sourcepackagename.name)


class TestEscapeJSString(TestCase):
    """Test `escape_js_string`."""

    def test_escape_js_string_empty(self):
        self.assertEqual('', escape_js_string(''))

    def test_escape_js_string_plain(self):
        self.assertEqual('foo', escape_js_string('foo'))

    def test_escape_js_string_singlequote(self):
        self.assertEqual("\\'", escape_js_string("'"))

    def test_escape_js_string_doublequote(self):
        self.assertEqual('\\"', escape_js_string('"'))

    def test_escape_js_string_backslash(self):
        self.assertEqual('\\\\', escape_js_string('\\'))

    def test_escape_js_string_ampersand(self):
        self.assertEqual('&', escape_js_string('&'))


load_tests = load_tests_apply_scenarios
