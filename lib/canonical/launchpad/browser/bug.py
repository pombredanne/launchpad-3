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
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView

class BugView:
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


class BugSetView:
    """The default view for /malone/bugs. 

    Essentially, this exists only to allow forms to post IDs here and be
    redirected to the right place.
    """
    def __init__(self, context, request):
        self.request = request
    
    def __call__(self, *args, **kw):
        bug_id = self.request.form.get("id")
        if bug_id:
            return self.request.response.redirect(bug_id)
        return self.request.response.redirect("/malone")


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
