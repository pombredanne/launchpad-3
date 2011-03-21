# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser view classes for security contacts."""

__metaclass__ = type

__all__ = [
    "SecurityContactEditView",
    ]

from canonical.launchpad.webapp.publisher import canonical_url
from lp.app.browser.launchpadform import (
    action,
    LaunchpadFormView,
    )
from lp.bugs.browser.bugrole import BugRoleMixin
from lp.bugs.interfaces.securitycontact import IHasSecurityContact


class SecurityContactEditView(BugRoleMixin, LaunchpadFormView):
    """Browser view for editing the security contact.

    self.context is assumed to implement IHasSecurityContact.
    """

    schema = IHasSecurityContact
    field_names = ['security_contact']

    @property
    def label(self):
        """See `LaunchpadFormView`."""
        return 'Edit %s security contact' % self.context.displayname

    @property
    def page_title(self):
        """The page title."""
        return self.label

    @property
    def initial_values(self):
        return {
            'security_contact': self.context.security_contact}

    def validate(self, data):
        """See `LaunchpadFormView`."""
        self.validateSecurityContact(data)

    @action('Change', name='change')
    def change_action(self, action, data):
        security_contact = data['security_contact']
        if self.context.security_contact == security_contact:
            return

        self.context.security_contact = security_contact
        if security_contact:
            self.request.response.addNotification(
                "Successfully changed the security contact to %s." %
                security_contact.displayname)
        else:
            self.request.response.addNotification(
                "Successfully removed the security contact.")

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url
