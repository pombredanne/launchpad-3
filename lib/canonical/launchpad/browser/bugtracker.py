# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug tracker views."""

__metaclass__ = type

__all__ = [
    'BugTrackerSetNavigation',
    'BugTrackerContextMenu',
    'BugTrackerSetContextMenu',
    'BugTrackerView',
    'BugTrackerSetView',
    'BugTrackerAddView',
    'BugTrackerEditView',
    'BugTrackerNavigation',
    'RemoteBug',
    ]

from itertools import chain

from zope.interface import implements
from zope.component import getUtility
from zope.app.form.browser import TextAreaWidget
from zope.formlib import form
from zope.schema import Choice

from canonical.cachedproperty import cachedproperty
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad import _
from canonical.launchpad.helpers import english_list, shortlist
from canonical.launchpad.interfaces import (
    BugTrackerType, IBugTracker, IBugTrackerSet, ILaunchBag,
    ILaunchpadCelebrities, IRemoteBug)
from canonical.launchpad.webapp import (
    ContextMenu, GetitemNavigation, LaunchpadEditFormView, LaunchpadFormView,
    LaunchpadView, Link, Navigation, action, canonical_url, custom_widget,
    redirection, structured)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.widgets import DelimitedListWidget


# A set of bug tracker types for which there can only ever be one bug
# tracker.
SINGLE_INSTANCE_TRACKERS = (
    BugTrackerType.DEBBUGS,
    BugTrackerType.SAVANNAH,
    BugTrackerType.SOURCEFORGE,
    )

# A set of bug tracker types that we should not allow direct creation
# of.
NO_DIRECT_CREATION_TRACKERS = (
    SINGLE_INSTANCE_TRACKERS + (
        BugTrackerType.EMAILADDRESS,))


class BugTrackerSetNavigation(GetitemNavigation):

    usedfor = IBugTrackerSet

    def breadcrumb(self):
        return 'Remote Bug Trackers'


class BugTrackerContextMenu(ContextMenu):

    usedfor = IBugTracker

    links = ['edit']

    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')


class BugTrackerSetContextMenu(ContextMenu):

    usedfor = IBugTrackerSet

    links = ['newbugtracker']

    def newbugtracker(self):
        text = 'Register another bug tracker'
        return Link('+newbugtracker', text, icon='add')


class BugTrackerAddView(LaunchpadFormView):

    schema = IBugTracker
    label = "Register an external bug tracker"
    field_names = ['name', 'bugtrackertype', 'title', 'summary',
                   'baseurl', 'contactdetails']

    def setUpWidgets(self, context=None):
        # We only show those bug tracker types for which there can be
        # multiple instances in the bugtrackertype Choice widget.
        vocab_items = [
            item for item in BugTrackerType.items.items
                if item not in NO_DIRECT_CREATION_TRACKERS]
        fields = []
        for field_name in self.field_names:
            if field_name == 'bugtrackertype':
                fields.append(form.FormField(
                    Choice(__name__='bugtrackertype',
                           title=_('Bug Tracker Type'),
                           values=vocab_items,
                           default=BugTrackerType.BUGZILLA)))
            else:
                fields.append(self.form_fields[field_name])
        self.form_fields = form.Fields(*fields)
        super(BugTrackerAddView, self).setUpWidgets(context=context)

    @action(_('Add'), name='add')
    def add(self, action, data):
        """Create the IBugTracker."""
        btset = getUtility(IBugTrackerSet)
        bugtracker = btset.ensureBugTracker(
            name=data['name'],
            bugtrackertype=data['bugtrackertype'],
            title=data['title'],
            summary=data['summary'],
            baseurl=data['baseurl'],
            contactdetails=data['contactdetails'],
            owner=getUtility(ILaunchBag).user)
        self.next_url = canonical_url(bugtracker)


class BugTrackerSetView(LaunchpadView):
    """View for actions on the bugtracker index pages."""
    PILLAR_LIMIT = 3

    def initialize(self):
        self.bugtrackers = list(self.context)
        bugtrackerset = getUtility(IBugTrackerSet)
        # The caching of bugtracker pillars here avoids us hitting the
        # database multiple times for each bugtracker.
        self._pillar_cache = bugtrackerset.getPillarsForBugtrackers(
            self.bugtrackers)

    def getPillarData(self, bugtracker):
        """Return dict of pillars and booleans indicating ellipsis.

        In more detail, the dictionary holds a list of products/projects
        and a boolean determining whether or not there we omitted
        pillars by truncating to PILLAR_LIMIT.

        If no pillars are mapped to this bugtracker, returns {}.
        """
        if bugtracker not in self._pillar_cache:
            return {}
        pillars = self._pillar_cache[bugtracker]
        if len(pillars) > self.PILLAR_LIMIT:
            has_more_pillars = True
        else:
            has_more_pillars = False
        return {
            'pillars': pillars[:self.PILLAR_LIMIT],
            'has_more_pillars': has_more_pillars
        }


class BugTrackerView(LaunchpadView):

    usedfor = IBugTracker

    def initialize(self):
        self.batchnav = BatchNavigator(self.context.watches, self.request)

    @property
    def related_projects(self):
        """Return all project groups and projects.

        This property was created for the Related projects portlet in
        the bug tracker's page.
        """
        return shortlist(chain(self.context.projects,
                               self.context.products), 100)


class BugTrackerEditView(LaunchpadEditFormView):

    schema = IBugTracker
    field_names = ['name', 'title', 'bugtrackertype',
                   'summary', 'baseurl', 'aliases', 'contactdetails']

    custom_widget('summary', TextAreaWidget, width=30, height=5)
    custom_widget('aliases', DelimitedListWidget, height=3)

    def validate(self, data):
        # Normalise aliases to an empty list if it's None.
        if data.get('aliases') is None:
            data['aliases'] = []

        # If aliases has an error, unwrap the Dantean exception from
        # Zope so that we can tell the user something useful.
        if self.getFieldError('aliases'):
            # XXX: GavinPanella 2008-04-02 bug=210901: The error
            # messages may already be escaped (with `cgi.escape`), but
            # the water is muddy, so we won't attempt to unescape them
            # or otherwise munge them, in case we introduce a
            # different problem. For now, escaping twice is okay as we
            # won't see any artifacts of that during normal use.
            aliases_errors = self.widgets['aliases']._error.errors.args[0]
            self.setFieldError('aliases', structured(
                    '<br />'.join(['%s'] * len(aliases_errors)),
                    *aliases_errors))

    @action('Change', name='change')
    def change_action(self, action, data):
        # If the baseurl is going to change, save the current baseurl
        # as an alias. Users attempting to use this URL, which is
        # presumably incorrect or out-of-date, will be captured.
        current_baseurl = self.context.baseurl
        requested_baseurl = data['baseurl']
        if requested_baseurl != current_baseurl:
            data['aliases'].append(current_baseurl)

        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

    @cachedproperty
    def delete_not_possible_reasons(self):
        """A list of reasons why the context cannot be deleted.

        An empty list means that there are no reasons, so the delete
        can go ahead.
        """
        reasons = []
        celebrities = getUtility(ILaunchpadCelebrities)

        # We go through all of the conditions why the bug tracker
        # can't be deleted, and record reasons for all of them. We do
        # this so that users can discover the logic behind the
        # decision, and try something else, seek help, or give up as
        # appropriate. Just showing the first problem would stop users
        # from being able to help themselves.

        # Check that no products or projects use this bugtracker.
        pillars = (
            getUtility(IBugTrackerSet).getPillarsForBugtrackers(
                [self.context]).get(self.context, []))
        if len(pillars) > 0:
            reasons.append(
                'This is the bug tracker for %s.' % english_list(
                    sorted(pillar.title for pillar in pillars)))

        # Only admins and registry experts can delete bug watches en
        # masse.
        if self.context.watches.count() > 0:
            admin_teams = [celebrities.admin, celebrities.registry_experts]
            for team in admin_teams:
                if self.user.inTeam(team):
                    break
            else:
                reasons.append(
                    'There are linked bug watches and only members of %s '
                    'can delete them en masse.' % english_list(
                        sorted(team.title for team in admin_teams)))

        # Bugtrackers with imported messages cannot be deleted.
        if self.context.imported_bug_messages.count() > 0:
            reasons.append(
                'Bug comments have been imported via this bug tracker.')

        # If the bugtracker is a celebrity then we protect it from
        # deletion.
        celebrities_set = set(
            getattr(celebrities, name)
            for name in ILaunchpadCelebrities.names())
        if self.context in celebrities_set:
            reasons.append(
                'This bug tracker is protected from deletion.')

        return reasons

    def delete_condition(self, action):
        return len(self.delete_not_possible_reasons) == 0

    @action('Delete', name='delete', condition=delete_condition)
    def delete_action(self, action, data):
        # First unlink bug watches from all bugtasks, flush updates,
        # then delete the watches themselves.
        for watch in self.context.watches:
            for bugtask in watch.bugtasks:
                if len(bugtask.bug.bugtasks) < 2:
                    raise AssertionError(
                        'There should be more than one bugtask for a bug '
                        'when one of them is linked to the original bug via '
                        'a bug watch.')
                bugtask.bugwatch = None
        flush_database_updates()
        for watch in self.context.watches:
            watch.destroySelf()

        # Now delete the aliases and the bug tracker itself.
        self.context.aliases = []
        self.context.destroySelf()

        # Hey, it worked! Tell the user.
        self.request.response.addInfoNotification(
            '%s has been deleted.' % (self.context.title,))

        # Go back to the bug tracker listing.
        self.next_url = canonical_url(getUtility(IBugTrackerSet))


class BugTrackerNavigation(Navigation):

    usedfor = IBugTracker

    def breadcrumb(self):
        return self.context.title

    def traverse(self, remotebug):
        bugs = self.context.getBugsWatching(remotebug)
        if len(bugs) == 0:
            # no bugs watching => not found
            return None
        elif len(bugs) == 1:
            # one bug watching => redirect to that bug
            return redirection(canonical_url(bugs[0]))
        else:
            # else list the watching bugs
            return RemoteBug(self.context, remotebug, bugs)


class RemoteBug:
    """Represents a bug in a remote bug tracker."""

    implements(IRemoteBug)

    def __init__(self, bugtracker, remotebug, bugs):
        self.bugtracker = bugtracker
        self.remotebug = remotebug
        self.bugs = bugs

    @property
    def title(self):
        return 'Remote Bug #%s in %s' % (self.remotebug,
                                         self.bugtracker.title)

