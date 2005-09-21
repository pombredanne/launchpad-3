# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BugView',
    'BugSetView',
    'BugEditView',
    'BugAddView',
    'BugAddingView',
    'BugLinkView',
    'BugUnlinkView',
    'BugRelatedObjectAddView',
    'BugRelatedObjectEditView',
    'DeprecatedAssignedBugsView']

import urllib

from zope.interface import implements
from zope.component import getUtility
from zope.app.form.browser.add import AddView

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    IBug, ILaunchBag, IBugSet, IBugLinkTarget, IBugCve)
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.form import FormView


class BugView:
    """The view for the main bug page"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.notices = []

        # figure out who the user is for this transaction
        self.user = getUtility(ILaunchBag).user

        # establish if a subscription form was posted
        newsub = request.form.get('subscribe', None)
        if newsub is not None and self.user and request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this bug.")
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this bug.")

    @property
    def subscription(self):
        """establish if this user has a subscription"""
        if self.user is None:
            return None
        for subscription in self.context.subscriptions:
            if subscription.person.id == self.user.id:
                return subscription
        return None


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

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class BugAddView(SQLObjectAddView):
    """View for adding a bug."""

    def add(self, content):
        self.bugadded = content
        return content

    def create(self, **kw):
        """"Create a new bug."""
        return getUtility(IBugSet).createBug(**kw)

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


class BugLinkView(FormView):
    """This view will be used for objects that support IBugLinkTarget, and
    so can be linked and unlinked from bugs.
    """

    schema = IBugCve
    fieldNames = ['bug']
    _arguments = ['bug']

    def process(self, bug):
        # we are not creating, but we need to find the bug from the bug num
        malone_bug = getUtility(IBugSet).get(bug)
        user = getUtility(ILaunchBag).user
        assert IBugLinkTarget.providedBy(self.context)
        return self.context.linkBug(malone_bug, user)

    def nextURL(self):
        return canonical_url(self.context)


class BugUnlinkView(FormView):
    """This view will be used for objects that support IBugLinkTarget, and
    thus can be unlinked from bugs.
    """

    schema = IBugCve
    fieldNames = ['bug']
    _arguments = ['bug']

    def process(self, bug):
        malone_bug = getUtility(IBugSet).get(bug)
        user = getUtility(ILaunchBag).user
        return self.context.unlinkBug(malone_bug, user)

    def nextURL(self):
        return canonical_url(self.context)


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


