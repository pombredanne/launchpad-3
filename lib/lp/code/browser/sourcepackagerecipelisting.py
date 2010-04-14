# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base class view for sourcepackagerecipe listings."""

__metaclass__ = type

__all__ = [
    'RecipeListingView',

    #'BranchRecipeListingView',
    #'PersonRecipeListingView',
    #'ProductRecipeListingView',
    ]

from lazr.enum import EnumeratedType, Item
from zope.interface import Interface
from zope.schema import Choice

from canonical.launchpad import _
from canonical.launchpad.browser.feeds import FeedsMixin
from canonical.launchpad.webapp import LaunchpadFormView, LaunchpadView
from lp.code.interfaces.branch import IBranch


class RecipeListingSort(EnumeratedType):
    """Choices for how to sort recipe listings."""

    NEWEST = Item("""
        by newest

        Sort recipes by newest
        """)


class IRecipeListingFilter(Interface):
    """The schema for the branch listing ordering form."""

    sort_by = Choice(
        title=_('ordered by'), vocabulary=RecipeListingSort,
        default=RecipeListingSort.NEWEST)


class RecipeListingView(LaunchpadView, FeedsMixin):

    feed_types = ()


class BranchRecipeListingView(RecipeListingView):

    __used_for__ = IBranch

    @property
    def page_title(self):
        return 'Source Package Recipes for %(displayname)s' % {
            'displayname': self.context.displayname}





#class RecipeListingView(LaunchpadFormView, FeedsMixin):
#    """A base class for views of branch listings."""
#
#    schema = IRecipeListingFilter
#    field_names = ['sort_by']
#    custom_widget('sort_by', LaunchpadDropdownWidget)
#
#    extra_columns = []
#    label_template = 'Source Package Recipes for %(displayname)s'
#
#    # no_sort_by is a sequence of items from the RecipeListingSort
#    # enumeration to not offer in the sort_by widget.
#    no_sort_by = ()
#
#    # Set the feed types to be only the various branches feed links.  The
#    # `feed_links` property will screen this list and produce only the feeds
#    # appropriate to the context.
#    feed_types = ()
#
#    @property
#    def label(self):
#        return self.label_template % {
#            'displayname': self.context.displayname,
#            'title': getattr(self.context, 'title', 'no-title')}
#
#    # Provide a default page_title for distros and other things without
#    # breadcrumbs..
#    page_title = label
#
#    @property
#    def initial_values(self):
#        return {}
#
#    def recipes(self):
#        """All branches related to this target, sorted for display."""
#        return self.context.getRecipes()
#
#    @cachedproperty
#    def recipe_count(self):
#        """The number of total branches the user can see."""
#        return self.recipes.count()
#
#    @property
#    def recipe_listing_sort_values(self):
#        """The enum items we should present in the 'sort_by' widget.
#
#        Subclasses get the chance to avoid some sort options (it makes no
#        sense to offer to sort the product branch listing by product name!)
#        and if we're filtering to a single lifecycle status it doesn't make
#        much sense to sort by lifecycle.
#        """
#        # This is pretty painful.
#        # First we find the items which are not excluded for this view.
#        vocab_items = [item for item in RecipeListingSort.items.items
#                       if item not in self.no_sort_by]
#        return vocab_items
#
#    @property
#    def sort_by_field(self):
#        """The zope.schema field for the 'sort_by' widget."""
#        orig_field = IRecipeListingFilter['sort_by']
#        values = self.recipe_listing_sort_values
#        return Choice(__name__=orig_field.__name__,
#                      title=orig_field.title,
#                      required=True, values=values, default=values[0])
#
#    @property
#    def sort_by(self):
#        """The value of the `sort_by` widget, or None if none was present."""
#        widget = self.widgets['sort_by']
#        if widget.hasValidInput():
#            return widget.getInputValue()
#        else:
#            # If a derived view has specified a default sort_by, use that.
#            return self.initial_values.get('sort_by')
#
#    def setUpWidgets(self, context=None):
#        """Set up the 'sort_by' widget with only the applicable choices."""
#        fields = []
#        for field_name in self.field_names:
#            if field_name == 'sort_by':
#                field = form.FormField(self.sort_by_field)
#            else:
#                field = self.form_fields[field_name]
#            fields.append(field)
#        self.form_fields = form.Fields(*fields)
#        super(RecipeListingView, self).setUpWidgets(context)
