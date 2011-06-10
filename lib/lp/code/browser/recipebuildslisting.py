# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View for daily builds listings."""

__metaclass__ = type

__all__ = [
    'CompletedDailyBuildsView',
    ]

from lazr.enum import (
    EnumeratedType,
    Item,
    )
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import Choice

from canonical.launchpad import _
from canonical.launchpad.webapp.batching import BatchNavigator
from lp.app.browser.launchpadform import (
    custom_widget,
    LaunchpadFormView,
    )
from lp.app.widgets.itemswidgets import LaunchpadDropdownWidget
from lp.code.interfaces.recipebuild import IRecipeBuildRecordSet


class RecipeBuildFilter(EnumeratedType):
    """Choices for how to filter recipe build listings."""

    ALL = Item("""
        at any time

        Show all most recently completed recipe builds.
        """)

    WITHIN_30_DAYS = Item("""
        within last 30 days

        Show only recently completed recipe builds from within the last
        30 days.
        """)


class RecipeBuildBatchNavigator(BatchNavigator):
    """A Batch Navigator turn activate table sorting for single page views."""

    @property
    def table_class(self):
        if self.has_multiple_pages:
            return "listing"
        else:
            return "listing sortable"


class CompletedDailyBuildsView(LaunchpadFormView):
    """The view to show completed builds for source package recipes."""

    class schema(Interface):
        when_completed_filter = Choice(
            title=_('Recipe Build Filter'), vocabulary=RecipeBuildFilter,
            default=RecipeBuildFilter.ALL,
            description=_(
                "Filter for selecting when recipe builds have completed."))
    field_names = ['when_completed_filter']
    custom_widget('when_completed_filter', LaunchpadDropdownWidget)

    @property
    def page_title(self):
        return 'Packages Built Daily With Recipes'

    def initialize(self):
        LaunchpadFormView.initialize(self)
        self.dailybuilds = self.getDailyBuilds()
        self.batchnav = RecipeBuildBatchNavigator(
            self.dailybuilds, self.request)

    def getDailyBuilds(self):
        widget = self.widgets['when_completed_filter']
        if widget.hasValidInput():
            when_completed = widget.getInputValue()
            if when_completed == RecipeBuildFilter.WITHIN_30_DAYS:
                epoch_days = 30
            else:
                epoch_days = None
        else:
            epoch_days = None
        recipe_build_set = getUtility(IRecipeBuildRecordSet)
        return recipe_build_set.findCompletedDailyBuilds(epoch_days)
