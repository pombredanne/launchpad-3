# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugTask-related browser views."""

__metaclass__ = type

__all__ = [
    'BugTargetTraversalMixin',
    'BugTaskNavigation',
    'BugTaskSetNavigation',
    'BugTaskContextMenu',
    'BugTaskEditView',
    'BugTaskPortletView',
    'BugListingPortletView',
    'BugTaskSearchListingView',
    'BugTargetView',
    'BugTaskView',
    'BugTaskBackportView',
    'get_sortorder_from_request',
    'BugTargetTextView']

import urllib

from zope.event import notify
from zope.interface import providedBy
from zope.schema.vocabulary import getVocabularyRegistry
from zope.component import getUtility, getView
from zope.app.form import CustomWidgetFactory
from zope.app.form.utility import (
    setUpWidgets, setUpDisplayWidgets, getWidgetsData, applyWidgetsChanges)
from zope.app.form.interfaces import IInputWidget, WidgetsError
from zope.schema.interfaces import IList
from zope.security.proxy import isinstance as zope_isinstance

from canonical.config import config
from canonical.lp import dbschema
from canonical.launchpad.webapp import (
    canonical_url, GetitemNavigation, Navigation, stepthrough,
    redirection, LaunchpadView)
from canonical.launchpad.interfaces import (
    ILaunchBag, IBugSet, IProduct, IDistribution, IDistroRelease, IBugTask,
    IBugTaskSet, IDistroReleaseSet, ISourcePackageNameSet, IBugTaskSearch,
    BugTaskSearchParams, IUpstreamBugTask, IDistroBugTask,
    IDistroReleaseBugTask, IPerson, INullBugTask, IBugAttachmentSet,
    IBugExternalRefSet, IBugWatchSet, NotFoundError, IDistributionSourcePackage,
    ISourcePackage, IPersonBugTaskSearch, UNRESOLVED_BUGTASK_STATUSES,
    valid_distrotask, valid_upstreamtask, BugDistroReleaseTargetDetails)
from canonical.launchpad.searchbuilder import any, NULL
from canonical.launchpad import helpers
from canonical.launchpad.event.sqlobjectevent import SQLObjectModifiedEvent
from canonical.launchpad.browser.bug import BugContextMenu
from canonical.launchpad.components.bugtask import NullBugTask
from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.launchpad.webapp.batching import TableBatchNavigator
from canonical.database.sqlbase import flush_database_updates

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
                # Security proxy this object on the way out.
                return getUtility(IBugTaskSet).get(bugtask.id)

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


class BugTaskView(LaunchpadView):
    """View class for presenting information about an IBugTask."""

    def __init__(self, context, request):
        LaunchpadView.__init__(self, context, request)

        # Make sure we always have the current bugtask.
        if not IBugTask.providedBy(context):
            self.context = getUtility(ILaunchBag).bugtask
        else:
            self.context = context

        self.notices = []

    def process(self):
        """Process changes to the bug page.

        These include potentially changing bug branch statuses and
        adding a comment.
        """
        if not "save" in self.request:
            return

        # Process the comment, if one was added.
        form = self.request.form
        comment = form.get("comment")
        subject = form.get("subject")

        if comment:
            self.context.bug.newMessage(
                subject=subject, content=comment, owner=self.user)

    def handleSubscriptionRequest(self):
        """Subscribe or unsubscribe the user from the bug, if requested."""
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

    def isReleaseTargetableContext(self):
        """Is the context something that supports release targeting?

        Returns True or False.
        """
        return (
            IDistroBugTask.providedBy(self.context) or
            IDistroReleaseBugTask.providedBy(self.context))


class BugTaskPortletView:
    def alsoReportedIn(self):
        """Return a list of IUpstreamBugTasks in which this bug is reported.

        If self.context is an IUpstreamBugTasks, it will be excluded
        from this list.
        """
        return [
            task for task in self.context.bug.bugtasks
            if task.id is not self.context.id]


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
        # complexity, to provide the user a useful error message if
        # they make a change comment but don't change anything.
        self.comment_on_change_error = ""

    @property
    def initial_values(self):
        """See canonical.launchpad.webapp.generalform.GeneralFormView."""
        field_values = {}
        for name in self.fieldNames:
            field_values[name] = getattr(self.context, name)

        return field_values

    def _setUpWidgets(self):
        """Set up the bug task status edit widgets."""
        # Set up the milestone widget as an input widget only if the has
        # launchpad.Edit permissions on the distribution, for distro tasks, or
        # launchpad.Edit permissions on the product, for upstream tasks.
        milestone_context = (
            self.context.product or self.context.distribution or
            self.context.distrorelease.distribution)

        field_names = list(self.fieldNames)
        if (("milestone" in field_names) and not
            helpers.check_permission("launchpad.Edit", milestone_context)):
            # The user doesn't have permission to edit the milestone, so render
            # a read-only milestone widget.
            field_names.remove("milestone")
            setUpDisplayWidgets(self, self.schema, names=["milestone"])

        setUpWidgets(
            self, self.schema, IInputWidget, names=field_names,
            initial=self.initial_values)

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
        distro = bugtask.distribution
        sourcename = bugtask.sourcepackagename
        product = bugtask.product
        if distro is not None and sourcename != data['sourcepackagename']:
            valid_distrotask(bugtask.bug, distro, data['sourcepackagename'])
        if product is not None and product != data['product']:
            valid_upstreamtask(bugtask.bug, data['product'])

        return data

    def process(self):
        """See canonical.launchpad.webapp.generalform.GeneralFormView."""
        bugtask = self.context
        # Save the field names we extract from the form in a separate
        # list, because we modify this list of names later if the
        # bugtask is reassigned to a different product.
        field_names = list(self.fieldNames)
        new_values = getWidgetsData(self, self.schema, field_names)

        bugtask_before_modification = helpers.Snapshot(
            bugtask, providing=providedBy(bugtask))

        # If the user is reassigning an upstream task to a different product,
        # we'll clear out the milestone value, to avoid violating DB constraints
        # that ensure an upstream task can't be assigned to a milestone on a
        # different product.
        milestone_cleared = None
        if (IUpstreamBugTask.providedBy(bugtask) and
            (bugtask.product != new_values.get("product")) and
             bugtask.milestone):
            milestone_cleared = bugtask.milestone
            bugtask.milestone = None
            # Remove the "milestone" field from the list of fields whose changes
            # we want to apply, because we don't want the form machinery to try
            # and set this value back to what it was!
            field_names.remove("milestone")

        changed = applyWidgetsChanges(
            self, self.schema, target=bugtask, names=field_names)

        if milestone_cleared:
            self.request.response.addWarningNotification(
                "The bug report for %s was removed from the %s milestone "
                "because it was reassigned to a new product" % (
                    bugtask.targetname, milestone_cleared.displayname))

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
                    edited_fields=field_names,
                    comment_on_change=comment_on_change))

        if (bugtask_before_modification.sourcepackagename !=
            bugtask.sourcepackagename):
            # The source package was changed, so tell the user that we've
            # subscribed the new bug contacts.
            self.request.response.addNotification(
                "The bug contacts for %s have been subscribed to this bug." % (
                    bugtask.targetname))

    def nextURL(self):
        """See canonical.launchpad.webapp.generalform.GeneralFormView."""
        return canonical_url(self.context)


class BugListingPortletView(LaunchpadView):
    """Portlet containing all available bug listings."""
    def getOpenBugsURL(self):
        """Return the URL for open bugs on this bug target."""
        return self.getSearchFilterURL(
            status=[status.title for status in UNRESOLVED_BUGTASK_STATUSES])

    def getBugsAssignedToMeURL(self):
        """Return the URL for bugs assigned to the current user on target."""
        if self.user:
            return self.getSearchFilterURL(assignee=self.user.name)
        else:
            return str(self.request.URL) + "/+login"

    def getBugsAssignedToMeCount(self):
        assert self.user, (
            "Counting 'bugs assigned to me' requires a logged-in user")

        search_params = BugTaskSearchParams(
            user=self.user, assignee=self.user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES))

        return self.context.searchTasks(search_params).count()

    def getCriticalBugsURL(self):
        """Return the URL for critical bugs on this bug target."""
        return self.getSearchFilterURL(
            status=[status.title for status in UNRESOLVED_BUGTASK_STATUSES],
            severity=dbschema.BugTaskSeverity.CRITICAL.title)

    def getUnassignedBugsURL(self):
        """Return the URL for critical bugs on this bug target."""
        return self.getSearchFilterURL(
            status=[status.title for status in UNRESOLVED_BUGTASK_STATUSES],
            unassigned='on')

    def getUnconfirmedBugsURL(self):
        """Return the URL for unconfirmed bugs on this bug target."""
        return self.getSearchFilterURL(
            status=dbschema.BugTaskStatus.UNCONFIRMED.title)

    def getSearchFilterURL(self, **extra_params):
        """Return a URL with search parameters."""
        search_params = []
        if extra_params:
            for param_name, value in sorted(extra_params.items()):
                search_params.append(('field.' + param_name, value))

        query_string = urllib.urlencode(search_params, doseq=True)

        search_filter_url = str(self.request.URL) + "?search=Search"
        if query_string:
            search_filter_url += "&" + query_string

        return search_filter_url


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
    @property
    def columns_to_show(self):
        """Returns a sequence of column names to be shown in the listing."""
        upstream_context = self._upstreamContext()
        distribution_context = self._distributionContext()
        distrorelease_context = self._distroReleaseContext()
        distrosourcepackage_context = self._distroSourcePackageContext()
        sourcepackage_context = self._sourcePackageContext()

        assert (
            upstream_context or distribution_context or
            distrorelease_context or distrosourcepackage_context or
            sourcepackage_context), (
            "Unrecognized context; don't know which report "
            "columns to show.")

        if (upstream_context or distrosourcepackage_context or
            sourcepackage_context):
            return ["id", "summary", "importance", "status"]
        elif distribution_context or distrorelease_context:
            return ["id", "summary", "packagename", "importance", "status"]

    def initialize(self):
        #XXX: The base class should have a simple schema containing only
        #     the search form. Sub classes, like
        #     AdvancedBugTaskSearchView should use a seperate schema if
        #     they need to. -- Bjorn Tillenius, 2005-09-29
        if self._personContext():
            self.schema = IPersonBugTaskSearch
        else:
            self.schema = IBugTaskSearch

        setUpWidgets(self, self.schema, IInputWidget)

    def showTableView(self):
        """Should the search results be displayed as a table?"""
        return False

    def showListView(self):
        """Should the search results be displayed as a list?"""
        return True

    def search(self, searchtext=None, context=None, extra_params=None):
        """Return an ITableBatchNavigator for the GET search criteria.

        If :searchtext: is None, the searchtext will be gotten from the
        request.

        :extra_params: is a dict that provides search params added to the search
        criteria taken from the request. Params in :extra_params: take
        precedence over request params.
        """
        data = {}
        data.update(
            getWidgetsData(
                self, self.schema,
                names=[
                    "searchtext", "status", "assignee", "severity",
                    "priority", "owner", "omit_dupes", "has_patch",
                    "milestone"]))

        if extra_params:
            data.update(extra_params)

        if data:
            searchtext = data.get("searchtext")
            if searchtext and searchtext.isdigit():
                try:
                    bug = getUtility(IBugSet).get(searchtext)
                except NotFoundError:
                    pass
                else:
                    self.request.response.redirect(canonical_url(bug))

            assignee_option = self.request.form.get("assignee_option")
            if assignee_option == "none":
                data['assignee'] = NULL

            has_patch = data.pop("has_patch", False)
            if has_patch:
                data["attachmenttype"] = dbschema.BugAttachmentType.PATCH

        if data.get("omit_dupes") is None:
            # The "omit dupes" parameter wasn't provided, so default to omitting
            # dupes from reports, of course.
            data["omit_dupes"] = True

        if data.get("status") is None:
            # Show only open bugtasks as default
            data['status'] = UNRESOLVED_BUGTASK_STATUSES

        # "Normalize" the form data into search arguments.
        form_values = {}
        for key, value in data.items():
            if zope_isinstance(value, (list, tuple)):
                form_values[key] = any(*value)
            else:
                form_values[key] = value

        # Base classes can provide an explicit search context.
        if not context:
            context = self.context

        search_params = BugTaskSearchParams(user=self.user, **form_values)
        search_params.orderby = get_sortorder_from_request(self.request)
        tasks = context.searchTasks(search_params)

        return TableBatchNavigator(tasks, self.request,
                    columns_to_show=self.columns_to_show,
                    size=config.malone.buglist_batch_size)

    def getWidgetValues(self, vocabulary_name, default_values=()):
        """Return data used to render a field's widget."""
        widget_values = []

        vocabulary_registry = getVocabularyRegistry()
        for term in vocabulary_registry.get(None, vocabulary_name):
            widget_values.append(
                dict(
                    value=term.token, title=term.title or term.token,
                    checked=term.value in default_values))

        return helpers.shortlist(widget_values, longest_expected=10)

    def getStatusWidgetValues(self):
        """Return data used to render the status checkboxes."""
        return self.getWidgetValues(
            vocabulary_name="BugTaskStatus",
            default_values=UNRESOLVED_BUGTASK_STATUSES)

    def getPriorityWidgetValues(self):
        """Return data used to render the priority checkboxes."""
        return self.getWidgetValues(vocabulary_name="BugTaskPriority")

    def getSeverityWidgetValues(self):
        """Return data used to render the severity checkboxes."""
        return self.getWidgetValues("BugTaskSeverity")

    def getMilestoneWidgetValues(self):
        """Return data used to render the milestone checkboxes."""
        return self.getWidgetValues("Milestone")

    def getAdvancedSearchPageHeading(self):
        """The header for the advanced search page."""
        return "Bugs in %s: Advanced Search" % self.context.displayname

    def getAdvancedSearchButtonLabel(self):
        """The Search button for the advanced search page."""
        return "Search bugs in %s" % self.context.displayname

    def getAdvancedSearchActionURL(self):
        """Return a URL to be used as the action for the advanced search."""
        return canonical_url(self.context) + "/+bugs"

    def shouldShowAssigneeWidget(self):
        """Should the assignee widget be shown on the advanced search page?"""
        return True

    def shouldShowReporterWidget(self):
        """Should the reporter widget be shown on the advanced search page?"""
        return True

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

        form_params = getWidgetsData(self, self.schema)
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

        release_buglistings = []
        for release in releases:
            release_buglistings.append(
                dict(
                    title=release.displayname,
                    url=canonical_url(release) + "/+bugs",
                    count=release.open_bugtasks.count()))

        return release_buglistings

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

