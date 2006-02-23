# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTask-related browser views."""

__metaclass__ = type

__all__ = [
    'BugTargetTraversalMixin',
    'BugTaskNavigation',
    'BugTaskSetNavigation',
    'BugTaskContextMenu',
    'BugTaskEditView',
    'BugListingPortletView',
    'BugTaskSearchListingView',
    'AssignedBugTasksView',
    'OpenBugTasksView',
    'CriticalBugTasksView',
    'UntriagedBugTasksView',
    'UnassignedBugTasksView',
    'AllBugTasksView',
    'AdvancedBugTaskSearchView',
    'BugTargetView',
    'BugTaskView',
    'BugTaskBackportView',
    'get_sortorder_from_request',
    'BugTargetTextView']

import urllib

from zope.event import notify
from zope.interface import providedBy
from zope.component import getUtility, getView
from zope.app.form.utility import (
    setUpWidgets, getWidgetsData, applyWidgetsChanges)
from zope.app.form.interfaces import IInputWidget, WidgetsError
from zope.schema.interfaces import IList

from canonical.config import config
from canonical.lp import dbschema
from canonical.launchpad.webapp import (
    canonical_url, GetitemNavigation, Navigation, stepthrough,
    redirection, LaunchpadView)
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import (
    ILaunchBag, IDistroBugTaskSearch, IUpstreamBugTaskSearch, IBugSet,
    IProduct, IDistribution, IDistroRelease, IBugTask, IBugTaskSet,
    IDistroReleaseSet, ISourcePackageNameSet, IBugTaskSearch, BugTaskSearchParams,
    IUpstreamBugTask, IDistroBugTask, IDistroReleaseBugTask, IPerson,
    INullBugTask, IBugAttachmentSet, IBugExternalRefSet, IBugWatchSet,
    NotFoundError, IDistributionSourcePackage, ISourcePackage,
    IPersonBugTaskSearch, UNRESOLVED_BUGTASK_STATUSES)
from canonical.launchpad.searchbuilder import any, NULL
from canonical.launchpad import helpers
from canonical.launchpad.event.sqlobjectevent import SQLObjectModifiedEvent
from canonical.launchpad.browser.bug import BugContextMenu
from canonical.launchpad.interfaces.bugtarget import BugDistroReleaseTargetDetails
from canonical.launchpad.components.bugtask import NullBugTask
from canonical.launchpad.webapp.generalform import GeneralFormView



def get_sortorder_from_request(request):
    """Get the sortorder from the request."""
    if request.get("orderby"):
        return request.get("orderby").split(",")
    else:
        # No sort ordering specified, so use a reasonable default.
        return ["-priority", "-severity"]


class BugTargetTraversalMixin:
    """Mix-in in class that provides .../+bug/NNN traversal."""

    redirection('+bug', '+bugs')

    @stepthrough('+bug')
    def traverse_bug(self, name):
        """Traverses +bug portions of URLs"""
        return self._get_task_for_context(name)

    def _get_task_for_context(self, name):
        """Return the IBugTask for this name in this context.

        If the bug has been reported, but not in this specific context, a
        NullBugTask will be returned.

        Raises NotFoundError if no bug with the given name is found.

        If the context type does provide IProduct, IDistribution,
        IDistroRelease, ISourcePackage or IDistributionSourcePackage
        a TypeError is raised.
        """
        context = self.context

        # Raises NotFoundError if no bug is found
        bug = getUtility(IBugSet).getByNameOrID(name)

        # Loop through this bug's tasks to try and find the appropriate task
        # for this context. We always want to return a task, whether or not
        # the user has the permission to see it so that, for example, an
        # anonymous user is presented with a login screen at the correct URL,
        # rather than making it look as though this task was "not found",
        # because it was filtered out by privacy-aware code.
        for bugtask in helpers.shortlist(bug.bugtasks):
            if bugtask.target == context:
                return bugtask

        # If we've come this far, it means that no actual task exists in this
        # context, so we'll return a null bug task. This makes it possible to,
        # for example, return a bug page for a context in which the bug hasn't
        # yet been reported.
        if IProduct.providedBy(context):
            null_bugtask = NullBugTask(bug=bug, product=context)
        elif IDistribution.providedBy(context):
            null_bugtask = NullBugTask(bug=bug, distribution=context)
        elif IDistributionSourcePackage.providedBy(context):
            null_bugtask = NullBugTask(
                bug=bug, distribution=context.distribution,
                sourcepackagename=context.sourcepackagename)
        elif IDistroRelease.providedBy(context):
            null_bugtask = NullBugTask(bug=bug, distrorelease=context)
        elif ISourcePackage.providedBy(context):
            null_bugtask = NullBugTask(
                bug=bug, distrorelease=context.distrorelease,
                sourcepackagename=context.sourcepackagename)
        else:
            raise TypeError(
                "Unknown context type for bug task: %s" % repr(context))

        return null_bugtask


class BugTaskNavigation(Navigation):

    usedfor = IBugTask

    def traverse(self, name):
        # Are we traversing to the view or edit status page of the
        # bugtask? If so, and the task actually exists, return the
        # appropriate page. If the task doesn't yet exist (i.e. it's a
        # NullBugTask), then return a 404. In other words, the URL:
        #
        #   /products/foo/+bug/1/+viewstatus
        #
        # will return the +viewstatus page if bug 1 has actually been
        # reported in "foo". If bug 1 has not yet been reported in "foo",
        # a 404 will be returned.
        if name in ("+viewstatus", "+editstatus"):
            if INullBugTask.providedBy(self.context):
                # The bug has not been reported in this context.
                return None
            else:
                # The bug has been reported in this context.
                return getView(self.context, name + "-page", self.request)

    @stepthrough('attachments')
    def traverse_attachments(self, name):
        if name.isdigit():
            return getUtility(IBugAttachmentSet)[name]

    @stepthrough('references')
    def traverse_references(self, name):
        if name.isdigit():
            return getUtility(IBugExternalRefSet)[name]

    @stepthrough('watches')
    def traverse_watches(self, name):
        if name.isdigit():
            return getUtility(IBugWatchSet)[name]

    redirection('watches', '..')
    redirection('references', '..')


class BugTaskSetNavigation(GetitemNavigation):

    usedfor = IBugTaskSet


class BugTaskContextMenu(BugContextMenu):
    usedfor = IBugTask


class BugTaskView:
    """View class for presenting information about an IBugTask."""

    def __init__(self, context, request):
        # Make sure we always have the current bugtask.
        if not IBugTask.providedBy(context):
            self.context = getUtility(ILaunchBag).bugtask
        else:
            self.context = context

        self.request = request
        self.notices = []

    def handleSubscriptionRequest(self):
        """Subscribe or unsubscribe the user from the bug, if requested."""
        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user

        # establish if a subscription form was posted
        newsub = self.request.form.get('subscribe', None)
        if newsub and self.user and self.request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.bug.subscribe(self.user)
                self.notices.append("You have been subscribed to this bug.")
            elif newsub == 'Unsubscribe':
                self.context.bug.unsubscribe(self.user)
                self.notices.append("You have been unsubscribed from this bug.")

    def reportBugInContext(self):
        form = self.request.form
        fake_task = self.context
        if form.get("reportbug"):
            # The user has requested that the bug be reported in this
            # context.
            if IUpstreamBugTask.providedBy(fake_task):
                # Create a real upstream task in this context.
                real_task = getUtility(IBugTaskSet).createTask(
                    bug=fake_task.bug, owner=getUtility(ILaunchBag).user,
                    product=fake_task.product)
            elif IDistroBugTask.providedBy(fake_task):
                # Create a real distro bug task in this context.
                real_task = getUtility(IBugTaskSet).createTask(
                    bug=fake_task.bug, owner=getUtility(ILaunchBag).user,
                    distribution=fake_task.distribution,
                    sourcepackagename=fake_task.sourcepackagename)
            elif IDistroReleaseBugTask.providedBy(fake_task):
                # Create a real distro release bug task in this context.
                real_task = getUtility(IBugTaskSet).createTask(
                    bug=fake_task.bug, owner=getUtility(ILaunchBag).user,
                    distrorelease=fake_task.distrorelease,
                    sourcepackagename=fake_task.sourcepackagename)
            else:
                raise TypeError(
                    "Unknown bug task type: %s" % repr(fake_task))

            self.context = real_task

            # Add an appropriate feedback message
            self.notices.append("Thank you for your bug report.")

    def isReportedInContext(self):
        """Is the bug reported in this context? Returns True or False.

        This is particularly useful for views that may render a
        NullBugTask.
        """
        return self.context.datecreated is not None

    def alsoReportedIn(self):
        """Return a list of IUpstreamBugTasks in which this bug is reported.

        If self.context is an IUpstreamBugTasks, it will be excluded
        from this list.
        """
        return [
            task for task in self.context.bug.bugtasks
            if task.id is not self.context.id]

    def isReleaseTargetableContext(self):
        """Is the context something that supports release targeting?

        Returns True or False.
        """
        return (
            IDistroBugTask.providedBy(self.context) or
            IDistroReleaseBugTask.providedBy(self.context))


class BugTaskBackportView:
    """View class for targeting bugs to IDistroReleases."""

    @property
    def release_target_details(self):
        """Return a list of BugDistroReleaseTargetDetails objects.

        Releases are filtered to only include distributions relevant
        to the context.distribution or .distrorelease (whichever is
        not None.)

        If the context does not provide IDistroBugTask or
        IDistroReleaseBugTask, a TypeError is raised.
        """
        # Ensure we have what we need.
        distribution = None
        context = self.context
        if IDistroBugTask.providedBy(context):
            distribution = context.distribution
        elif IDistroReleaseBugTask.providedBy(context):
            distribution = context.distrorelease.distribution
        else:
            raise TypeError(
                "retrieving related releases: need IDistroBugTask or "
                "IDistribution, found %s" % type(context))

        # First, let's gather the already-targeted
        # IDistroReleaseBugTasks relevant to this context.
        distro_release_tasks = {}
        for bugtask in context.bug.bugtasks:
            if not IDistroReleaseBugTask.providedBy(bugtask):
                continue

            release_targeted = bugtask.distrorelease
            if release_targeted.distribution == distribution:
                distro_release_tasks[release_targeted] = bugtask

        release_target_details = []
        sourcepackagename = bugtask.sourcepackagename
        for possible_target in distribution.releases:
            # Exclude the current release from this list, because it doesn't
            # make sense to "backport a fix" to the current release.
            if possible_target == distribution.currentrelease:
                continue

            if sourcepackagename is not None:
                sourcepackage = possible_target.getSourcePackage(
                    sourcepackagename)
            else:
                sourcepackage = None
            bug_distrorelease_target_details = BugDistroReleaseTargetDetails(
                release=possible_target, sourcepackage=sourcepackage)

            if possible_target in distro_release_tasks:
                # This release is already a target for this bugfix, so
                # let's grab some more data about this task.
                task = distro_release_tasks[possible_target]

                bug_distrorelease_target_details.istargeted = True
                bug_distrorelease_target_details.assignee = task.assignee
                bug_distrorelease_target_details.status = task.status

            release_target_details.append(bug_distrorelease_target_details)

        return release_target_details

    def createBackportTasks(self):
        """Create distrorelease-targeted tasks for this bug."""
        form = self.request.form

        if not form.get("savetargets"):
            # The form doesn't look like it was submitted; nothing to
            # do here.
            return

        targets = form.get("target")
        if not isinstance(targets, (list, tuple)):
            targets = [targets]

        bugtask = self.context
        bug = bugtask.bug

        # Grab the distribution, for use in looking up distro releases
        # by name later on.
        if IDistroBugTask.providedBy(bugtask):
            distribution = bugtask.distribution
        else:
            distribution = bugtask.distrorelease.distribution

        for target in targets:
            if target is None:
                # If the user didn't change anything a single target
                # with the value of None is submitted, so just skip. 
                continue
            # A target value looks like 'warty.mozilla-firefox'. If
            # there was no specific sourcepackage targeted, it would
            # look like 'warty.'. 
            if "." in target:
                # We need to ensure we split into two parts, because 
                # some packages names contains dots.
                releasename, spname = target.split(".", 1)
                spname = getUtility(ISourcePackageNameSet).queryByName(spname)
            else:
                releasename = target
                spname = None
            release = getUtility(IDistroReleaseSet).queryByName(
                distribution, releasename)

            if not release:
                raise ValueError(
                    "Failed to locate matching IDistroRelease: %s" %
                    releasename)

            user = getUtility(ILaunchBag).user
            assert user is not None, 'Not logged in'
            getUtility(IBugTaskSet).createTask(
                    bug=bug, owner=user, distrorelease=release,
                    sourcepackagename=spname)

        # Redirect the user back to the task form.
        self.request.response.redirect(canonical_url(bugtask))


class BugTaskEditView(GeneralFormView):
    """The view class used for the task +editstatus page."""
    def __init__(self, context, request):
        GeneralFormView.__init__(self, context, request)

        # A simple hack, which avoids the mind-bending Z3 form/widget
        # complexity, to provide the user a useful error message if they make a
        # change comment but don't change anything.
        self.comment_on_change_error = ""

    @property
    def initial_values(self):
        """See canonical.launchpad.webapp.generalform.GeneralFormView."""
        field_values = {}
        for name in self.fieldNames:
            field_values[name] = getattr(self.context, name)

        return field_values

    def validate(self, data):
        """See canonical.launchpad.webapp.generalform.GeneralFormView."""
        bugtask = self.context
        comment_on_change = self.request.form.get("comment_on_change")
        if comment_on_change:
            # There was a comment on this change, so make sure that a
            # change was actually made.
            changed = False
            for field_name in data:
                current_value = getattr(bugtask, field_name)
                if current_value != data[field_name]:
                    changed = True
                    break

            if not changed:
                self.comment_on_change_error = (
                    "You provided a change comment without changing anything.")
                # Pass the comment_on_change_error as a list here, because
                # WidgetsError expects a list of errors.
                raise WidgetsError([self.comment_on_change_error])

        return data

    def process(self):
        """See canonical.launchpad.webapp.generalform.GeneralFormView."""
        bugtask = self.context
        new_values = getWidgetsData(self, self.schema, self.fieldNames)

        bugtask_before_modification = helpers.Snapshot(
            bugtask, providing=providedBy(bugtask))
        changed = applyWidgetsChanges(
            self, self.schema, target=bugtask, names=self.fieldNames)

        comment_on_change = self.request.form.get("comment_on_change")

        # The statusexplanation field is being display as a "Comment on most
        # recent change" field now, so set it to the current change comment if
        # there is one, otherwise clear it out.
        if comment_on_change:
            # Add the change comment as a comment on the bug.
            bugtask.bug.newMessage(
                owner=getUtility(ILaunchBag).user,
                subject=bugtask.bug.followup_subject(),
                content=comment_on_change,
                publish_create_event=False)

            bugtask.statusexplanation = comment_on_change
        else:
            bugtask.statusexplanation = ""

        if changed:
            notify(
                SQLObjectModifiedEvent(
                    object=bugtask,
                    object_before_modification=bugtask_before_modification,
                    edited_fields=self.fieldNames,
                    comment_on_change=comment_on_change))

    def nextURL(self):
        """See canonical.launchpad.webapp.generalform.GeneralFormView."""
        return canonical_url(self.context)


class BugListing:
    """Helper class for information about a bug listing.

        :target: the IBugTarget
        :displayname: the name that will be displayed in the portlet
        :name: the name of the page, e.g. +bugs-open
        :request: the IBrowserRequest
        :require_login: whether login is required to view the page

    The number of bugtasks in the buglisting will be calculated.
    """

    def __init__(self, target, displayname, name, request, require_login=False):
        listing_view = getView(target, name, request)
        listing_view.initialize()

        self.displayname = displayname
        self.url = canonical_url(target) + '/' + name
        self.count = listing_view.unfilteredTaskCount
        self.require_login = require_login


class BugListingPortletView(LaunchpadView):
    """Portlet containing all available bug listings."""

    @property
    def buglistings(self):
        request = self.request
        context = self.context
        require_login = self.user is None
        return [
            BugListing(context, 'All open bugs', '+bugs-open', request),
            BugListing(
                context, 'Assigned to me', '+bugs-assigned-to', request,
                require_login=require_login),
            BugListing(context, 'Critical', '+bugs-critical', request),
            BugListing(context, 'Untriaged', '+bugs-untriaged', request),
            BugListing(context, 'Unassigned', '+bugs-unassigned', request),
            BugListing(context, 'All bugs ever reported', '+bugs-all', request),
            ]


def getInitialValuesFromSearchParams(search_params, form_schema):
    """Build a dictionary that can be given as initial values to
    setUpWidgets, based on the given search params.

    >>> initial = getInitialValuesFromSearchParams(
    ...     {'status': any(*UNRESOLVED_BUGTASK_STATUSES)}, IBugTaskSearch)
    >>> [status.name for status in initial['status']]
    ['UNCONFIRMED', 'CONFIRMED', 'INPROGRESS', 'NEEDSINFO']

    >>> initial = getInitialValuesFromSearchParams(
    ...     {'status': dbschema.BugTaskStatus.REJECTED}, IBugTaskSearch)
    >>> [status.name for status in initial['status']]
    ['REJECTED']

    >>> initial = getInitialValuesFromSearchParams(
    ...     {'severity': [dbschema.BugTaskSeverity.CRITICAL,
    ...                   dbschema.BugTaskSeverity.MAJOR]}, IBugTaskSearch)
    >>> [severity.name for severity in initial['severity']]
    ['CRITICAL', 'MAJOR']

    >>> getInitialValuesFromSearchParams(
    ...     {'assignee': NULL}, IBugTaskSearch)
    {'assignee': None}
    """
    initial = {}
    for key, value in search_params.items():
        if IList.providedBy(form_schema[key]):
            if isinstance(value, any):
                value = value.query_values
            elif isinstance(value, (list, tuple)):
                value = value
            else:
                value = [value]
        elif value == NULL:
            value = None
        else:
            # Should be safe to pass value as it is to setUpWidgets, no need
            # to worry
            pass

        initial[key] = value

    return initial

class BugTaskSearchListingView(LaunchpadView):
    """Base class for bug listings.

    Subclasses should define getExtraSearchParams() to filter the
    search.
    """

    def __init__(self, context, request):
        LaunchpadView.__init__(self, context, request)
        # The initial values to be used when setting up the widgets of this 
        # page.
        self.initial_values = {}

    def initialize(self):
        #XXX: The base class should have a simple schema containing only
        #     the search form. Sub classes, like
        #     AdvancedBugTaskSearchView should use a seperate schema if
        #     they need to. -- Bjorn Tillenius, 2005-09-29
        if self._upstreamContext():
            self.search_form_schema = IUpstreamBugTaskSearch
        elif (self._distributionContext()
              or self._distroReleaseContext()
              or self._sourcePackageContext()
              or self._distroSourcePackageContext()):
            self.search_form_schema = IDistroBugTaskSearch
        elif self._personContext():
            self.search_form_schema = IPersonBugTaskSearch
        else:
            raise TypeError("Unknown context: %s" % repr(self.context))

        setUpWidgets(self, self.search_form_schema, IInputWidget,
                     initial=self.initial_values)

    @property
    def unfilteredTaskCount(self):
        """The number of tasks an empty search will return."""
        # We need to pass in batch_start, so it doesn't use a value from
        # the request.
        return self.search(searchtext='', batch_start=0).batch.total()

    def showTableView(self):
        """Should the search results be displayed as a table?"""
        return False

    def showListView(self):
        """Should the search results be displayed as a list?"""
        return True

    def shouldShowAssignee(self):
        """Should we show the assignee in the list of results?"""
        return True

    def getExtraSearchParams(self):
        """Return extra search parameters to filter the bug list.

        The search parameters should be returned as a dict with the
        corresponding BugTaskSearchParams attribute name as the key.
        """
        return {}

    def search(self, searchtext=None, batch_start=None, context=None):
        """Return an IBatchNavigator for the GET search criteria.

        If :searchtext: is None, the searchtext will be gotten from the
        request.
        """
        form_params = getWidgetsData(self, self.search_form_schema)
        search_params = BugTaskSearchParams(user=self.user, omit_dupes=True)
        search_params.orderby = get_sortorder_from_request(self.request)

        if searchtext is None:
            searchtext = form_params.get("searchtext")
        if searchtext:
            if searchtext.isdigit():
                # The user wants to jump to a bug with a specific id.
                try:
                    bug = getUtility(IBugSet).get(int(searchtext))
                except NotFoundError:
                    pass
                else:
                    self.request.response.redirect(canonical_url(bug))
            else:
                # The user wants to filter on certain text.
                search_params.searchtext = searchtext

        # Allow subclasses to filter the search.
        extra_params = self.getExtraSearchParams()
        for param_name in extra_params:
            setattr(search_params, param_name, extra_params[param_name])

        # Base classes can provide an explicit search context.
        if not context:
            context = self.context

        tasks = context.searchTasks(search_params)
        if self.showBatchedListing():
            if batch_start is None:
                batch_start = int(self.request.get('batch_start', 0))
            batch = Batch(tasks, batch_start, config.malone.buglist_batch_size)
        else:
            batch = tasks

        return BatchNavigator(batch=batch, request=self.request)

    def shouldShowAdvancedSearchWidgets(self):
        """Return True if the advanced search widgets should be shown."""
        return False

    def shouldShowSearchWidgets(self):
        """Should the search widgets be displayed on this page?"""
        # XXX: It's probably a good idea to hide the search widgets if there's
        # only one batched page of results, but this will have to wait because
        # this patch is already big enough. -- Guilherme Salgado, 2005-11-05.
        return True

    def showBatchedListing(self):
        """Should the listing be batched?"""
        return True

    def assign_to_milestones(self):
        """Assign bug tasks to the given milestone."""
        if self.request.form.get("Assign to Milestone"):
            # Targeting one or more tasks to a milestone can be done only on
            # upstreams by the upstream owner, so let's sanity check this
            # mass-target request.
            assert self._upstreamContext(), (
                "Mass-targeting of bugtasks to milestones is currently only "
                "supported for products")
            assert (self.user is not None and
                    self.user.inTeam(self.context.owner)), \
                    ("You must be logged in to mass-assign bugs to milestones")

        form_params = getWidgetsData(self, self.search_form_schema)
        milestone_assignment = form_params.get('milestone_assignment')
        if milestone_assignment is not None:
            taskids = self.request.form.get('task')
            if taskids:
                if not isinstance(taskids, (list, tuple)):
                    taskids = [taskids]

                bugtaskset = getUtility(IBugTaskSet)
                tasks = [bugtaskset.get(taskid) for taskid in taskids]
                for task in tasks:
                    task.milestone = milestone_assignment

    def mass_edit_allowed(self):
        """Indicates whether the user can edit bugtasks directly on the page.

        At the moment the user can edit only product milestone
        assignments, if the user is an owner of the product.
        """
        return (
            self._upstreamContext() is not None and
            self.user is not None and self.user.inTeam(self.context.owner))

    def task_columns(self):
        """Returns a sequence of column names to be shown in the listing.

        This list may be calculated on the fly, e.g. in the case of a
        listing that allows the user to choose which columns to show
        in the listing.
        """
        upstream_context = self._upstreamContext()
        distribution_context = self._distributionContext()
        distrorelease_context = self._distroReleaseContext()

        if upstream_context:
            upstream_columns = [
                "id", "title", "milestone", "status", "severity", "priority",
                "assignedto"]
            if self.mass_edit_allowed():
                return ["select"] + upstream_columns
            else:
                return upstream_columns
        elif distribution_context or distrorelease_context:
            return [
                "id", "title", "package", "status", "severity", "priority",
                "assignedto"]

    @property
    def release_buglistings(self):
        """Return a buglisting for each release.

        The list is sorted newest release to oldest.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        distribution_context = self._distributionContext()
        distrorelease_context = self._distroReleaseContext()

        if distrorelease_context:
            distribution = distrorelease_context.distribution
        elif distribution_context:
            distribution = distribution_context
        else:
            raise AssertionError, ("release_bug_counts called with "
                                   "illegal context")

        releases = getUtility(IDistroReleaseSet).search(
            distribution=distribution, orderBy="-datereleased")

        return [
            BugListing(release, release.displayname, '+bugs', self.request)
            for release in releases]

    def getSortLink(self, colname):
        """Return a link that can be used to sort results by colname."""
        form = self.request.form
        sortlink = ""
        if form.get("search") is None:
            # There is no search criteria to preserve.
            sortlink = "%s?search=Search&orderby=%s" % (
                str(self.request.URL), colname)
            return sortlink

        # XXX: is it not possible to get the exact request supplied and
        # just sneak a "-" in front of the orderby argument, if it
        # exists? If so, the code below could be a lot simpler.
        #       -- kiko, 2005-08-23

        # There is search criteria to preserve.
        sortlink = str(self.request.URL) + "?"
        for fieldname in form:
            fieldvalue = form.get(fieldname)
            if isinstance(fieldvalue, (list, tuple)):
                fieldvalue = [value.encode("utf-8") for value in fieldvalue]
            else:
                fieldvalue = fieldvalue.encode("utf-8")

            if fieldname != "orderby":
                sortlink += "%s&" % urllib.urlencode(
                    {fieldname : fieldvalue}, doseq=True)

        sorted, ascending = self._getSortStatus(colname)
        if sorted and ascending:
            # If we are currently ascending, revert the direction
            colname = "-" + colname

        sortlink += "orderby=%s" % colname

        return sortlink

    def shouldShowTargetName(self):
        """Should the bug target name be displayed in the list of results?

        This is mainly useful for the listview.
        """
        # It doesn't make sense to show the target name when viewing product
        # bugs.
        if IProduct.providedBy(self.context):
            return False
        else:
            return True

    def getSortClass(self, colname):
        """Return a class appropriate for sorted columns"""
        sorted, ascending = self._getSortStatus(colname)
        if not sorted:
            return ""
        if ascending:
            return "sorted ascending"
        return "sorted descending"

    def _getSortStatus(self, colname):
        """Finds out if the list is sorted by the column specified.

        Returns a tuple (sorted, ascending), where sorted is true if the
        list is currently sorted by the column specified, and ascending
        is true if sorted in ascending order.
        """
        current_sort_column = self.request.form.get("orderby")
        if current_sort_column is None:
            return (False, False)

        ascending = True
        sorted = True
        if current_sort_column.startswith("-"):
            ascending = False
            current_sort_column = current_sort_column[1:]

        if current_sort_column != colname:
            sorted = False

        return (sorted, ascending)

    def _upstreamContext(self):
        """Is this page being viewed in an upstream context?

        Return the IProduct if yes, otherwise return None.
        """
        return IProduct(self.context, None)

    def _personContext(self):
        """Is this page being viewed in a person context?

        Return the IPerson if yes, otherwise return None.
        """
        return IPerson(self.context, None)

    def _distributionContext(self):
        """Is this page being viewed in a distribution context?

        Return the IDistribution if yes, otherwise return None.
        """
        return IDistribution(self.context, None)

    def _distroReleaseContext(self):
        """Is this page being viewed in a distrorelease context?

        Return the IDistroRelease if yes, otherwise return None.
        """
        return IDistroRelease(self.context, None)

    def _sourcePackageContext(self):
        """Is this page being viewed in a [distrorelease] sourcepackage context?

        Return the ISourcePackage if yes, otherwise return None.
        """
        return ISourcePackage(self.context, None)

    def _distroSourcePackageContext(self):
        """Is this page being viewed in a distribution sourcepackage context?

        Return the IDistributionSourcePackage if yes, otherwise return None.
        """
        return IDistributionSourcePackage(self.context, None)

class RedirectToAdvancedBugTasksView(BugTaskSearchListingView):
    """A view that will render the advanced search page if the user requested
    an advanced search form.
    """

    def render(self):
        request = self.request
        if request.form.get('advanced'):
            # The user wants to do an advanced search, let's render the
            # advanced page and keep the predefined values of this search.
            new_view = getView(self.context, '+bugs-advanced', request)
            new_view.initial_values = getInitialValuesFromSearchParams(
                self.getExtraSearchParams(), self.search_form_schema)
            return new_view()
        else:
            return BugTaskSearchListingView.render(self)


class AssignedBugTasksView(RedirectToAdvancedBugTasksView):
    """All open bugs assigned to someone."""

    def getExtraSearchParams(self):
        return {'status': any(*UNRESOLVED_BUGTASK_STATUSES),
                'assignee': self.user}

    def shouldShowAssignee(self):
        """Should we show the assignee in the list of results?"""
        return False


class OpenBugTasksView(RedirectToAdvancedBugTasksView):
    """All open bugs."""

    @property
    def unfilteredTaskCount(self):
        return self.context.open_bugtasks.count()

    def getExtraSearchParams(self):
        return {'status': any(*UNRESOLVED_BUGTASK_STATUSES)}


class CriticalBugTasksView(RedirectToAdvancedBugTasksView):
    """All open critical bugs."""

    @property
    def unfilteredTaskCount(self):
        return self.context.critical_bugtasks.count()

    def getExtraSearchParams(self):
        return {'status': any(*UNRESOLVED_BUGTASK_STATUSES),
                'severity': dbschema.BugTaskSeverity.CRITICAL}


class UntriagedBugTasksView(RedirectToAdvancedBugTasksView):
    """All untriaged bugs.

    Only bugs with status UNCONFIRMED are considered to be untriaged.
    """

    def getExtraSearchParams(self):
        return {'status': dbschema.BugTaskStatus.UNCONFIRMED}


class UnassignedBugTasksView(RedirectToAdvancedBugTasksView):
    """All open bugs that don't have an assignee."""

    @property
    def unfilteredTaskCount(self):
        return self.context.unassigned_bugtasks.count()

    def getExtraSearchParams(self):
        return {'status': any(*UNRESOLVED_BUGTASK_STATUSES), 'assignee': NULL}

    def shouldShowAssignee(self):
        """Should we show the assignee in the list of results?"""
        return False


class AllBugTasksView(RedirectToAdvancedBugTasksView):
    """All bugs ever reported."""


class AdvancedBugTaskSearchView(BugTaskSearchListingView):
    """Advanced search for bugtasks."""

    def getExtraSearchParams(self):
        """Return the extra parameters for a search that used the advanced form.

        This method can also be used to get the extra parameters when a simple
        form is submitted. This allows us to hide the advanced form in some
        pages and still use this method to get the extra params of the
        submitted simple form.
        """
        # Even though we pass self.initial_values to setUpWidgets(), that
        # method won't add anything to the request (obviously), and that's
        # where getWidgetsData() will get the values from. For this reason we
        # update self.initial_values with the return of getWidgetsData().
        form_params = self.initial_values
        form_params.update(getWidgetsData(self, self.search_form_schema))

        search_params = {}
        search_params['statusexplanation'] = form_params.get(
            "statusexplanation")
        search_params['assignee'] = form_params.get("assignee")

        severities = form_params.get("severity")
        if severities:
            search_params['severity'] = any(*severities)

        milestones = form_params.get("milestone")
        if milestones:
            search_params['milestone'] = any(*milestones)

        attachmenttype = form_params.get("attachmenttype")
        if attachmenttype:
            search_params['attachmenttype'] = any(*attachmenttype)

        statuses = form_params.get("status", UNRESOLVED_BUGTASK_STATUSES)
        if statuses is not None:
            search_params['status'] = any(*statuses)

        unassigned = form_params.get("unassigned")
        if unassigned:
            # If the user both inputs an assignee, and chooses to show
            # only unassigned bugs, he will get all unassigned bugs.
            search_params['assignee'] = NULL

        # This reversal with include_dupes and omit_dupes is a bit odd;
        # the reason to do this is that from the search UI's viewpoint,
        # including a dupe is the special case, whereas a
        # BugTaskSet.search() method that omitted dupes silently would
        # be a source of surprising bugs.
        if form_params.get("include_dupes"):
            search_params['omit_dupes'] = False
        else:
            search_params['omit_dupes'] = True

        return search_params

    def shouldShowAdvancedSearchWidgets(self):
        return True

    def hasSimpleMode(self):
        """Does this view has a "simple" mode where only a small subset of
        widgets are displayed?

        We need to know this in order to provide a button to switch to that
        mode when we are in the advanced mode.
        """
        return False


class BugTargetView:
    """Used to grab bugs for a bug target; used by the latest bugs portlet"""
    def latestBugTasks(self, quantity=5):
        """Return <quantity> latest bugs reported against this target."""
        params = BugTaskSearchParams(orderby="-datecreated",
                                     user=getUtility(ILaunchBag).user)

        tasklist = self.context.searchTasks(params)
        return tasklist[:quantity]


class BugTargetTextView(LaunchpadView):
    """View for simple text page showing bugs filed against a bug target."""

    def render(self):
        self.request.response.setHeader('Content-type', 'text/plain')
        tasks = self.context.searchTasks(BugTaskSearchParams(self.user))

        # We use task.bugID rather than task.bug.id here as the latter
        # would require an extra query per task.
        return u''.join('%d\n' % task.bugID for task in tasks)

