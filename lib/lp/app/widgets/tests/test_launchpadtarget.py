# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import doctest

from zope.interface import (
    implements,
    Interface,
    )

from lazr.restful.fields import Reference

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.launchpadtarget import LaunchpadTargetWidget
from lp.app.validators import LaunchpadValidationError
from lp.registry.vocabularies import (
    DistributionVocabulary,
    DistributionSourcePackageVocabulary,
    ProductVocabulary,
    )
from lp.services.features.testing import FeatureFixture
from lp.soyuz.model.binaryandsourcepackagename import (
    BinaryAndSourcePackageNameVocabulary,
    )
from lp.testing import TestCaseWithFactory


class IThing(Interface):
    target = Reference(schema=Interface)


class Thing:
    implements(IThing)
    target = None


class LaunchpadTargetWidgetTestCase(TestCaseWithFactory):
    """Test the LaunchpadTargetWidget class."""

    layer = DatabaseFunctionalLayer
    doctest_opts = (
        doctest.NORMALIZE_WHITESPACE | doctest.REPORT_NDIFF |
        doctest.ELLIPSIS)

    @property
    def form(self):
        return {
        'field.target': 'package',
        'field.target.distribution': 'fnord',
        'field.target.package': 'snarf',
        'field.target.product': 'pting',
        }

    def setUp(self):
        super(LaunchpadTargetWidgetTestCase, self).setUp()
        self.distribution, self.package = self.factory.makeDSPCache(
            distro_name='fnord', package_name='snarf')
        self.project = self.factory.makeProduct('pting')
        field = Reference(
            __name__='target', schema=Interface, title=u'target')
        field = field.bind(Thing())
        request = LaunchpadTestRequest()
        self.widget = LaunchpadTargetWidget(field, request)

    def test_template(self):
        # The render template is setup.
        self.assertTrue(
            self.widget.template.filename.endswith('launchpad-target.pt'),
            'Template was not setup.')

    def test_default_option(self):
        # This package field is the default option.
        self.assertEqual('package', self.widget.default_option)

    def test_getDistributionVocabulary(self):
        # The vocabulary is always "Distribution".
        self.assertEqual(
            'Distribution', self.widget.getDistributionVocabulary())

    def test_hasInput_false(self):
        # hasInput is false when the widget's name is not in the form data.
        self.widget.request = LaunchpadTestRequest(form={})
        self.assertEqual('field.target', self.widget.name)
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_true(self):
        # hasInput is true is the widget's name in the form data.
        self.widget.request = LaunchpadTestRequest(form=self.form)
        self.assertEqual('field.target', self.widget.name)
        self.assertTrue(self.widget.hasInput())

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are setup and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsInstance(
            self.widget.distribution_widget.context.vocabulary,
            DistributionVocabulary)
        self.assertIsInstance(
            self.widget.package_widget.context.vocabulary,
            BinaryAndSourcePackageNameVocabulary)
        self.assertIsInstance(
            self.widget.product_widget.context.vocabulary,
            ProductVocabulary)

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were setup.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIs(None, getattr(self.widget, 'distribution_widget', None))
        self.assertIs(None, getattr(self.widget, 'package_widget', None))
        self.assertIs(None, getattr(self.widget, 'product_widget', None))

    def test_setUpSubWidgets_dsp_picker_feature_flag(self):
        # The DistributionSourcePackageVocabulary is used when the
        # disclosure.dsp_picker.enabled is true.
        with FeatureFixture({u"disclosure.dsp_picker.enabled": u"on"}):
            self.widget.setUpSubWidgets()
        self.assertIsInstance(
            self.widget.package_widget.context.vocabulary,
            DistributionSourcePackageVocabulary)

    def test_setUpOptions_default_package_checked(self):
        # The radio button options are composed of the setup widgets with
        # the package widget set as the default.
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            "selectWidget('field.target.option.package', event)",
            self.widget.package_widget.onKeyPress)
        self.assertEqual(
            "selectWidget('field.target.option.product', event)",
            self.widget.product_widget.onKeyPress)
        self.assertEqual(
            '<input class="radioType" checked="checked" '
            'id="field.target.option.package" name="field.target" '
            'type="radio" value="package" />',
            self.widget.options['package'])
        self.assertEqual(
            '<input class="radioType" '
            'id="field.target.option.product" name="field.target" '
            'type="radio" value="product" />',
            self.widget.options['product'])

    def test_setUpOptions_product_checked(self):
        # The product radio button is selected when the form is submitted
        # when the target field's value is 'product'.
        form = {
            'field.target': 'product',
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" '
            'id="field.target.option.package" name="field.target" '
            'type="radio" value="package" />',
            self.widget.options['package'])
        self.assertEqual(
            '<input class="radioType" checked="checked" '
            'id="field.target.option.product" name="field.target" '
            'type="radio" value="product" />',
            self.widget.options['product'])

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted parts are valid.
        self.widget.request = LaunchpadTestRequest(form=self.form)
        self.assertTrue(self.widget.hasValidInput())

    def test_hasValidInput_false(self):
        # The field input is invalid if any of the submitted parts are
        # invalid.
        form = self.form
        form['field.target.package'] = 'non-existant'
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertFalse(self.widget.hasValidInput())

    def test_getInputValue_package(self):
        # The field value is the package when the package radio button
        # is selected and the package sub field has valid input.
        self.widget.request = LaunchpadTestRequest(form=self.form)
        self.assertEqual(self.package, self.widget.getInputValue())

    def test_getInputValue_distribution(self):
        # The field value is the distribution when the package radio button
        # is selected and the package sub field empty.
        form = self.form
        form['field.target.package'] = ''
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(self.distribution, self.widget.getInputValue())

    def test_getInputValue_distribution_invalid(self):
        form = self.form
        form['field.target.package'] = ''
        form['field.target.distribution'] = 'non-existant'
        self.widget.request = LaunchpadTestRequest(form=form)
        message = (
            "There is no distribution named 'non-existant' registered in "
            "Launchpad")
        self.assertRaisesWithContent(
            LaunchpadValidationError, message, self.widget.getInputValue)

    def test_getInputValue_product(self):
        # The field value is the product when the project radio button
        # is selected and the project sub field is valid.
        form = self.form
        form['field.target'] = 'product'
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(self.project, self.widget.getInputValue())

    def test_getInputValue_product_missing_input(self):
        # The field value is the product when the project radio button
        # is selected and the project sub field is valid.
        form = self.form
        form['field.target'] = 'product'
        del form['field.target.product']
        self.widget.request = LaunchpadTestRequest(form=form)
        message = 'Please enter a project name'
        self.assertRaisesWithContent(
            LaunchpadValidationError, message, self.widget.getInputValue)

    def test_getInputValue_product_invalid(self):
        # The field value is the product when the project radio button
        # is selected and the project sub field is valid.
        form = self.form
        form['field.target'] = 'product'
        form['field.target.product'] = 'non-existant'
        self.widget.request = LaunchpadTestRequest(form=form)
        message = (
            "There is no project named 'non-existant' registered in "
            "Launchpad")
        self.assertRaisesWithContent(
            LaunchpadValidationError, message, self.widget.getInputValue)
