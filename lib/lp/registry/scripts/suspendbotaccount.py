# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Suspend a bot account."""

from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.services.identity.interfaces.account import AccountStatus
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )
from lp.services.webapp import canonical_url


class SuspendBotAccountScript(LaunchpadScript):

    description = "Suspend a bot account."
    output = None

    def add_my_options(self):
        self.parser.add_option(
            '-e', '--email', metavar='ADDR', action='store',
            type='string', dest='email', default='', help='Email address')

    def main(self):
        emailaddress = unicode(self.options.email)
        if not emailaddress:
            raise LaunchpadScriptFailure('--email is required')

        person = getUtility(IPersonSet).getByEmail(emailaddress)
        if person is None:
            raise LaunchpadScriptFailure(
                'Account with email address {} does not exist'.format(
                    emailaddress))

        person.account.setStatus(
            AccountStatus.SUSPENDED, None,
            'Suspended by suspend-bot-account.py')

        self.logger.info('Suspended {}'.format(canonical_url(person)))
        self.txn.commit()
