# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module doc."""

__metaclass__ = type


from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.translations.browser.potemplate import POTemplateAdminView

class TestPOTemplateAdminViewValidation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_validates_name(self):
        # A template name may not already be used.
        existing_name = self.factory.getUniqueString()
        existing_potemplate = self.factory.makePOTemplate(name=existing_name)
        series = existing_potemplate.productseries
        potemplate = self.factory.makePOTemplate(productseries=series)

        view = POTemplateAdminView(potemplate, LaunchpadTestRequest())
        data = dict(
            distroseries=None,
            sourcepackagename=None,
            productseries=series,
            name=existing_name,
            translation_domain=potemplate.translation_domain,
            )
        view.validate(data)
        self.assertEqual([u'Name is already in use.'], view.errors)

    def test_validates_translation_domain(self):
        # A translation domain may not already be used.
        existing_domain = self.factory.getUniqueString()
        existing_potemplate = self.factory.makePOTemplate(
            translation_domain=existing_domain)
        series = existing_potemplate.productseries
        potemplate = self.factory.makePOTemplate(productseries=series)

        view = POTemplateAdminView(potemplate, LaunchpadTestRequest())
        data = dict(
            distroseries=None,
            sourcepackagename=None,
            productseries=series,
            name=potemplate.name,
            translation_domain=existing_domain,
            )
        view.validate(data)
        self.assertEqual([u'Domain is already in use.'], view.errors)
