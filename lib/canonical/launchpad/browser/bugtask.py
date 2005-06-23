# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from xml.sax.saxutils import escape

from zope.app.traversing.browser import absoluteurl
from zope.interface import implements
from zope.component import getUtility
from zope.app.publisher.browser import BrowserView
from zope.app.form.utility import setUpWidgets, getWidgetsData
from zope.app.form.interfaces import IInputWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import (
    IPersonSet, ILaunchBag, IDistroBugTaskSearch, IUpstreamBugTaskSearch,
    IBugSet, IProduct, IDistribution, IDistroRelease, IUpstreamBugTask,
    IDistroBugTask, IDistroBugTask, IBugTask, IBugTaskSet)
from canonical.lp import dbschema
from canonical.launchpad.interfaces import IBugTaskSearchListingView
from canonical.launchpad.searchbuilder import any, NULL
from canonical.launchpad import helpers
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.bug import BoundPortlet

# Bug Reports
class BugTasksReportView:
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
        return '<input type="text" name="name" value="%s"/>\n' % (
                self.user.name,
                )
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
        for item in dbschema.BugSeverity.items:
            html = html + '<option value="' + str(item.value) + '"'
            if item.value==self.minseverity:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + str(item.title)
            html = html + '</option>\n'
        html = html + '</select>\n'
        return html

    # TODO: replace this with a smart vocabulary and widget
    def prioritySelector(self):
        html = '<select name="minpriority">\n'
        for item in dbschema.BugPriority.items:
            html = html + '<option value="' + str(item.value) + '"'
            if item.value==self.minpriority:
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
        return getUtility(IPersonSet).search(password = NULL)


class ViewWithBugTaskContext:
    def __init__(self, context, request):
        self.request = request
        self.context = context
        setUpWidgets(self, IBugTask, IInputWidget)

    def alsoReportedIn(self):
        """Return a list of IUpstreamBugTasks in which this bug is reported.

        If self.context is an IUpstreamBugTasks, it will be excluded
        from this list.
        """
        return [
            task for task in self.context.bug.bugtasks
            if task.id is not self.context.id]

    def getCCs(self):
        return [
            s for s in self.context.bug.subscriptions
                if s.subscription==dbschema.BugSubscription.CC]

    def getWatches(self):
        return [
            s for s in self.context.bug.subscriptions
                if s.subscription==dbschema.BugSubscription.WATCH]

    def getIgnores(self):
        return [
            s for s in self.context.bug.subscriptions
                if s.subscription==dbschema.BugSubscription.IGNORE]

class BugTaskViewBase:
    """The base class for IBugTask view classes."""

class BugTaskEditView(SQLObjectEditView, BugTaskViewBase):
    pass


class BugTaskDisplayView(BugTaskViewBase):
    """Simple view class that makes bugtask portlets accessible."""


class BugTaskSearchListingView:

    implements(IBugTaskSearchListingView)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.is_maintainer = helpers.is_maintainer(self.context.context)

        if self._upstreamContext():
            self.search_form_schema = IUpstreamBugTaskSearch
        elif self._distributionContext() or self._distroReleaseContext():
            self.search_form_schema = IDistroBugTaskSearch
        else:
            raise TypeError("Unknown context: %s" % repr(self.context.context))

        setUpWidgets(self, self.search_form_schema, IInputWidget)

    def search(self):
        """See canonical.launchpad.interfaces.IBugTaskSearchListingView."""
        search_params = {}

        form_params = getWidgetsData(self, self.search_form_schema)

        searchtext = form_params.get("searchtext")
        if searchtext:
            if searchtext.isdigit():
                # The user wants to jump to a bug with a specific id.
                bug = getUtility(IBugSet).get(int(searchtext))
                self.request.response.redirect(absoluteurl(bug, self.request))
            else:
                # The user wants to filter on certain text.
                search_params["searchtext"] = searchtext

        statuses = form_params.get("status")
        if statuses:
            search_params["status"] = any(*statuses)
        else:
            # The user is likely coming into the form by clicking on a
            # URL (vs. having submitted it with POSTed search
            # criteria), so show NEW and ACCEPTED bugs by default.
            search_params["status"] = any(
                dbschema.BugTaskStatus.NEW, dbschema.BugTaskStatus.ACCEPTED)

        severities = form_params.get("severity")
        if severities:
            search_params["severity"] = any(*severities)

        assignee = form_params.get("assignee")
        if assignee:
            search_params["assignee"] = assignee

        unassigned = form_params.get("unassigned")
        if unassigned:
            if search_params.get("assignee") is not None:
                raise ValueError(
                    "Conflicting search criteria: can't specify an assignee "
                    "to filter on when 'show only unassigned bugs' is checked.")
            search_params["assignee"] = NULL

        milestones = form_params.get("milestone")
        if milestones:
            search_params["milestone"] = any(*milestones)

        search_params["statusexplanation"] = form_params.get(
                "statusexplanation")

        # make this search context-sensitive
        tasks = self.context.search(**search_params)

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

        if helpers.is_maintainer(self.context.context):
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

    def task_columns(self):
        """See canonical.launchpad.interfaces.IBugTaskSearchListingView."""
        return [
            "select", "id", "title", "package", "milestone", "status",
            "submittedby", "assignedto"]

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

    def _upstreamContext(self):
        """Is this page being viewed in an upstream context?

        Return the IProduct if yes, otherwise return None.
        """
        return IProduct(self.context.context, None)

    def _distributionContext(self):
        """Is this page being viewed in a distribution context?

        Return the IDistribution if yes, otherwise return None.
        """
        return IDistribution(self.context.context, None)

    def _distroReleaseContext(self):
        """Is this page being viewed in a distrorelease context?

        Return the IDistroRelease if yes, otherwise return None.
        """
        return IDistroRelease(self.context.context, None)

class BugTaskAbsoluteURL(BrowserView):
    """The view for an absolute URL of a bug task."""
    def __str__(self):
        urlpath = ""
        task = self.context
        if task.product is not None:
            # This is an upstream task.
            urlpath = "/products/%s/+bugs/" % task.product.name
        elif task.distribution is not None:
            # This is a distribution task.
            urlpath = "/distros/%s/+bugs/" % task.distribution.name
        elif task.distrorelease is not None:
            # This is a distrorelease task.
            urlpath = "/distros/%s/%s/+bugs/" % (
                task.distrorelease.distribution.name,
                task.distrorelease.name)

        return "%s%s%d" % (
            self.request.getApplicationURL(),
            urlpath, task.bug.id)


class BugTaskAnorakSearchPageBegoneView:
    """This view simply kicks the user somewhere else.

    Despite being a bit dirty, it's better for /malone/bugs to kick
    the user somewhere else (and *not* the old, scary Anorak search
    page) until we've clearly defined what /malone/bugs would actually
    look like (though that URL might be completely gone before we even
    get to thinking about it. :)
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.request.response.redirect("/malone")
