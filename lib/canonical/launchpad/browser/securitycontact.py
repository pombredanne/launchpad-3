# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes for security contacts."""

__metaclass__ = type
__all__ = ["SecurityContactEditView"]

from canonical.launchpad.webapp import canonical_url

class SecurityContactEditView:
    """Browser view for editing the security contact.

    self.context is assumed to implement IHasSecurityContact.
    """

    @property
    def initial_values(self):
        return {
            'security_contact': self.context.security_contact}

    def process(self, security_contact):
        self.context.security_contact = security_contact
        if security_contact:
            self.request.response.addNotification(
                "Successfully set the security contact to %s" %
                security_contact.preferredemail.email)
        else:
            self.request.response.addNotification(
                "Successfully removed the security contact")

    def nextURL(self):
        return canonical_url(self.context)
