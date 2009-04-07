# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser code related to Accounts on the OpenID server."""

__metaclass__ = type
__all__ = []


from zope.component import getUtility

from canonical.widgets import PasswordChangeWidget

from canonical.launchpad import _

from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.interfaces.launchpad import IPasswordEncryptor
from lp.registry.interfaces.person import IPersonChangePassword
from canonical.launchpad.webapp import (
    action, custom_widget, LaunchpadEditFormView, LaunchpadFormView)


class AccountEditView(LaunchpadEditFormView):
    """Edit account details."""

    schema = IAccount
    label = 'Change your personal details'
    field_names = ["displayname"]
    next_url = '/'

    def setUpWidgets(self):
        super(AccountEditView, self).setUpWidgets(context=self.account)

    @action('Change', name='change')
    def change_action(self, action, data):
        """Update the account details."""
        self.updateContextFromData(data, context=self.account)


class AccountPasswordEditview(LaunchpadFormView):
    """Change the account's password."""

    schema = IPersonChangePassword
    label = 'Change your password'
    next_url = '/'
    field_names = ['currentpassword', 'password']
    custom_widget('password', PasswordChangeWidget)

    def setUpWidgets(self):
        super(AccountPasswordEditview, self).setUpWidgets(
            context=self.account)

    def validate(self, data):
        currentpassword = data.get('currentpassword')
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(currentpassword, self.account.password):
            self.setFieldError('currentpassword', _(
                "The provided password doesn't match your current password."))

    @action(_("Change"), name="submit")
    def submit_action(self, action, data):
        self.account.password = data['password']
