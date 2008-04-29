# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Milestone views."""

__metaclass__ = type

__all__ = [
    'milestone_to_structuralheading',
    'MilestoneSetNavigation',
    'MilestoneNavigation',
    'MilestoneContextMenu',
    'MilestoneAddView',
    'MilestoneEditView',
    ]

from zope.component import getUtility

from canonical.launchpad import _
from canonical.cachedproperty import cachedproperty

from canonical.launchpad.interfaces import (ILaunchBag, IMilestone,
    IMilestoneSet, IBugTaskSet, BugTaskSearchParams, IProjectMilestone,
    IStructuralHeaderPresentation)

from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget,
    ContextMenu, Link, LaunchpadEditFormView, LaunchpadFormView,
    LaunchpadView, enabled_with_permission, GetitemNavigation, Navigation)

from canonical.widgets import DateWidget


class MilestoneSetNavigation(GetitemNavigation):

    usedfor = IMilestoneSet


# XXX: jamesh 2005-12-14:
# This class is required in order to make use of a side effect of
# Navigation.publishTraverse: adding context objects to
# request.traversed_objects.
class MilestoneNavigation(Navigation):

    usedfor = IMilestone


def milestone_to_structuralheading(milestone):
    """Adapts an `IMilestone` into an `IStructuralHeaderPresentation`."""
    return IStructuralHeaderPresentation(milestone.target)


class MilestoneContextMenu(ContextMenu):

    usedfor = IMilestone

    links = ['edit', 'admin', 'subscribe']

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

    def subscribe(self):
        enabled = not IProjectMilestone.providedBy(self.context)
        return Link('+subscribe', 'Subscribe to bug mail',
                    icon='edit', enabled=enabled)


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


class MilestoneAddView(LaunchpadFormView):
    """A view for creating a new Milestone."""

    schema = IMilestone
    field_names = ['name', 'dateexpected', 'description']
    label = "Register a new milestone"

    custom_widget('dateexpected', DateWidget)

    @action(_('Register milestone'), name='register')
    def register_action(self, action, data):
        """Use the newMilestone method on the context to make a milestone."""
        milestone = self.context.newMilestone(
            name=data.get('name'),
            dateexpected=data.get('dateexpected'),
            description=data.get('description'))
        self.next_url = canonical_url(self.context)

    @property
    def action_url(self):
        return "%s/+addmilestone" % canonical_url(self.context)


class MilestoneEditView(LaunchpadEditFormView):
    """A view for editing milestone properties.

    This view supports editing of properties such as the name, the date it is
    expected to complete, the milestone description, and whether or not it is
    visible (i.e. active).
    """

    schema = IMilestone
    field_names = ['name', 'visible', 'dateexpected', 'description']
    label = "Modify milestone details"

    custom_widget('dateexpected', DateWidget)

    @action(_('Update'), name='update')
    def update_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class MilestoneAdminEditView(LaunchpadEditFormView):
    """A view for administering the milestone.

    This view allows an administrator to change the productseries and
    distroseries.
    """

    schema = IMilestone
    field_names = ['productseries', 'distroseries']
    label = "Modify milestone details"

    @action(_('Update'), name='update')
    def update_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


