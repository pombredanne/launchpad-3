# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for requesting recipe builds."""

__metaclass__ = type
__all__ = []

import transaction

from canonical.launchpad.webapp.publisher import canonical_url
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )
from lp.testing.windmill.lpuser import login_person
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase


class TestRecipeEdit(WindmillTestCase):
    """Test recipe editing with inline widgets."""

    layer = CodeWindmillLayer
    suite_name = "Request recipe build"

    def setUp(self):
        super(TestRecipeEdit, self).setUp()
        self.chef = self.factory.makePerson(
            displayname='Master Chef', name='chef', password='test',
            email="chef@example.com")
        self.user = self.chef
        self.recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, name=u'cake_recipe')
        transaction.commit()
        login_person(self.chef, "chef@example.com", "test", self.client)

    def test_inline_distroseries_edit(self):
        """Test that inline editing of distroseries works."""

        client = self.client
        client.open(url=canonical_url(self.recipe))
        client.waits.forElement(
            id=u'edit-distroseries-items', timeout=PAGE_LOAD)

        # Edit the distro series.
        client.click(
            jquery=u'("span#edit-distroseries button.yui3-activator-act")[0]')
        client.waits.forElement(
            jquery=u'(".overlay-close-button.lazr-pos")',
            timeout=FOR_ELEMENT)
        client.click(name=u'field.distroseries.0')
        client.click(jquery=u'(".overlay-close-button.lazr-pos")[0]')

        # Give the UI a chance to be updated.
        client.waits.sleep(milliseconds=SLEEP)

        # Check that the new one is added.
        client.asserts.assertTextIn(
            jquery=u"('#edit-distroseries-items ul li a')[0]",
            validator=u'Hoary')

