# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Browser view for bug contact."""

__metaclass__ = type

__all__ = ['BugContactEditView']


from canonical.launchpad.interfaces import IHasBugContact
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadEditFormView)
from canonical.launchpad.webapp.menu import structured


class BugContactEditView(LaunchpadEditFormView):
    """Browser view class for editing the bug contact."""

    schema = IHasBugContact
    field_names = ['bugcontact']

    @action('Change', name='change')
    def change_action(self, action, data):
        """Redirect to the target page with a success message."""
        target = self.context
        bugcontact = data['bugcontact']
        target.setBugContact(bugcontact, self.user)

        if bugcontact is not None:
            self.request.response.addNotification(structured(
                'Successfully changed the bug supervisor to '
                '<a href="%(contacturl)s">%(displayname)s</a>.'
                '<br />'
                '<a href="%(contacturl)s">%(displayname)s</a> has also been '
                'subscribed to bug notifications for %(targetname)s. '
                '<br />'
                'You can '
                '<a href="%(targeturl)s/+subscribe">'
                'change the subscriptions</a> for '
                '%(targetname)s at any time.',
                contacturl=canonical_url(bugcontact),
                displayname=bugcontact.displayname,
                targetname=self.context.displayname,
                targeturl=canonical_url(self.context)))
        else:
            self.request.response.addNotification(
                "Successfully cleared the bug supervisor. "
                "You can set the bug supervisor again at any time.")

        self.request.response.redirect(canonical_url(target))

    def validate(self, data):
        """Validates the new bug contact.

        The following values are valid as bug contacts:
            * None, indicating that the bug contact field for the target
              should be cleared in change_action().
            * A valid Person (email address or launchpad id).
            * A valid Team of which the current user is an administrator.

        If the the bug contact entered does not meet any of the above criteria
        then the submission will fail and the user will be notified of the
        error.
        """

        # `data` will not have a bugcontact entry in cases where the
        # bugcontact the user entered is valid according to the
        # ValidPersonOrTeam vocabulary
        # (i.e. is not a Person, Team or None).
        if not data.has_key('bugcontact'):
            self.setFieldError(
                'bugcontact',
                'You must choose a valid person or team to be the'
                ' bug supervisor for %s.' %
                self.context.displayname)

            return

        contact = data['bugcontact']

        if (contact is not None and contact.isTeam() and
            contact not in self.user.getAdministratedTeams()):
            error = structured(
                "You cannot set %(team)s as the bug contact for "
                "%(target)s because you are not an administrator of that "
                "team.<br />If you believe that %(team)s should be the bug"
                " supervisor for %(target)s, please notify one of the "
                "<a href=\"%(url)s\">%(team)s administrators</a>.",
                team=contact.displayname,
                target=self.context.displayname,
                url=(canonical_url(contact, rootsite='mainsite') +
                     '/+members'))
            self.setFieldError('bugcontact', error)


