# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BugView',
    'BugSetView',
    'BugEditView',
    'BugAddView',
    'BugAddingView',
    'BugAddForm',
    'BugRelatedObjectAddView',
    'BugRelatedObjectEditView',
    'DeprecatedAssignedBugsView']

import urllib

from zope.interface import implements
from zope.component import getUtility

from canonical.lp import dbschema, decorates, Passthrough
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import IBugAddForm, IBug, ILaunchBag
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView

class BugView:
    """The view for the main bug page"""
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
    def redirectToBug(self):
        bug_id = self.request.form.get("id")
        if bug_id:
            return self.request.response.redirect(bug_id)
        return self.request.response.redirect("/malone")


class BugEditView(BugView, SQLObjectEditView):
    """The view for the edit bug page"""
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


class BugRelatedObjectAddView(SQLObjectAddView):
    """View class for add views of bug-related objects.

    Examples would include the add cve page, the add subscription
    page, etc.
    """
    def __init__(self, context, request):
        SQLObjectAddView.__init__(self, context, request)
        self.bug = getUtility(ILaunchBag).bug


class BugRelatedObjectEditView(SQLObjectEditView):
    """View class for edit views of bug-related object.

    Examples would include the edit cve page, edit subscription page,
    etc.
    """
    def __init__(self, context, request):
        SQLObjectEditView.__init__(self, context, request)
        self.bug = getUtility(ILaunchBag).bug

    def changed(self):
        """Redirect to the bug page."""
        self.request.response.redirect(canonical_url(self.bug))


class DeprecatedAssignedBugsView:
    """Deprecate the /malone/assigned namespace.

    It's important to ensure that this namespace continues to work, to
    prevent linkrot, but since FOAF seems to be a more natural place
    to put the assigned bugs report, we'll redirect to the appropriate
    FOAF URL.
    """
    def __init__(self, context, request):
        """Redirect the user to their assigned bugs report."""
        self.context = context
        self.request = request

    def redirect_to_assignedbugs(self):
        self.request.response.redirect(
            canonical_url(getUtility(ILaunchBag).user) +
            "/+assignedbugs")
