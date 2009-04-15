# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Milestone views."""

__metaclass__ = type

__all__ = [
    'MilestoneAddView',
    'MilestoneContextMenu',
    'MilestoneDeleteView',
    'MilestoneEditView',
    'MilestoneNavigation',
    'MilestoneOverviewNavigationMenu',
    'MilestoneSetNavigation',
    ]

from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice

from canonical.launchpad import _
from canonical.cachedproperty import cachedproperty

from canonical.launchpad.interfaces.bugtask import BugTaskSearchParams, IBugTaskSet
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.registry.interfaces.milestone import (
    IMilestone, IMilestoneSet, IProjectMilestone)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, ContextMenu, Link,
    LaunchpadEditFormView, LaunchpadFormView, LaunchpadView,
    enabled_with_permission, GetitemNavigation, Navigation, NavigationMenu)

from canonical.widgets import DateWidget


class MilestoneSetNavigation(GetitemNavigation):

    usedfor = IMilestoneSet


# XXX: jamesh 2005-12-14:
# This class is required in order to make use of a side effect of
# Navigation.publishTraverse: adding context objects to
# request.traversed_objects.
class MilestoneNavigation(Navigation):

    usedfor = IMilestone


class MilestoneContextMenu(ContextMenu):

    usedfor = IMilestone

    links = ['edit', 'subscribe', 'publish_release', 'view_release']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        # ProjectMilestones are virtual milestones and do not have
        # any properties which can be edited.
        enabled = not IProjectMilestone.providedBy(self.context)
        return Link('+edit', text, icon='edit', enabled=enabled)

    def subscribe(self):
        enabled = not IProjectMilestone.providedBy(self.context)
        return Link('+subscribe', 'Subscribe to bug mail',
                    icon='edit', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def publish_release(self):
        text = 'Publish release'
        # Releases only exist for products.
        # A milestone can only have a single product release.
        enabled = (not IProjectMilestone.providedBy(self.context)
                   and self.context.product_release is None)
        return Link('+addrelease', text, icon='add', enabled=enabled)

    def view_release(self):
        text = 'View release'
        # Releases only exist for products.
        if (not IProjectMilestone.providedBy(self.context)
            and self.context.product_release is not None):
            enabled = True
            url = canonical_url(self.context.product_release)
        else:
            enabled = False
            url = '.'
        return Link(url, text, enabled=enabled)


class MilestoneOverviewNavigationMenu(NavigationMenu):
    """Overview navigation menus for `IProductSeries` objects."""
    # Suppress the ProductOverviewNavigationMenu from showing on milestones,
    # pages.
    usedfor = IMilestone
    facet = 'overview'
    links = ()


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
        # We could replace all the code below with a simple
        # >>> [task for task in tasks if task.conjoined_master is None]
        # But that'd cause one extra hit to the DB for every bugtask returned
        # by the search above, so we do a single query to get all of a task's
        # siblings here and use that to find whether or not a given bugtask
        # has a conjoined master.
        bugs_and_tasks = getUtility(IBugTaskSet).getBugTasks(
            [task.bug.id for task in tasks])
        non_conjoined_slaves = []
        for task in tasks:
            if task.getConjoinedMaster(bugs_and_tasks[task.bug]) is None:
                non_conjoined_slaves.append(task)
        return non_conjoined_slaves

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
    field_names = ['name', 'dateexpected', 'summary']
    label = "Register a new milestone"

    custom_widget('dateexpected', DateWidget)

    @action(_('Register milestone'), name='register')
    def register_action(self, action, data):
        """Use the newMilestone method on the context to make a milestone."""
        milestone = self.context.newMilestone(
            name=data.get('name'),
            dateexpected=data.get('dateexpected'),
            summary=data.get('summary'))
        self.next_url = canonical_url(self.context)

    @property
    def action_url(self):
        return "%s/+addmilestone" % canonical_url(self.context)


class MilestoneEditView(LaunchpadEditFormView):
    """A view for editing milestone properties.

    This view supports editing of properties such as the name, the date it is
    expected to complete, the milestone description, and whether or not it is
    active.
    """

    schema = IMilestone
    label = "Modify milestone details"

    custom_widget('dateexpected', DateWidget)

    @property
    def field_names(self):
        """See `LaunchpadFormView`.

        There are two series fields, one for for product milestones and the
        other for distribution milestones. The product milestone may change
        its productseries. The distribution milestone may change its
        distroseries.
        """
        names = ['name', 'code_name', 'active', 'dateexpected', 'summary']
        if self.context.product is None:
            # This is a distribution milestone.
            names.append('distroseries')
        else:
            names.append('productseries')
        return names

    def setUpFields(self):
        """See `LaunchpadFormView`.

        The schema permits the series field to be None (required=False) to
        create the milestone, but once a series field is set, None is invalid.
        The choice for the series is redefined to ensure None is not included.
        """
        super(MilestoneEditView, self).setUpFields()
        if self.context.product is None:
            # This is a distribution milestone.
            choice = Choice(
                __name__='distroseries', vocabulary="FilteredDistroSeries")
        else:
            choice = Choice(
                __name__='productseries', vocabulary="FilteredProductSeries")
        choice.title = _("Series")
        choice.description = _("The series for which this is a milestone.")
        field = form.Fields(choice, render_context=self.render_context)
        # Remove the schema's field, then add back the replacement field.
        self.form_fields = self.form_fields.omit(choice.__name__) + field

    @action(_('Update'), name='update')
    def update_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class MilestoneDeleteView(LaunchpadFormView):
    """A view for deleting an `IMilestone`."""
    schema = IMilestone
    field_names = []

    @property
    def label(self):
        """The form label."""
        return 'Delete %s' % self.context.title

    @cachedproperty
    def bugtasks(self):
        """The list `IBugTask`s targeted to the milestone."""
        params = BugTaskSearchParams(milestone=self.context, user=None)
        bugtasks = getUtility(IBugTaskSet).search(params)
        return list(bugtasks)

    @cachedproperty
    def specifications(self):
        """The list `ISpecification`s targeted to the milestone."""
        return list(self.context.specifications)

    @cachedproperty
    def product_release(self):
        """The `IProductRelease` associated with the milestone."""
        return self.context.product_release

    @cachedproperty
    def product_release_files(self):
        """The list of `IProductReleaseFile`s related to the milestone."""
        if self.product_release:
            return list(self.product_release.files)
        else:
            return []

    @action('Delete this Milestone', name='delete')
    def delete_action(self, action, data):
        # Any associated bugtasks and specifications are untargeted.
        for bugtask in self.bugtasks:
            bugtask.milestone = None
        for spec in self.context.specifications:
            spec.milestone = None
        # Any associated product release and its files are deleted.
        for release_file in self.product_release_files:
            release_file.destroySelf()
        if self.product_release is not None:
            self.product_release.destroySelf()
        self.request.response.addInfoNotification(
            "Milestone %s deleted." % self.context.name)
        self.next_url = canonical_url(self.context.productseries)
        self.context.destroySelf()

    @property
    def cancel_url(self):
        return canonical_url(self.context)
