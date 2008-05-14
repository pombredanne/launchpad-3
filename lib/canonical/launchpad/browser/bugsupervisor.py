# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Browser view for bug supervisor."""

__metaclass__ = type

__all__ = ['BugSupervisorEditView']


from canonical.launchpad.interfaces import IHasBugSupervisor
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadEditFormView)
from canonical.launchpad.webapp.menu import structured


class BugSupervisorEditView(LaunchpadEditFormView):
    """Browser view class for editing the bug supervisor."""

    schema = IHasBugSupervisor
    field_names = ['bug_supervisor']

    @action('Change', name='change')
    def change_action(self, action, data):
        """Redirect to the target page with a success message."""
        target = self.context
        bug_supervisor = data['bug_supervisor']
        target.setBugSupervisor(bug_supervisor, self.user)

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
        else:
            self.request.response.addNotification(
                "Successfully cleared the bug supervisor. "
                "You can set the bug supervisor again at any time.")

        self.request.response.redirect(canonical_url(target))

    def validate(self, data):
        """Validates the new bug supervisor.

        The following values are valid as bug supervisors:
            * None, indicating that the bug supervisor field for the target
              should be cleared in change_action().
            * A valid Person (email address or launchpad id).
            * A valid Team of which the current user is an administrator.

        If the the bug supervisor entered does not meet any of the above
        criteria then the submission will fail and the user will be notified
        of the error.
        """

        # `data` will not have a bug_supervisor entry in cases where the
        # bug_supervisor the user entered is valid according to the
        # ValidPersonOrTeam vocabulary
        # (i.e. is not a Person, Team or None).
        if not data.has_key('bug_supervisor'):
            self.setFieldError(
                'bug_supervisor',
                'You must choose a valid person or team to be the'
                ' bug supervisor for %s.' %
                self.context.displayname)

            return

        supervisor = data['bug_supervisor']

        if (supervisor is not None and supervisor.isTeam() and
            supervisor not in self.user.getAdministratedTeams()):
            error = structured(
                "You cannot set %(team)s as the bug supervisor for "
                "%(target)s because you are not an administrator of that "
                "team.<br />If you believe that %(team)s should be the bug"
                " supervisor for %(target)s, please notify one of the "
                "<a href=\"%(url)s\">%(team)s administrators</a>.",
                team=supervisor.displayname,
                target=self.context.displayname,
                url=(canonical_url(supervisor, rootsite='mainsite') +
                     '/+members'))
            self.setFieldError('bug_supervisor', error)


