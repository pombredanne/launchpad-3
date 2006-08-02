# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes for security contacts."""

__metaclass__ = type
__all__ = ["SecurityContactEditView"]

from zope.formlib.form import action

from canonical.launchpad.interfaces import IHasSecurityContact
from canonical.launchpad.webapp import canonical_url, LaunchpadFormView

class SecurityContactEditView(LaunchpadFormView):
    """Browser view for editing the security contact.

    self.context is assumed to implement IHasSecurityContact.
    """

    schema = IHasSecurityContact
    field_names = ['security_contact']

    @property
    def initial_values(self):
        return {
            'security_contact': self.context.security_contact}

    @action(u'Submit', name='submit')
    def handle_submit(self, action, data):
        security_contact = data['security_contact']
        if self.context.security_contact == security_contact:
            return

        self.context.security_contact = security_contact
        if security_contact:
            security_contact_display_value = None
            if security_contact.preferredemail:
                # The security contact was set to a new person or team.
                security_contact_display_value = (
                    security_contact.preferredemail.email)
            else:
                # The security contact doesn't have a preferred email address,
                # so it must be a team.
                assert security_contact.isTeam(), (
                    "Expected security contact with no email address to be a team.")
                security_contact_display_value = security_contact.browsername

            self.request.response.addNotification(
                "Successfully changed the security contact to %s" %
                security_contact_display_value)
        else:
            self.request.response.addNotification(
                "Successfully removed the security contact")

    @property
    def next_url(self):
        return canonical_url(self.context)
