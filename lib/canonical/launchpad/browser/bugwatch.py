# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugWatch-related browser views."""

__metaclass__ = type
__all__ = [
    'BugWatchSetNavigation',
    'BugWatchEditView',
    'BugWatchView']

from zope.component import getUtility
from zope.interface import Interface

from canonical.widgets.textwidgets import URIWidget

from canonical.launchpad import _
from canonical.launchpad.browser import get_comments_for_bugtask
from canonical.launchpad.fields import URIField
from canonical.launchpad.interfaces import (
    IBugWatch, IBugWatchSet, ILaunchBag, ILaunchpadCelebrities,
    NoBugTrackerFound, UnrecognizedBugTrackerURL)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, GetitemNavigation,
    LaunchpadFormView, LaunchpadView)
from canonical.launchpad.webapp.menu import structured


class BugWatchSetNavigation(GetitemNavigation):

    usedfor = IBugWatchSet


class BugWatchView(LaunchpadView):
    """View for displaying a bug watch."""

    schema = IBugWatch

    @property
    def comments(self):
        """Return the comments to be displayed for a bug watch.

        If the current user is not a member of the Launchpad developers
        team, no comments will be returned.
        """
        user = getUtility(ILaunchBag).user
        lp_developers = getUtility(ILaunchpadCelebrities).launchpad_developers
        if not user.inTeam(lp_developers):
            return []

        bug_comments = get_comments_for_bugtask(self.context.bug.bugtasks[0],
            truncate=True)

        # Filter out those comments that don't pertain to this bug
        # watch.
        displayed_comments = []
        for bug_comment in bug_comments:
            if bug_comment.bugwatch == self.context:
                bug_comment.display_if_from_bugwatch = True
                displayed_comments.append(bug_comment)

        return displayed_comments


class BugWatchEditForm(Interface):
    """Form definition for the bug watch edit view."""

    url = URIField(
        title=_('URL'), required=True,
        allowed_schemes=['http', 'https', 'mailto'],
        description=_("The URL at which to view the remote bug, or the "
                      "email address to which this bug has been "
                      "forwarded (as a mailto: URL)."))


class BugWatchEditView(LaunchpadFormView):
    """View for editing a bug watch."""

    schema = BugWatchEditForm
    field_names = ['url']
    custom_widget('url', URIWidget)

    @property
    def initial_values(self):
        """See `LaunchpadFormView.`"""
        return {'url' : self.context.url}

    def validate(self, data):
        """See `LaunchpadFormView.`"""
        if 'url' not in data:
            return
        try:
            bugtracker, bug = getUtility(
                IBugWatchSet).extractBugTrackerAndBug(data['url'])
        except (NoBugTrackerFound, UnrecognizedBugTrackerURL):
            self.setFieldError('url', 'Invalid bug tracker URL.')

    @action('Change', name='change')
    def change_action(self, action, data):
        bugtracker, remote_bug = getUtility(
            IBugWatchSet).extractBugTrackerAndBug(data['url'])
        self.context.bugtracker = bugtracker
        self.context.remotebug = remote_bug

    def bugWatchIsUnlinked(self, action):
        """Return whether the bug watch is unlinked."""
        return self.context.bugtasks.count() == 0

    @action('Delete Bug Watch', name='delete', condition=bugWatchIsUnlinked)
    def delete_action(self, action, data):
        bugwatch = self.context
        self.request.response.addInfoNotification(
            structured(
            'The <a href="%(url)s">%(bugtracker)s #%(remote_bug)s</a>'
            ' bug watch has been deleted.',
            url=bugwatch.url, bugtracker=bugwatch.bugtracker.name,
            remote_bug=bugwatch.remotebug))
        bugwatch.destroySelf()

    @property
    def next_url(self):
        return canonical_url(getUtility(ILaunchBag).bug)
