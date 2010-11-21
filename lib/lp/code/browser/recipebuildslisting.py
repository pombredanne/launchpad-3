# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View for daily builds listings."""

__metaclass__ = type

__all__ = [
    'CompletedDailyBuildsView',
    ]

from zope.component import getUtility
from zope.interface import Interface
from zope.schema import Choice

from lazr.enum._enum import EnumeratedType, Item

from canonical.launchpad import _
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.launchpadform import (
    custom_widget,
    LaunchpadFormView,
    )
from canonical.widgets.itemswidgets import LaunchpadDropdownWidget
from lp.code.interfaces.recipebuild import IRecipeBuildRecordSet


class RecipeBuildFilter(EnumeratedType):
    """Choices for how to filter recipe build listings."""

    ALL = Item("""
        all

        Show all completed recipe builds.
        """)

    WITHIN_30_DAYS = Item("""
        within last 30 days

        Show only recipe builds completed within last 30 days.
        """)

    
class RecipeBuildBatchNavigator(BatchNavigator):
    @property
    def table_class(self):
        if self.has_multiple_pages:
            return "listing"
        else:
            return "listing sortable"


class CompletedDailyBuildsView(LaunchpadFormView):

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
        return 'Most Recently Completed Daily Recipe Builds'

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
