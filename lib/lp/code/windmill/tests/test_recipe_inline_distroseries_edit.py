# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for requesting recipe builds."""

__metaclass__ = type
__all__ = []

import transaction

from zope.component import getUtility
from storm.store import Store

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.publisher import canonical_url
from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
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
        client.click(jquery=u'("#edit-distroseries-btn")[0]')
        client.waits.forElement(
            jquery=u'("#edit-distroseries-save")',
            timeout=FOR_ELEMENT)
        # Click the checkbox to select the first distro series
        client.click(name=u'field.distroseries.0')
        client.waits.forElement(
          jquery=u"('[name=\"field.distroseries.0\"][checked=\"checked\"]')",
          timeout=FOR_ELEMENT)
        # Save it
        client.click(jquery=u'("#edit-distroseries-save")[0]')

        # Wait for the the new one that is added.
        client.waits.forElement(
            jquery=u"('#edit-distroseries-items ul li a')[0]",
            timeout=FOR_ELEMENT)

        # Check that the new data was saved.
        transaction.commit()
        hoary = getUtility(ILaunchpadCelebrities).ubuntu['hoary']
        store = Store.of(self.recipe)
        saved_recipe = store.find(
            SourcePackageRecipe,
            SourcePackageRecipe.name==u'cake_recipe').one()
        self.assertEqual(len(list(saved_recipe.distroseries)), 2)
        distroseries=sorted(
            saved_recipe.distroseries, key=lambda ds: ds.displayname)
        self.assertEqual(distroseries[0], hoary)