# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser view for bug supervisor."""

__metaclass__ = type

__all__ = ['BugSupervisorEditView']

from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadEditFormView)
from canonical.launchpad.webapp.menu import structured
from lazr.restful.interface import copy_field
from zope.interface import Interface

from lp.bugs.interfaces.bugsupervisor import IHasBugSupervisor


class BugRoleMixin:

    INVALID_PERSON = object()
    OTHER_USER = object()
    OTHER_TEAM = object()
    OK = object()

    def _getFieldState(self, field_name, data):
        """Return the enum that summarises the field state."""
        # The field_name will not be in the data if the user did not enter
        # a person in the ValidPersonOrTeam vocabulary.
        if field_name not in data:
            return self.INVALID_PERSON
        role = data[field_name]
        user = self.user
        # The user may assign the role to None, himself, or a team he admins.
        if role is None or self.context.userCanAlterSubscription(role, user):
            return self.OK
        # The user is not an admin of the team, or he entered another user.
        if role.isTeam():
            return self.OTHER_TEAM
        else:
            return self.OTHER_USER

    def validateBugSupervisor(self, data):
        """Validates the new bug supervisor.

        Verify that the value is None, the user, or a team he administers,
        otherwise, set a field error.
        """
        field_state = self._getFieldState('bug_supervisor', data)
        if field_state is self.INVALID_PERSON:
            error = (
                'You must choose a valid person or team to be the'
                ' bug supervisor for %s.' % self.context.displayname)
        elif field_state is self.OTHER_TEAM:
            supervisor = data['bug_supervisor']
            error = structured(
                "You cannot set %(team)s as the bug supervisor for "
                "%(target)s because you are not an administrator of that "
                "team.<br />If you believe that %(team)s should be the "
                "bug supervisor for %(target)s, please notify one of the "
                "<a href=\"%(url)s\">%(team)s administrators</a>. See "
                "<a href=\"https://help.launchpad.net/BugSupervisors\">"
                "the help wiki</a> for information about setting a bug "
                "supervisor.",
                team=supervisor.displayname,
                target=self.context.displayname,
                url=(canonical_url(supervisor, rootsite='mainsite') +
                     '/+members'))
        elif field_state is self.OTHER_USER:
            error = structured(
                "You cannot set another person as the bug supervisor for "
                "%(target)s.<br />See "
                "<a href=\"https://help.launchpad.net/BugSupervisors\">"
                "the help wiki</a> for information about setting a bug "
                "supervisor.",
                target=self.context.displayname)
        else:
            # field_state is self.OK.
            return
        self.setFieldError('bug_supervisor', error)

    def changeBugSupervisor(self, bug_supervisor):
        self.context.setBugSupervisor(bug_supervisor, self.user)
        if bug_supervisor is not None:
            self.request.response.addNotification(structured(
                'Successfully changed the bug supervisor to '
                '<a href="%(supervisor_url)s">%(displayname)s</a>.'
                '<br />'
                '<a href="%(supervisor_url)s">%(displayname)s</a> '
                'has also been '
                'subscribed to bug notifications for %(targetname)s. '
                '<br />'
                'You can '
                '<a href="%(targeturl)s/+subscribe">'
                'change the subscriptions</a> for '
                '%(targetname)s at any time.',
                supervisor_url=canonical_url(bug_supervisor),
                displayname=bug_supervisor.displayname,
                targetname=self.context.displayname,
                targeturl=canonical_url(self.context)))


class BugSupervisorEditSchema(Interface):
    """Defines the fields for the edit form.

    This is necessary to make an editable field for bug supervisor as it is
    defined as read-only in the interface to prevent setting it directly.
    """
    bug_supervisor = copy_field(
        IHasBugSupervisor['bug_supervisor'], readonly=False)


class BugSupervisorEditView(BugRoleMixin, LaunchpadEditFormView):
    """Browser view class for editing the bug supervisor."""

    schema = BugSupervisorEditSchema
    field_names = ['bug_supervisor']

    @property
    def label(self):
        """The form label."""
        return 'Edit bug supervisor for %s' % self.context.displayname

    @property
    def page_title(self):
        """The page title."""
        return self.label

    @property
    def adapters(self):
        """See `LaunchpadFormView`"""
        return {BugSupervisorEditSchema: self.context}

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    cancel_url = next_url

    def validate(self, data):
        """See `LaunchpadFormView`."""
        self.validateBugSupervisor(data)

    @action('Change', name='change')
    def change_action(self, action, data):
        """Redirect to the target page with a success message."""
        bug_supervisor = data['bug_supervisor']
        self.changeBugSupervisor(bug_supervisor)
        if bug_supervisor is None:
            self.request.response.addNotification(
                "Successfully cleared the bug supervisor. "
                "You can set the bug supervisor again at any time.")
