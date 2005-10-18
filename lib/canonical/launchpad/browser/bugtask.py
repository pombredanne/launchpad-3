# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTask-related browser views."""

__metaclass__ = type

__all__ = [
    'BugTargetTraversalMixin',
    'BugTaskNavigation',
    'BugTaskSetNavigation',
    'BugTaskContextMenu',
    'BugTasksReportView',
    'BugTaskEditView',
    'BugTaskSearchListingView',
    'BugTargetView',
    'BugTaskView',
    'BugTaskReleaseTargetingView',
    'get_sortorder_from_request']

import urllib

from zope.interface import implements
from zope.component import getUtility, getView
from zope.app.form.utility import setUpWidgets, getWidgetsData
from zope.app.form.interfaces import IInputWidget

from canonical.lp import dbschema
from canonical.launchpad.webapp import (
    canonical_url, Link, GetitemNavigation, Navigation, stepthrough,
    redirection)
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import (
    IPersonSet, ILaunchBag, IDistroBugTaskSearch, IUpstreamBugTaskSearch,
    IBugSet, IProduct, IDistribution, IDistroRelease, IBugTask, IBugTaskSet,
    IDistroReleaseSet, ISourcePackageNameSet, BugTaskSearchParams,
    IUpstreamBugTask, IDistroBugTask, IDistroReleaseBugTask,
    INullBugTask, IBugAttachmentSet, IBugExternalRefSet, IBugWatchSet,
    NotFoundError, IDistributionSourcePackage, ISourcePackage)
from canonical.launchpad.interfaces import IBugTaskSearchListingView
from canonical.launchpad.searchbuilder import any, NULL
from canonical.launchpad import helpers
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.bug import BugContextMenu
from canonical.launchpad.interfaces.bug import BugDistroReleaseTargetDetails
from canonical.launchpad.components.bugtask import NullBugTask

# This shortcut constant indicates what we consider "open"
# (non-terminal) states. XXX: should this be centralized elsewhere?
#       -- kiko, 2005-08-23
STATUS_OPEN = any(dbschema.BugTaskStatus.NEW,
                  dbschema.BugTaskStatus.ACCEPTED)

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
        if name.isdigit():
            return self._get_task_for_context(name)
        raise NotFoundError

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
        # Raises NotFoundError if no bug with that ID exists.
        bug = getUtility(IBugSet).get(name)

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
    def traverse_references(self, name):
        if name.isdigit():
            return getUtility(IBugWatchSet)[name]

    redirection('watches', '..')
    redirection('references', '..')


class BugTaskSetNavigation(GetitemNavigation):

    usedfor = IBugTaskSet


class BugTaskContextMenu(BugContextMenu):
    usedfor = IBugTask


class BugTasksReportView:
    """The view class for the assigned bugs report."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = None

        form = self.request.form
        # default to showing bugs assigned to the logged in user.
        username = form.get('name')
        if username:
            self.user = getUtility(IPersonSet).getByName(username)
        else:
            self.user = getUtility(ILaunchBag).user

        # default to showing even wishlist bugs
        self.minseverity = int(form.get('minseverity', 0))
        self.minpriority = int(form.get('minpriority', 0))
        self.showclosed = form.get('showclosed') == 'yes'

    def productColumns(self):
        return ['id', 'product', 'title', 'severity', 'priority', 'assignee',
                'status', 'target', 'assignedto']

    def packageColumns(self):
        return ['id', 'package', 'title', 'severity', 'priority',
                'assignee', 'status', 'target', 'assignedto']

    def maintainedPackageBugs(self):
        return self.context.maintainedPackageBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    def maintainedProductBugs(self):
        return self.context.maintainedProductBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    def packageAssigneeBugs(self):
        return self.context.packageAssigneeBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    def productAssigneeBugs(self):
        return self.context.productAssigneeBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    def assignedBugs(self):
        return self.context.assignedBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    # TODO: replace this with a smart vocabulary and widget
    def userSelector(self):
        if self.user:
            name = self.user.name
        else:
            name = ""
        return '<input type="text" name="name" value="%s"/>\n' % name
        # Don't do this - when you have 60000+ people it tends to kill
        # the production server.
        # html = '<select name="name">\n'
        # for person in self.allPeople():
        #     html = html + '<option value="'+person.name+'"'
        #     if person==self.user:
        #         html = html + ' selected="yes"'
        #     html = html + '>'
        #     html = html + person.browsername + '</option>\n'
        # html = html + '</select>\n'
        # return html

    # TODO: replace this with a smart vocabulary and widget
    def severitySelector(self):
        html = '<select name="minseverity">\n'
        for item in dbschema.BugTaskSeverity.items:
            html = html + '<option value="' + str(item.value) + '"'
            if item.value == self.minseverity:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + str(item.title)
            html = html + '</option>\n'
        html = html + '</select>\n'
        return html

    # TODO: replace this with a smart vocabulary and widget
    def prioritySelector(self):
        html = '<select name="minpriority">\n'
        for item in dbschema.BugTaskPriority.items:
            html = html + '<option value="' + str(item.value) + '"'
            if item.value == self.minpriority:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + str(item.title)
            html = html + '</option>\n'
        html = html + '</select>\n'
        return html

    def showClosedSelector(self):
        html = ('<input type="checkbox" id="showclosed" '
                'name="showclosed" value="yes"')
        if self.showclosed:
            html = html + ' checked="yes"'
        html = html + ' />'
        return html

    def allPeople(self):
        # XXX: We should be using None, not NULL outside of database code.
        #      -- Steve Alexander, 2005-04-22
        return getUtility(IPersonSet).search(password=NULL)


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
            self.notices.append(
                "Successfully opened bug #%d in %s" % (
                real_task.bug.id, real_task.targetname))

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


class BugTaskReleaseTargetingView:
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

    def createTargetedTasks(self):
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
            # look like 'warty.'
            if "." in target:
                releasename, spname = target.split(".")
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
            getUtility(IBugTaskSet).createTask(
                    bug=bug, owner=user, distrorelease=release,
                    sourcepackagename=spname)

        # Redirect the user back to the task form.
        self.request.response.redirect(canonical_url(bugtask)) 


class BugTaskEditView(SQLObjectEditView):
    """The view class used for the task +edit page"""

    def changed(self):
        """Redirect the browser to the bug page when we successfully update
        the bug task."""
        self.request.response.redirect(canonical_url(self.context))


class BugTaskSearchListingView:

    implements(IBugTaskSearchListingView)

    def showTableView(self):
        """Should the search results be displayed as a table?"""
        return False

    def showListView(self):
        """Should the search results be displayed as a list?"""
        return True

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

        if self._upstreamContext():
            self.search_form_schema = IUpstreamBugTaskSearch
        elif self._distributionContext() or self._distroReleaseContext():
            self.search_form_schema = IDistroBugTaskSearch
        else:
            raise TypeError("Unknown context: %s" % repr(self.context))

        setUpWidgets(self, self.search_form_schema, IInputWidget)

    def search(self):
        """See canonical.launchpad.interfaces.IBugTaskSearchListingView."""

        form_params = getWidgetsData(self, self.search_form_schema)
        search_params = BugTaskSearchParams(user=self.user)

        search_params.statusexplanation = form_params.get("statusexplanation")
        search_params.assignee = form_params.get("assignee")

        search_params.orderby = get_sortorder_from_request(self.request)

        severities = form_params.get("severity")
        if severities:
            search_params.severity = any(*severities)

        milestones = form_params.get("milestone")
        if milestones:
            search_params.milestone = any(*milestones)

        attachmenttype = form_params.get("attachmenttype")
        if attachmenttype:
            search_params.attachmenttype = any(*attachmenttype)

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

        statuses = form_params.get("status", None)
        if statuses is not None:
            search_params.status = any(*statuses)
        elif (self.request.form.get('advanced') or
              self.request.form.get('any-status')):
            # The advanced search form always provides explicit
            # statuses; the any-status bit is a hack to allow us to
            # generate URLs to the basic search that display bugs in any
            # status. XXX: should this be cleaned up to make the status
            # /always/ explicit?
            #   -- kiko, 2005-08-23
            pass
        else:
            # The basic search form always uses the open statuses by
            # default
            search_params.status = STATUS_OPEN

        unassigned = form_params.get("unassigned")
        if unassigned:
            if search_params.assignee is not None:
                raise ValueError(
                    "Conflicting search criteria: can't specify an assignee "
                    "to filter on when 'show only unassigned bugs' is checked.")
            search_params.assignee = NULL

        # This reversal with include_dupes and omit_dupes is a bit odd;
        # the reason to do this is that from the search UI's viewpoint,
        # including a dupe is the special case, whereas a
        # BugTaskSet.search() method that omitted dupes silently would
        # be a source of surprising bugs.
        if form_params.get("include_dupes"):
            search_params.omit_dupes = False
        else:
            search_params.omit_dupes = True

        tasks = self.context.searchTasks(search_params)
        return BatchNavigator(
            batch=Batch(tasks, int(self.request.get('batch_start', 0))),
            request=self.request)


    def assign_to_milestones(self):
        """Assign bug tasks to the given milestone."""
        if not self._upstreamContext():
            # The context is not an upstream, so, since the only
            # context that currently supports milestones is upstream,
            # there's nothing to do here.
            return

        if helpers.is_maintainer(self.context):
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
                        # XXX: When spiv fixes so that proxied objects
                        #      can be assigned to a SQLBase '.id' can be
                        #      removed. -- Bjorn Tillenius, 2005-05-04
                        task.milestone = milestone_assignment.id

    def mass_edit_allowed(self):
        """Indicates whether the user can edit bugtasks directly on the page.

        At the moment the user can edit only product milestone
        assignments, if the user is a maintainer of the product.
        """
        return (
            self._upstreamContext() is not None and
            helpers.is_maintainer(self.context))

    def task_columns(self):
        """See canonical.launchpad.interfaces.IBugTaskSearchListingView."""
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

    def advanced(self):
        """Should the form be rendered in advanced search mode?"""
        marker = object()
        form = self.request.form
        if form.get('advanced_submit', marker) is not marker:
            return True
        if form.get('simple_submit', marker) is not marker:
            return False
        if form.get('advanced', 0):
            return True
        return False
    advanced = property(advanced)

    @property
    def critical_count(self):
        """Return the number of critical bugs filed in a context.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        critical = dbschema.BugTaskSeverity.CRITICAL
        return self._countTasks(status=STATUS_OPEN,
                                severity=critical, user=self.user,
                                omit_dupes=True)

    @property
    def critical_count_filter_url(self):
        """Construct and return the URL for all critical bugs.

        The URL is context-aware.
        """
        return (
            str(self.request.URL) +
            "?field.status%3Alist=New&field.status%3Alist=Accepted&" +
            "field.severity%3Alist=Critical&search=Search")

    @property
    def assigned_to_me_count(self):
        """Return the number of bugs assigned to the user in this context.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        return self._countTasks(assignee=self.user, user=self.user,
                                status=STATUS_OPEN, omit_dupes=True)

    @property
    def assigned_to_me_count_filter_url(self):
        """Construct and return the URL that shows just bugs assigned to me.

        The URL is context-aware.
        """
        return (
            str(self.request.URL) +
            "?field.status%3Alist=New&field.status%3Alist=Accepted&" +
            "field.assignee=" + self.user.name + "&search=Search")

    @property
    def untriaged_count(self):
        """Return the number of untriaged bugs in this context.

        'Untriaged' simply means IBugTask.status == NEW.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        return self._countTasks(status=dbschema.BugTaskStatus.NEW,
                                user=self.user, omit_dupes=True)

    @property
    def untriaged_count_filter_url(self):
        """Construct and return the URL that shows just untriaged bugs.

        The URL is context-aware.
        """
        return str(self.request.URL) + "?field.status%3Alist=New&search=Search"

    @property
    def unassigned_count(self):
        """Return the unassigned bugs filed in this context.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        return self._countTasks(assignee=NULL, user=self.user, omit_dupes=True,
                                status=STATUS_OPEN)

    @property
    def unassigned_count_filter_url(self):
        """Construct and return the URL that shows just the unassigned tasks.

        The URL is context-aware.
        """
        return (
            str(self.request.URL) +
            "?field.status%3Alist=New&field.status%3Alist=Accepted&" +
            "field.status-empty-marker=1&field.severity-empty-marker=1&" +
            "field.assignee=&field.unassigned.used=&field.unassigned=on&" +
            "search=Search")

    @property
    def total_open_count(self):
        """Return the total number of bugs filed in this context.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        return self._countTasks(user=self.user, status=STATUS_OPEN,
                                omit_dupes=True)

    @property
    def total_open_count_filter_url(self):
        """Construct and return the URL that shows all open bugs.

        The URL is context-aware. Note that the basic bug search listing
        only displays open bugs, which is why we don't need to specify
        any status here.
        """
        return str(self.request.URL) + "?search=Search"
    
    @property
    def total_count(self):
        """Return the total number of bugs filed in this context.

        The count only considers bugs that the user would actually be
        able to see in a listing.
        """
        return self._countTasks(user=self.user, omit_dupes=True)

    @property
    def total_count_filter_url(self):
        """Construct and return the URL that shows all bugs.

        The URL is context-aware.
        """
        # See search() for details on the any-status hack
        return str(self.request.URL) + "?any-status=1&search=Search"

    @property
    def advanced_url(self):
        """Construct and return the URL that gets you to the advanced search.

        The URL is context-aware.
        """
        return str(self.request.URL) + "?advanced=Advanced"

    @property
    def release_bug_counts(self):
        """Return a list of release bug counts.

        Each list element is a dict of the form:

        {"releasename" : releasename, "bugcount" : bugcount, "url" : url}

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
            distribution=distribution, isreleased=True, orderBy="-datereleased")

        release_bugs = []
        for release in releases:
            bugcount = self._countTasks(user=self.user, status=STATUS_OPEN, 
                                        omit_dupes=True)
            release_bugs.append({
                "releasename" : release.displayname,
                "bugcount" : bugcount,
                "url" : canonical_url(release) + '/+bugs'})

        return release_bugs

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

    def shouldShowPackageName(self):
        """See canonical.launchpad.interfaces.IBugTaskSearchListingView."""
        target = self.context

        # It only makes sense to show the sourcepackage name when viewing
        # distribution or distrorelease bugs.
        if (IDistribution.providedBy(target) or
            IDistroRelease.providedBy(target)):
            return True
        else:
            return False

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

    def _countTasks(self, **kwargs):
        search_params = BugTaskSearchParams(**kwargs)
        tasks = self.context.searchTasks(search_params)
        return tasks.count()

    def _upstreamContext(self):
        """Is this page being viewed in an upstream context?

        Return the IProduct if yes, otherwise return None.
        """
        return IProduct(self.context, None)

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


class BugTargetView:
    """Used to grab bugs for a bug target; used by the latest bugs portlet"""
    def latestBugTasks(self, quantity=5):
        """Return <quantity> latest bugs reported against this target."""
        params = BugTaskSearchParams(orderby="-datecreated",
                                     user=getUtility(ILaunchBag).user)

        tasklist = self.context.searchTasks(params)
        return tasklist[:quantity]

