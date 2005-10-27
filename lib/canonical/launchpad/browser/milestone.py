# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Milestone views."""

__metaclass__ = type

__all__ = [
    'MilestoneSetNavigation',
    'MilestoneFacets',
    'MilestoneContextMenu',
    'MilestoneAddView',
    'MilestoneEditView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, IMilestone, IMilestoneSet)
from canonical.launchpad.browser.editview import SQLObjectEditView

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ContextMenu, Link, GetitemNavigation)


class MilestoneSetNavigation(GetitemNavigation):

    usedfor = IMilestoneSet


class MilestoneFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IMilestone."""

    usedfor = IMilestone

    enable_only = ['overview']

    def overview(self):
        target = ''
        text = 'Overview'
        summary = 'General information about %s' % self.context.displayname
        return Link(target, text, summary)


class MilestoneContextMenu(ContextMenu):

    usedfor = IMilestone

    links = ['edit']

    def edit(self):
        text = 'Edit Milestone'
        return Link('+edit', text, icon='edit')


class MilestoneAddView:
    def create(self, name, dateexpected=None):
        """Inject the relevant product or distribution into the kw args."""
        product = None
        distribution = None
        if IProduct.providedBy(self.context):
            product = self.context.id
        elif IDistribution.providedBy(self.context):
            distribution = self.context.id
        return getUtility(IMilestoneSet).new(name, product=product,
            distribution=distribution, dateexpected=dateexpected)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return '.'


class MilestoneEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect('../..')

