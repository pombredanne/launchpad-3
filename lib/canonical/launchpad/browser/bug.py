# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from urlparse import urljoin

from zope.app.publisher.browser import BrowserView
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import (
    ViewPageTemplateFile, BoundPageTemplate)
from zope.interface import implements

from canonical.lp import dbschema, decorates, Passthrough
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    IPerson, ILaunchBag, IBugSet, IBugTaskSet, IDistributionSet, IBugAddForm,
    IBug)
from canonical.lp import dbschema
from canonical.launchpad.database import Person, Bug
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView

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
        return canonical_url(self.context)


class BugEditView(BugView, SQLObjectEditView):
    def __init__(self, context, request):
        BugView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)


class BugAddView(SQLObjectAddView):
    def add(self, content):
        retval = super(BugAddView, self).add(content)
        self.bugadded = content
        return retval

    def nextURL(self):
        return canonical_url(self.bugadded)


class BugAddingView(SQLObjectAddView):
    """A hack for browser:addform's that use IBug as their context.

    Use this class in the class="" of a browser:addform directive
    for IBug.
    """
    def add(self, content):
        return content

    def nextURL(self):
        return "."


class BugAddForm:
    implements(IBugAddForm)
    decorates(IBug, context='bug')

    product = Passthrough('product', 'bugtask')
    sourcepackagename = Passthrough('sourcepackagename', 'bugtask')
    binarypackage = Passthrough('binarypackage', 'bugtask')
    distribution = Passthrough('distribution', 'bugtask')

    def __init__(self, bug):
        # When we add a new bug there should be exactly one task and one
        # message.
        assert len(bug.bugtasks) == 1
        assert len(bug.messages) == 1

        self.bug = bug
        self.bugtask = bug.bugtasks[0]
        self.comment = bug.messages[0]


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
