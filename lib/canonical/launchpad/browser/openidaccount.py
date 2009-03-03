# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser code related to Accounts on the OpenID server."""

__metaclass__ = type
__all__ = []


from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.webapp import action, LaunchpadEditFormView


class AccountEditView(LaunchpadEditFormView):
    """Edit account details."""

    schema = IAccount
    field_names = ["displayname"]
    next_url = '/'

    def setUpWidgets(self):
        super(AccountEditView, self).setUpWidgets(context=self.account)

    @action('Change', name='change')
    def change_action(self, action, data):
        """Update the account details."""
        self.updateContextFromData(data, context=self.account)
