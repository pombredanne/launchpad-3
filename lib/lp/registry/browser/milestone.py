# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Milestone views."""

__metaclass__ = type

__all__ = [
    'MilestoneAddView',
    'MilestoneBreadcrumb',
    'MilestoneContextMenu',
    'MilestoneDeleteView',
    'MilestoneEditView',
    'MilestoneInlineNavigationMenu',
    'MilestoneNavigation',
    'MilestoneOverviewNavigationMenu',
    'MilestoneSetNavigation',
    'MilestoneWithoutCountsView',
    'MilestoneView',
    'ObjectMilestonesView',
    ]


from zope.component import getUtility
from zope.formlib import form
from zope.interface import (
    implements,
    Interface,
    )
from zope.schema import Choice

from canonical.launchpad import _
from canonical.launchpad.webapp import (
    canonical_url,
    enabled_with_permission,
    GetitemNavigation,
    LaunchpadView,
    Navigation,
    )
from canonical.launchpad.webapp.authorization import (
    precache_permission_for_objects,
    )
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.menu import (
    ApplicationMenu,
    ContextMenu,
    Link,
    NavigationMenu,
    )
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.app.widgets.date import DateWidget
from lp.bugs.browser.bugtask import BugTaskListingItem
from lp.bugs.browser.structuralsubscription import (
    expose_structural_subscription_data_to_js,
    StructuralSubscriptionMenuMixin,
    StructuralSubscriptionTargetTraversalMixin,
    )
from lp.bugs.interfaces.bugtask import IBugTaskSet
from lp.registry.browser import (
    get_status_counts,
    RegistryDeleteViewMixin,
    )
from lp.registry.browser import add_subscribe_link
from lp.registry.browser.product import ProductDownloadFileMixin
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.milestone import (
    IMilestone,
    IMilestoneSet,
    IProjectGroupMilestone,
    )
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProduct
from lp.services.propertycache import cachedproperty


class MilestoneSetNavigation(GetitemNavigation):
    """The navigation to traverse to milestones."""
    usedfor = IMilestoneSet


class MilestoneNavigation(Navigation,
    StructuralSubscriptionTargetTraversalMixin):
    """The navigation to traverse to a milestone."""
    usedfor = IMilestone


class MilestoneBreadcrumb(Breadcrumb):
    """The Breadcrumb for an `IMilestone`."""

    @property
    def text(self):
        milestone = IMilestone(self.context)
        if milestone.code_name:
            return '%s "%s"' % (milestone.name, milestone.code_name)
        else:
            return milestone.name


class MilestoneLinkMixin(StructuralSubscriptionMenuMixin):
    """The menu for this milestone."""

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        """The link to edit this milestone."""
        text = 'Change details'
        # ProjectMilestones are virtual milestones and do not have
        # any properties which can be edited.
        enabled = not IProjectGroupMilestone.providedBy(self.context)
        summary = "Edit this milestone"
        return Link(
            '+edit', text, icon='edit', summary=summary, enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def create_release(self):
        """The link to create a release for this milestone."""
        text = 'Create release'
        summary = 'Create a release from this milestone'
        # Releases only exist for products.
        # A milestone can only have a single product release.
        enabled = (IProduct.providedBy(self.context.target)
                   and self.context.product_release is None)
        return Link(
            '+addrelease', text, summary, icon='add', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def delete(self):
        """The link to delete this milestone."""
        text = 'Delete milestone'
        # ProjectMilestones are virtual.
        enabled = not IProjectGroupMilestone.providedBy(self.context)
        summary = "Delete milestone"
        return Link(
            '+delete', text, icon='trash-icon',
            summary=summary, enabled=enabled)


class MilestoneContextMenu(ContextMenu, MilestoneLinkMixin):
    """The menu for this milestone."""
    usedfor = IMilestone

    @cachedproperty
    def links(self):
        links = ['edit']
        add_subscribe_link(links)
        links.append('create_release')
        return links


class MilestoneOverviewNavigationMenu(NavigationMenu, MilestoneLinkMixin):
    """Overview navigation menu for `IMilestone` objects."""
    usedfor = IMilestone
    facet = 'overview'

    @cachedproperty
    def links(self):
        links = ['edit', 'delete']
        add_subscribe_link(links)
        return links


class MilestoneOverviewMenu(ApplicationMenu, MilestoneLinkMixin):
    """Overview  menus for `IMilestone` objects."""
    # This menu must not contain 'subscribe' because the link state is too
    # costly to calculate when this menu is used with a list of milestones.
    usedfor = IMilestone
    facet = 'overview'
    links = ('edit', 'create_release')


class IMilestoneInline(Interface):
    """A marker interface for views that show a milestone inline."""


class MilestoneInlineNavigationMenu(NavigationMenu, MilestoneLinkMixin):
    """An inline navigation menus for milestone views."""
    usedfor = IMilestoneInline
    facet = 'overview'
    links = ('edit', )


class MilestoneView(LaunchpadView, ProductDownloadFileMixin):
    """A View for listing milestones and releases."""
    # XXX sinzui 2009-05-29 bug=381672: Extract the BugTaskListingItem rules
    # to a mixin so that MilestoneView and others can use it.
    implements(IMilestoneInline)
    show_series_context = False

    def __init__(self, context, request):
        """See `LaunchpadView`.

        This view may be used with a milestone or a release. The milestone
        and release (if it exists) are accessible as attributes. The context
        attribute will always be the milestone.

        :param context: `IMilestone` or `IProductRelease`.
        :param request: `ILaunchpadRequest`.
        """
        super(MilestoneView, self).__init__(context, request)
        if IMilestone.providedBy(context):
            self.milestone = context
            self.release = context.product_release
        else:
            self.milestone = context.milestone
            self.release = context
        self.context = self.milestone

    def initialize(self):
        """See `LaunchpadView`."""
        self.form = self.request.form
        self.processDeleteFiles()
        expose_structural_subscription_data_to_js(
            self.context, self.request, self.user)

    @property
    def expire_cache_minutes(self):
        """Active milestone caches expires sooner than non-active ones."""
        if self.milestone.active:
            return 10
        else:
            return 360

    @property
    def should_show_bugs_and_blueprints(self):
        """Display the summary of bugs/blueprints for this milestone?"""
        return self.milestone.active

    @property
    def page_title(self):
        """Return the HTML page title."""
        return self.context.title

    def getReleases(self):
        """See `ProductDownloadFileMixin`."""
        return set([self.release])

    @cachedproperty
    def download_files(self):
        """The release's files as DownloadFiles."""
        if self.release is None or self.release.files.count() == 0:
            return None
        return list(self.release.files)

    # Listify and cache the specifications, ProductReleaseFiles and bugtasks
    # to avoid making the same query over and over again when evaluating in
    # the template.
    @cachedproperty
    def specifications(self):
        """The list of specifications targeted to this milestone."""
        return list(self.context.specifications)

    @cachedproperty
    def product_release_files(self):
        """Files associated with this milestone."""
        return list(self.release.files)

    @cachedproperty
    def _bugtasks(self):
        """The list of non-conjoined bugtasks targeted to this milestone."""
        # Put the results in a list so that iterating over it multiple
        # times in this method does not make multiple queries.
        non_conjoined_slaves = list(
            getUtility(IBugTaskSet).getPrecachedNonConjoinedBugTasks(
                self.user, self.context))
        # Checking bug permissions is expensive. We know from the query that
        # the user has at least launchpad.View on the bugtasks and their bugs.
        # NB: this is in principle unneeded due to injection of permission in
        # the model layer now.
        precache_permission_for_objects(
            self.request, 'launchpad.View', non_conjoined_slaves)
        precache_permission_for_objects(
            self.request, 'launchpad.View',
            [task.bug for task in non_conjoined_slaves])
        # We want the assignees loaded as we show them in the milestone home
        # page.
        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            [bug.assigneeID for bug in non_conjoined_slaves],
            need_validity=True))
        return non_conjoined_slaves

    @cachedproperty
    def _bug_badge_properties(self):
        """The badges for each bug associates with this milestone."""
        return getUtility(IBugTaskSet).getBugTaskBadgeProperties(
            self._bugtasks)

    def _getListingItem(self, bugtask):
        """Return a decorated bugtask for the bug listing."""
        badge_property = self._bug_badge_properties[bugtask]
        return BugTaskListingItem(
            bugtask,
            badge_property['has_branch'],
            badge_property['has_specification'],
            badge_property['has_patch'])

    @cachedproperty
    def bugtasks(self):
        """The list of bugtasks targeted to this milestone for listing."""
        return [self._getListingItem(bugtask) for bugtask in self._bugtasks]

    @property
    def bugtask_count_text(self):
        """The formatted count of bugs for this milestone."""
        count = len(self.bugtasks)
        if count == 1:
            return '1 bug'
        else:
            return '%d bugs' % count

    @property
    def bugtask_status_counts(self):
        """A list StatusCounts summarising the targeted bugtasks."""
        return get_status_counts(self.bugtasks, 'status')

    @property
    def specification_count_text(self):
        """The formatted count of specifications for this milestone."""
        count = len(self.specifications)
        if count == 1:
            return '1 blueprint'
        else:
            return '%d blueprints' % count

    @property
    def specification_status_counts(self):
        """A list StatusCounts summarising the targeted specification."""
        return get_status_counts(self.specifications, 'implementation_status')

    @cachedproperty
    def assignment_counts(self):
        """The counts of the items assigned to users."""
        all_assignments = self.bugtasks + self.specifications
        return get_status_counts(
            all_assignments, 'assignee', key='displayname')

    @cachedproperty
    def user_counts(self):
        """The counts of the items assigned to the currrent user."""
        all_assignments = []
        if self.user:
            for status_count in get_status_counts(
                self.specifications, 'assignee', key='displayname'):
                if status_count.status == self.user:
                    if status_count.count == 1:
                        status_count.status = 'blueprint'
                    else:
                        status_count.status = 'blueprints'
                    all_assignments.append(status_count)
            for status_count in get_status_counts(
                self.bugtasks, 'assignee', key='displayname'):
                if status_count.status == self.user:
                    if status_count.count == 1:
                        status_count.status = 'bug'
                    else:
                        status_count.status = 'bugs'
                    all_assignments.append(status_count)
            return all_assignments
        return all_assignments

    @cachedproperty
    def total_downloads(self):
        """Total downloads of files associated with this milestone."""
        return sum(
            file.libraryfile.hits for file in self.product_release_files)

    @property
    def is_distroseries_milestone(self):
        """Is the current milestone is a distroseries milestone?

        Milestones that belong to distroseries cannot have releases.
        """
        return IDistroSeries.providedBy(self.context.series_target)

    @property
    def is_project_milestone(self):
        """Check, if the current milestone is a project milestone.

        Return true, if the current milestone is a project milestone,
        else return False."""
        return IProjectGroupMilestone.providedBy(self.context)

    @property
    def has_bugs_or_specs(self):
        """Does the milestone have any bugtasks and specifications?"""
        return len(self.bugtasks) > 0 or len(self.specifications) > 0


class MilestoneWithoutCountsView(MilestoneView):
    """Show a milestone in a list of milestones."""

    show_series_context = True
    should_show_bugs_and_blueprints = False


class MilestoneAddView(LaunchpadFormView):
    """A view for creating a new Milestone."""

    schema = IMilestone
    field_names = ['name', 'code_name', 'dateexpected', 'summary']
    label = "Register a new milestone"

    custom_widget('dateexpected', DateWidget)

    @action(_('Register Milestone'), name='register')
    def register_action(self, action, data):
        """Use the newMilestone method on the context to make a milestone."""
        self.context.newMilestone(
            name=data.get('name'),
            code_name=data.get('code_name'),
            dateexpected=data.get('dateexpected'),
            summary=data.get('summary'))
        self.next_url = canonical_url(self.context)

    @property
    def action_url(self):
        """See `LaunchpadFormView`."""
        return "%s/+addmilestone" % canonical_url(self.context)

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)


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
    def cancel_url(self):
        """The context's URL."""
        return canonical_url(self.context)

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
        """Update the milestone."""
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class MilestoneDeleteView(LaunchpadFormView, RegistryDeleteViewMixin):
    """A view for deleting an `IMilestone`."""
    schema = IMilestone
    field_names = []

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def label(self):
        """The form label."""
        return 'Delete %s' % self.context.title

    @cachedproperty
    def bugtasks(self):
        """The list `IBugTask`s targeted to the milestone."""
        return self._getBugtasks(self.context)

    @cachedproperty
    def specifications(self):
        """The list `ISpecification`s targeted to the milestone."""
        return self._getSpecifications(self.context)

    @cachedproperty
    def product_release(self):
        """The `IProductRelease` associated with the milestone."""
        return self._getProductRelease(self.context)

    @cachedproperty
    def product_release_files(self):
        """The list of `IProductReleaseFile`s related to the milestone."""
        return self._getProductReleaseFiles(self.context)

    @action('Delete Milestone', name='delete')
    def delete_action(self, action, data):
        """Delete the milestone anddelete or unlink subordinate objects."""
        # Any associated bugtasks and specifications are untargeted.
        series = self.context.productseries
        name = self.context.name
        self._deleteMilestone(self.context)
        self.request.response.addInfoNotification(
            "Milestone %s deleted." % name)
        self.next_url = canonical_url(series)


class ObjectMilestonesView(LaunchpadView):
    """A view for listing the milestones for any `IHasMilestones` object"""

    label = 'Milestones'

    @cachedproperty
    def milestones(self):
        return list(self.context.all_milestones)
