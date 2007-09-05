# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Milestone views."""

__metaclass__ = type

__all__ = [
    'MilestoneSetNavigation',
    'MilestoneNavigation',
    'MilestoneFacets',
    'MilestoneContextMenu',
    'MilestoneAddView',
    'MilestoneEditView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (ILaunchBag, IMilestone,
    IMilestoneSet, IBugTaskSet, BugTaskSearchParams, IProjectMilestone)

from canonical.cachedproperty import cachedproperty

from canonical.launchpad.browser.editview import SQLObjectEditView

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ContextMenu, Link, LaunchpadView,
    enabled_with_permission, GetitemNavigation, Navigation)


class MilestoneSetNavigation(GetitemNavigation):

    usedfor = IMilestoneSet


# XXX: jamesh 2005-12-14:
# This class is required in order to make use of a side effect of
# Navigation.publishTraverse: adding context objects to
# request.traversed_objects.
class MilestoneNavigation(Navigation):

    usedfor = IMilestone


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

    links = ['edit', 'admin']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        # ProjectMilestones are virtual milestones and do not have
        # any properties which can be edited.
        enabled = not IProjectMilestone.providedBy(self.context)
        return Link('+edit', text, icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer'
        # ProjectMilestones are virtual milestones and provide no details
        # that can/must be administrated.
        enabled = not IProjectMilestone.providedBy(self.context)
        return Link('+admin', text, icon='edit', enabled=enabled)


class MilestoneView(LaunchpadView):

    # Listify and cache the specifications and bugtasks to avoid making
    # the same query over and over again when evaluating in the template.
    @cachedproperty
    def specifications(self):
        return list(self.context.specifications)

    @cachedproperty
    def bugtasks(self):
        user = getUtility(ILaunchBag).user
        params = BugTaskSearchParams(user, milestone=self.context,
                    orderby=['-importance', 'datecreated', 'id'],
                    omit_dupes=True)
        tasks = getUtility(IBugTaskSet).search(params)
        # XXX kiko 2007-08-27: Doing this in the callsite is
        # particularly annoying, but it's not easy to do the filtering
        # in BugTaskSet.search() unfortunately. Can we find a good way
        # of filtering conjoined in database queries?
        return [task for task in tasks if task.conjoined_master is None]

    @property
    def bugtask_count_text(self):
        count = len(self.bugtasks)
        if count == 1:
            return "1 bug targeted"
        else:
            return "%d bugs targeted" % count

    @property
    def specification_count_text(self):
        count = len(self.specifications)
        if count == 1:
            return "1 blueprint targeted"
        else:
            return "%d blueprints targeted" % count

    @property
    def is_project_milestone(self):
        """Check, if the current milestone is a project milestone.

        Return true, if the current milestone is a project milestone,
        else return False."""
        return IProjectMilestone.providedBy(self.context)

    @property
    def has_bugs_or_specs(self):
        return self.bugtasks or self.specifications


class MilestoneAddView:
    def create(self, name, dateexpected=None):
        """We will use the newMilestone method on the ProductSeries or
        DistroSeries context to make the milestone."""
        return self.context.newMilestone(name, dateexpected=dateexpected)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return '.'


class MilestoneEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect('../..')

