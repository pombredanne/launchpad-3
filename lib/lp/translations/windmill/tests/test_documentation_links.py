# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for translation documentation links behaviour."""

__metaclass__ = type
__all__ = []

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.windmill.testing import lpuser
from lp.app.enums import ServiceUsage
from lp.testing import WindmillTestCase
from lp.translations.windmill.testing import TranslationsWindmillLayer


class DocumentationLinksTest(WindmillTestCase):
    """Test that the documentation links on translation pages work."""

    layer = TranslationsWindmillLayer
    suite_name = "Translation documentation links"

    def createPOTemplateWithPOTMsgSets(self, productseries, name,
                                       number_of_potmsgsets):
        potemplate = self.factory.makePOTemplate(
            productseries=productseries, name=name)
        for sequence in range(number_of_potmsgsets):
            self.factory.makePOTMsgSet(potemplate, sequence=sequence+1)
        removeSecurityProxy(potemplate).messagecount = number_of_potmsgsets
        return potemplate

    def test_documentation_links(self):
        """Tests that documentation links are shown/hidden properly.

        The test:
        * opens a Spanish translation page;
        * tries hiding the notification box;
        * makes sure it's hidden when you stay on the same translation;
        * makes sure it's shown again when you go to a different translation.
        """
        client = self.client

        user = lpuser.TRANSLATIONS_ADMIN

        # Create a translation group with documentation to use in the test.
        group = self.factory.makeTranslationGroup(
            name='testing-group', title='Testing group',
            url=(u'https://help.launchpad.net/Translations/'
                 u'LaunchpadTranslators'))

        # Create a translatable project with a template containing 15
        # messages (so we can go to multiple pages of each translation).
        project = self.factory.makeProduct(
            name='test-product',
            displayname='Test Product',
            translations_usage=ServiceUsage.LAUNCHPAD)
        removeSecurityProxy(project).translationgroup = group

        potemplate = self.createPOTemplateWithPOTMsgSets(
            productseries=project.development_focus, name='template',
            number_of_potmsgsets=15)
        import transaction
        transaction.commit()

        # Go to Evolution translations page logged in as translations admin.
        user.ensure_login(client)

        client.open(
            url=(u'%s/test-product/trunk/+pots/template/es/'
                 % TranslationsWindmillLayer.base_url))
        client.waits.forPageLoad(timeout=u'20000')

        # Make sure notification box is shown.
        client.waits.forElement(classname=u'important-notice-container',
                                timeout=u'8000')
        # Click the hide button.
        client.waits.forElement(classname=u'important-notice-cancel-button',
                                timeout=u'8000')
        client.click(classname=u'important-notice-cancel-button')
        # Hiding entire container looks ugly, so only the ballon itself
        # is hidden.
        client.waits.forElementProperty(classname=u'important-notice-balloon',
                                        option=u'style.display|none',
                                        timeout=u'8000')

        # Navigating to the next page of this translation doesn't show
        # the notification box.
        client.click(classname=u'next')
        client.waits.forPageLoad(timeout=u'20000')
        client.asserts.assertProperty(classname=u'important-notice-container',
                                      validator=u'style.display|none')

        # Look at Catalan translations page to make sure that the
        # notification box is visible even though user dismissed Spanish
        # translation notification.
        client.open(
            url=(u'%s/test-product/trunk/+pots/template/ca/'
                 % TranslationsWindmillLayer.base_url))
        client.waits.forPageLoad(timeout=u'20000')
        client.asserts.assertNotProperty(
            classname=u'important-notice-container',
            validator=u'style.display|none')
