# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base class view for sourcepackagerecipe listings."""

__metaclass__ = type

__all__ = [
    'BranchRecipeListingView',
    'HasRecipesMenuMixin',
    'PersonRecipeListingView',
    'ProductRecipeListingView',
    ]


from lp.code.browser.decorations import DecoratedBranch
from lp.services.feeds.browser import FeedsMixin
from lp.services.webapp import (
    LaunchpadView,
    Link,
    )


class HasRecipesMenuMixin:
    """A mixin for context menus for objects that implement IHasRecipes."""

    def view_recipes(self):
        text = 'View source package recipes'
        enabled = False
        if self.context.recipes.count():
            enabled = True
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

    def initialize(self):
        super(BranchRecipeListingView, self).initialize()
        # Replace our context with a decorated branch, if it is not already
        # decorated.
        if not isinstance(self.context, DecoratedBranch):
            self.context = DecoratedBranch(self.context)


class PersonRecipeListingView(RecipeListingView):

    owner_enabled = False


class ProductRecipeListingView(RecipeListingView):
    pass
