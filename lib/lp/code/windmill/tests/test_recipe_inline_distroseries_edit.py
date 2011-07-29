# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for requesting recipe builds."""

__metaclass__ = type
__all__ = []

from storm.store import Store
import transaction
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    )


class TestRecipeEdit(WindmillTestCase):
    """Test recipe editing with inline widgets."""

    layer = CodeWindmillLayer
    suite_name = "Request recipe build"

    def test_inline_distroseries_edit(self):
        """Test that inline editing of distroseries works."""

        chef = self.factory.makePerson(
            displayname='Master Chef', name='chef', password='test',
            email="chef@example.com")
        recipe = self.factory.makeSourcePackageRecipe(owner=chef)
        transaction.commit()

        client, start_url = self.getClientFor(recipe, user=chef)
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
        store = Store.of(recipe)
        saved_recipe = store.find(
            SourcePackageRecipe,
            SourcePackageRecipe.name==recipe.name).one()
        self.assertEqual(len(list(saved_recipe.distroseries)), 2)
        distroseries=sorted(
            saved_recipe.distroseries, key=lambda ds: ds.displayname)
        self.assertEqual(distroseries[0], hoary)
