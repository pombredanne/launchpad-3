# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base class view for sourcepackagerecipe listings."""

__metaclass__ = type

__all__ = [
    'BranchRecipeListingView',
    'HasRecipesMenuMixin',
    'PersonRecipeListingView',
    'ProductRecipeListingView',
    ]


from canonical.launchpad.browser.feeds import FeedsMixin
from canonical.launchpad.webapp import (
    LaunchpadView,
    Link,
    )
from lp.code.interfaces.sourcepackagerecipe import recipes_enabled


class HasRecipesMenuMixin:
    """A mixin for context menus for objects that implement IHasRecipes."""

    def view_recipes(self):
        text = 'View source package recipes'
        enabled = False
        if self.context.getRecipes().count():
            enabled = True
        if not recipes_enabled():
            enabled = False
        return Link(
            '+recipes', text, icon='info', enabled=enabled, site='code')


class RecipeListingView(LaunchpadView, FeedsMixin):

    feed_types = ()

    branch_enabled = True
    owner_enabled = True

    @property
    def page_title(self):
        return 'Source Package Recipes for %(displayname)s' % {
            'displayname': self.context.displayname}


class BranchRecipeListingView(RecipeListingView):

    branch_enabled = False


class PersonRecipeListingView(RecipeListingView):

    owner_enabled = False


class ProductRecipeListingView(RecipeListingView):
    pass
