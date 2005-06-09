# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.app.publisher.browser import BrowserView
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import (
    ViewPageTemplateFile, BoundPageTemplate)
from zope.app.form.browser.add import AddView
from zope.interface import implements

from canonical.launchpad.interfaces import (
    IPerson, ILaunchBag, IBugSet, IBugTaskSet, IDistributionSet)
from canonical.lp import dbschema
from canonical.launchpad.database import (
    BugAttachmentSet, BugExternalRefSet, BugSubscriptionSet, BugWatchSet,
    BugProductInfestationSet, BugPackageInfestationSet, Person, Bug,
    BugTasksReport, CVERefSet)
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView

def traverseBug(bug, request, name):
    if name == 'attachments':
        return BugAttachmentSet(bug=bug.id)
    elif name == 'references':
        return BugExternalRefSet(bug=bug.id)
    elif name == 'cverefs':
        return CVERefSet(bug=bug.id)
    elif name == 'people':
        return BugSubscriptionSet(bug=bug.id)
    elif name == 'watches':
        return BugWatchSet(bug=bug.id)
    elif name == 'tasks':
        return getUtility(IBugTaskSet).get(bug.id)
    elif name == 'productinfestations':
        return BugProductInfestationSet(bug=bug.id)
    elif name == 'packageinfestations':
        return BugPackageInfestationSet(bug=bug.id)

    return None


def traverseBugs(bugcontainer, request, name):
    if name == 'assigned':
        return BugTasksReport()
    else:
        return getUtility(IBugSet).get(int(name))

    return None


# TODO: Steve will be hacking on a more general portlet mechanism today
# (2004-12-09)
class BoundPortlet(BoundPageTemplate):
    def __call__(self, *args, **kw):
        return BoundPageTemplate.__call__(self, *args, **kw)


class ViewWithBugContext:
    def __init__(self, view):
        self.request = view.request
        self.context = getUtility(ILaunchBag).bug

    def getCCs(self):
        return [s for s in self.context.subscriptions
                if s.subscription==dbschema.BugSubscription.CC]

    def getWatches(self):
        return [s for s in self.context.subscriptions
                if s.subscription==dbschema.BugSubscription.WATCH]

    def getIgnores(self):
        return [s for s in self.context.subscriptions
                if s.subscription==dbschema.BugSubscription.IGNORE]


class BugPortlet:
    def __init__(self, template_filename):
        self.template = ViewPageTemplateFile(template_filename)

    def __call__(self, view, *args, **kw):
        return self.template(ViewWithBugContext(view), *args, **kw)

    def __get__(self, instance, type=None):
        return BoundPortlet(self, instance)


# TODO: It should be possible to specify all this via ZCML and not require
# the BugView class with its ViewPageTemplateFile attributes
# (I think the browser:view directive allows this already -- stub)
class BugView:
    # TODO
    # The default path for the templates will be
    # lib/canonical/launchpad/templates.
    def __init__(self, context, request):
        self.context = context
        self.request = request

    watchPortlet = BugPortlet(
        '../templates/portlet-bug-watch.pt')
    productInfestationPortlet = BugPortlet(
        '../templates/portlet-bug-productinfestation.pt')
    packageInfestationPortlet = BugPortlet(
        '../templates/portlet-bug-sourcepackageinfestation.pt')
    referencePortlet = BugPortlet(
        '../templates/portlet-bug-reference.pt')
    duplicatesPortlet = BugPortlet(
        '../templates/bug-portlet-duplicates.pt')
    cvePortlet = BugPortlet(
        '../templates/portlet-bug-cve.pt')
    peoplePortlet = BugPortlet(
        '../templates/portlet-bug-people.pt')
    tasksHeadline = BugPortlet(
        '../templates/portlet-bug-tasks-headline.pt')
    actionsPortlet = BugPortlet(
        '../templates/portlet-bug-actions.pt')

    def getCCs(self):
        return [s for s in self.context.subscriptions
                if s.subscription==dbschema.BugSubscription.CC]

    def getWatches(self):
        return [s for s in self.context.subscriptions
                if s.subscription==dbschema.BugSubscription.WATCH]

    def getIgnores(self):
        return [s for s in self.context.subscriptions
                if s.subscription==dbschema.BugSubscription.IGNORE]


class BugAbsoluteURL(BrowserView):
    """The view for an absolute URL of a bug."""
    def __str__(self):
        return "%s%s/%d" % (
            self.request.getApplicationURL(),
            "/malone/bugs", self.context.id)


class BugEditView(BugView, SQLObjectEditView):
    def __init__(self, context, request):
        BugView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)


class BugTaskEditView(BugView, SQLObjectEditView):
    def __init__(self, context, request):
        BugView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)


class BugAddView(AddView):
    def add(self, content):
        retval = super(BugAddView, self).add(content)
        self.bugadded = content
        return retval

    def nextURL(self):
        distribution = getUtility(IDistributionSet).get(self.bugadded.distribution)
        return "/malone/distros/%s" % distribution.name


class BugAddingView(SQLObjectAddView):
    """A hack for browser:addform's that use IBug as their context.

    Use this class in the class="" of a browser:addform directive
    for IBug.
    """
    def add(self, content):
        return content

    def nextURL(self):
        return "."


class BugsCreatedByView:
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getAllPeople(self):
        return Person.select()

    def _getBugsForOwner(self, owner):
        bugs_created_by_owner = []
        if owner:
            persons = Person.select(Person.q.name == owner)
            if persons:
                person = persons[0]
                bugs_created_by_owner = Bug.select(Bug.q.ownerID == person.id)
        else:
            bugs_created_by_owner = Bug.select()

        return bugs_created_by_owner

    def getBugs(self):
        bugs_created_by_owner = self._getBugsForOwner(self.request.get("owner", ""))
        return bugs_created_by_owner
