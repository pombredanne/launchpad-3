# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes for security contacts."""

__metaclass__ = type
__all__ = ["SecurityContactEditView"]

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.generalform import GeneralFormView

class SecurityContactEditView(GeneralFormView):
    """Browser view for editing the security contact.

    self.context is assumed to implement IHasSecurityContact.
    """

    @property
    def initial_values(self):
        return {
            'security_contact': self.context.security_contact}

    def process(self, security_contact):
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

    def nextURL(self):
        return canonical_url(self.context)
