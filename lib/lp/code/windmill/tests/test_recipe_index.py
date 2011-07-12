# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for recipe index pages."""

__metaclass__ = type
__all__ = []

import transaction

from storm.store import Store

from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill.constants import FOR_ELEMENT


class TestRecipeSetDaily(WindmillTestCase):
    """Test setting the daily build flag."""

    layer = CodeWindmillLayer
    suite_name = "Recipe daily build flag setting"

    def test_inline_recipe_daily_build(self):
        eric = self.factory.makePerson(
            name="eric", displayname="Eric the Viking", password="test",
            email="eric@example.com")
        recipe = self.factory.makeSourcePackageRecipe(owner=eric)
        transaction.commit()

        client, start_url = self.getClientFor(recipe, user=eric)
        client.click(id=u'edit-build_daily')
        client.waits.forElement(
            classname=u'yui3-ichoicelist-content', timeout=FOR_ELEMENT)
        client.click(link=u'Built daily')
        client.waits.forElement(
            jquery=u'("#edit-build_daily a.editicon.sprite.edit")',
            timeout=FOR_ELEMENT)
        client.asserts.assertTextIn(
            id=u'edit-build_daily', validator=u'Built daily')

        transaction.commit()
        freshly_fetched_recipe = Store.of(recipe).find(
            SourcePackageRecipe, SourcePackageRecipe.id == recipe.id).one()
        self.assertTrue(freshly_fetched_recipe.build_daily)

    def test_inline_recipe_text_errors(self):
        # XXX: do we really want to error check here?
        eric = self.factory.makePerson(
            name="eric", displayname="Eric the Viking", password="test",
            email="eric@example.com")
        recipe = self.factory.makeSourcePackageRecipe(owner=eric)
        recipe_text = recipe.recipe_text + 'merge WTF?'
        transaction.commit()

        client, start_url = self.getClientFor(recipe, user=eric)
        client.click(
            jquery=u'("div#edit-recipe_text a.yui3-editable_text-trigger")[0]')
        client.waits.forElement(
            jquery=u'("div#edit-recipe_text textarea.yui3-ieditor-input")',
            timeout=FOR_ELEMENT)
        client.type(
            text=recipe_text,
            jquery=u'("div#edit-recipe_text textarea.yui3-ieditor-input")[0]')
        client.click(
            jquery=u'("div#edit-recipe_text button.yui3-ieditor-submit_button")[0]')
        client.waits.forElement(
            jquery=u'("div#edit-recipe_text textarea.yui3-ieditor-errors")',
            timeout=FOR_ELEMENT)
        client.asserts.assertTextIn(
            jquery=u'("div#edit-recipe_text textarea.yui3-ieditor-errors")[0]',
            validator=u'End of line while looking for the branch url.')
