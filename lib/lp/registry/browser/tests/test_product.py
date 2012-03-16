# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for product views."""

__metaclass__ = type

from zope.component import getUtility

from lp.app.enums import ServiceUsage
from lp.registry.interfaces.product import (
    IProductSet,
    License,
    )
from lp.services.config import config
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    BrowserTestCase,
    login_celebrity,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.fixture import DemoMode
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import find_tag_by_id
from lp.testing.service_usage_helpers import set_service_usage
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


class TestProductConfiguration(TestCaseWithFactory):
    """Tests the configuration links and helpers."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductConfiguration, self).setUp()
        self.product = self.factory.makeProduct()

    def test_registration_not_done(self):
        # The registration done property on the product index view
        # tells you if all the configuration work is done, based on
        # usage enums.

        # At least one usage enum is unknown, so registration done is false.
        self.assertEqual(
            self.product.codehosting_usage,
            ServiceUsage.UNKNOWN)
        view = create_view(self.product, '+get-involved')
        self.assertFalse(view.registration_done)

        set_service_usage(
            self.product.name,
            codehosting_usage="EXTERNAL",
            bug_tracking_usage="LAUNCHPAD",
            answers_usage="EXTERNAL",
            translations_usage="NOT_APPLICABLE")
        view = create_view(self.product, '+get-involved')
        self.assertTrue(view.registration_done)


class TestProductAddView(TestCaseWithFactory):
    """Tests the configuration links and helpers."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductAddView, self).setUp()
        self.product_set = getUtility(IProductSet)
        # Marker allowing us to reset the config.
        config.push(self.id(), '')
        self.addCleanup(config.pop, self.id())

    def test_staging_message_is_not_demo(self):
        view = create_initialized_view(self.product_set, '+new')
        message = find_tag_by_id(view.render(), 'staging-message')
        self.assertTrue(message is not None)

    def test_staging_message_is_demo(self):
        self.useFixture(DemoMode())
        view = create_initialized_view(self.product_set, '+new')
        message = find_tag_by_id(view.render(), 'staging-message')
        self.assertEqual(None, message)


class TestProductView(TestCaseWithFactory):
    """Tests the ProductView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductView, self).setUp()
        self.product = self.factory.makeProduct(name='fnord')

    def test_show_programming_languages_without_languages(self):
        # show_programming_languages is false when there are no programming
        # languages set.
        view = create_initialized_view(self.product, '+index')
        self.assertEqual(None, self.product.programminglang)
        self.assertFalse(view.show_programming_languages)

    def test_show_programming_languages_with_languages(self):
        # show_programming_languages is true when programming languages
        # are set.
        with person_logged_in(self.product.owner):
            self.product.programminglang = 'C++'
        view = create_initialized_view(self.product, '+index')
        self.assertTrue(view.show_programming_languages)

    def test_show_license_info_without_other_license(self):
        # show_license_info is false when one of the "other" licenses is
        # not selected.
        view = create_initialized_view(self.product, '+index')
        self.assertEqual((License.GNU_GPL_V2, ), self.product.licenses)
        self.assertFalse(view.show_license_info)

    def test_show_license_info_with_other_open_source_license(self):
        # show_license_info is true when the Other/Open Source license is
        # selected.
        view = create_initialized_view(self.product, '+index')
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.OTHER_OPEN_SOURCE]
        self.assertTrue(view.show_license_info)

    def test_show_license_info_with_other_open_proprietary_license(self):
        # show_license_info is true when the Other/Proprietary license is
        # selected.
        view = create_initialized_view(self.product, '+index')
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.OTHER_PROPRIETARY]
        self.assertTrue(view.show_license_info)

    def test_is_proprietary_with_proprietary_license(self):
        # is_proprietary is true when the project has a proprietary license.
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.OTHER_PROPRIETARY]
        view = create_initialized_view(self.product, '+index')
        self.assertTrue(view.is_proprietary)

    def test_is_proprietary_without_proprietary_license(self):
        # is_proprietary is false when the project has a proprietary license.
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.GNU_GPL_V2]
        view = create_initialized_view(self.product, '+index')
        self.assertFalse(view.is_proprietary)

    def test_active_widget(self):
        # The active widget is is unique to the product.
        view = create_initialized_view(self.product, '+index')
        widget = view.active_widget
        self.assertEqual('fnord-edit-active', widget.content_box_id)
        self.assertEqual(
            canonical_url(self.product, view_name='+review-license'),
            widget.edit_url)

    def test_project_reviewed_widget(self):
        # The license reviewed widget is is unique to the product.
        login_celebrity('registry_experts')
        view = create_initialized_view(self.product, '+index')
        widget = view.project_reviewed_widget
        self.assertEqual('fnord-edit-project-reviewed', widget.content_box_id)
        self.assertEqual(
            canonical_url(self.product, view_name='+review-license'),
            widget.edit_url)

    def test_license_approved_widget_any_license(self):
        # The license approved widget is is unique to the product.
        login_celebrity('registry_experts')
        view = create_initialized_view(self.product, '+index')
        widget = view.license_approved_widget
        self.assertEqual('fnord-edit-license-approved', widget.content_box_id)
        self.assertEqual(
            canonical_url(self.product, view_name='+review-license'),
            widget.edit_url)

    def test_license_approved_widget_prorietary_license(self):
        # Proprietary projects cannot be approved.
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.OTHER_PROPRIETARY]
        login_celebrity('registry_experts')
        view = create_initialized_view(self.product, '+index')
        text = view.license_approved_widget
        self.assertEqual('Commercial subscription required', text)

    def test_license_approved_widget_no_license(self):
        # Projects without a license cannot be approved.
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.DONT_KNOW]
        login_celebrity('registry_experts')
        view = create_initialized_view(self.product, '+index')
        text = view.license_approved_widget
        self.assertEqual('License required', text)

    def test_widget_id_for_name_dots(self):
        # Dots are replaced with dashes to make a valid CSS Id.
        login_celebrity('registry_experts')
        self.product.name = 'fnord.dom'
        view = create_initialized_view(self.product, '+index')
        self.assertEqual(
            'fnord-dom-edit-active',
            view.active_widget.content_box_id)
        self.assertEqual(
            'fnord-dom-edit-project-reviewed',
            view.project_reviewed_widget.content_box_id)
        self.assertEqual(
            'fnord-dom-edit-license-approved',
            view.license_approved_widget.content_box_id)


class ProductSetReviewLicensesViewTestCase(TestCaseWithFactory):
    """Tests the ProductSetReviewLicensesView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ProductSetReviewLicensesViewTestCase, self).setUp()
        self.product_set = getUtility(IProductSet)
        self.user = login_celebrity('registry_experts')

    def test_initial_values(self):
        # The initial values show active, unreviewed, unapproved projects.
        view = create_initialized_view(self.product_set, '+review-licenses')
        self.assertContentEqual(
            {'active': True,
             'project_reviewed': False,
             'license_approved': False,
             'search_text': None,
             'licenses': set(),
             'has_subscription': None,
             'created_after': None,
             'created_before': None,
             'subscription_expires_after': None,
             'subscription_expires_before': None,
             'subscription_modified_after': None,
             'subscription_modified_before': None,
             }.items(),
            view.initial_values.items())

    def test_forReviewBatched(self):
        # The projects are batched.
        view = create_initialized_view(self.product_set, '+review-licenses')
        batch = view.forReviewBatched()
        self.assertEqual(50, batch.default_size)

    def test_project_common_data(self):
        # The each project contains information to complete a review.
        self.factory.makeProduct(name='fnord')
        view = create_initialized_view(
            self.product_set, '+review-licenses', principal=self.user)
        content = find_tag_by_id(view.render(), 'project-fnord')
        self.assertTrue(content.find(id='fnord-maintainer') is not None)
        self.assertTrue(content.find(id='fnord-registrant') is not None)
        self.assertTrue(content.find(id='fnord-description') is not None)
        self.assertTrue(content.find(id='fnord-packages') is not None)
        self.assertTrue(content.find(id='fnord-releases') is not None)
        self.assertTrue(content.find(id='fnord-usage') is not None)
        self.assertTrue(content.find(id='fnord-licenses') is not None)
        self.assertTrue(content.find(id='fnord-whiteboard') is not None)
        self.assertFalse(content.find(
            id='fnord-commercial-subscription') is not None)
        self.assertFalse(content.find(id='fnord-license-info') is not None)

    def test_project_license_info_data(self):
        # The projects with the OTHER_* licenese will show license_info data.
        product = self.factory.makeProduct(name='fnord')
        with person_logged_in(product.owner):
            product.licenses = [License.OTHER_OPEN_SOURCE]
        view = create_initialized_view(
            self.product_set, '+review-licenses', principal=self.user)
        content = find_tag_by_id(view.render(), 'project-fnord')
        self.assertTrue(content.find(id='fnord-license-info') is not None)

    def test_project_commercial_subscription_data(self):
        # The projects with the OTHER_Proprietary license show commercial
        # subscription information.
        product = self.factory.makeProduct(name='fnord')
        with person_logged_in(product.owner):
            product.licenses = [License.OTHER_PROPRIETARY]
        view = create_initialized_view(
            self.product_set, '+review-licenses', principal=self.user)
        content = find_tag_by_id(view.render(), 'project-fnord')
        self.assertTrue(content.find(
            id='fnord-commercial-subscription') is not None)

    def test_project_widgets(self):
        # The active, project_reviewed, and license_approved lazrjs widgets
        # are used.
        self.factory.makeProduct(name='fnord')
        view = create_initialized_view(
            self.product_set, '+review-licenses', principal=self.user)
        content = find_tag_by_id(view.render(), 'fnord-statuses')
        self.assertTrue(
            'Y.lp.app.choice.addBinaryChoice' in str(
                content.find(id='fnord-edit-active').parent))
        self.assertTrue(
            'Y.lp.app.choice.addBinaryChoice' in str(
                content.find(id='fnord-edit-project-reviewed').parent))
        self.assertTrue(
            'Y.lp.app.choice.addBinaryChoice' in str(
                content.find(id='fnord-edit-license-approved').parent))


class TestProductRdfView(BrowserTestCase):
    """Test the Product RDF view."""

    layer = DatabaseFunctionalLayer

    def test_headers(self):
        """The headers for the RDF view of a product should be as expected."""
        product = self.factory.makeProduct()
        browser = self.getViewBrowser(product, view_name='+rdf')
        content_disposition = 'attachment; filename="%s.rdf"' % product.name
        self.assertEqual(
            content_disposition, browser.headers['Content-disposition'])
        self.assertEqual(
            'application/rdf+xml', browser.headers['Content-type'])
