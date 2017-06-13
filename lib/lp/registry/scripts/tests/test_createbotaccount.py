# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the create-bot-account script."""

__metaclass__ = type

from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.ssh import ISSHKeySet
from lp.registry.scripts.createbotaccount import CreateBotAccountScript
from lp.services.identity.interfaces.emailaddress import EmailAddressStatus
from lp.services.log.logger import DevNullLogger
from lp.testing import TestCase
from lp.testing.faketransaction import FakeTransaction
from lp.testing.layers import ZopelessDatabaseLayer


class TestCreateBotAccount(TestCase):
    """Test `create-bot-account`."""

    layer = ZopelessDatabaseLayer

    def makeScript(self, test_args):
        script = CreateBotAccountScript(test_args=test_args)
        script.logger = DevNullLogger()
        script.txn = FakeTransaction()
        return script

    def test_createbotaccount(self):
        sshkey_text = (
            'ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAIEA9BC4zfVrGsve6zh'
            'jOiEftyNMjqV8YMv1lLMpbWqa7Eqr0ZL+oAoJQMq2w8Dk/1hrgJ'
            '1pxdwxwQWogDHZTer8YDa89OSBWGenl++s6bk28h/ysZettSS82'
            'BrfpoSUc8Cfz2K1SbI9kz5OhmE4nBVsJgsdiHp9WwwQiyRrjfAu'
            'NhE= whatever@here.local.')
        script = self.makeScript([
            '--username', 'botty',
            '--openid', 'bottyid',
            '--teams', 'rosetta-admins,simple-team',
            '--sshkey', sshkey_text,
            ])
        script.main()

        person_set = getUtility(IPersonSet)

        person = person_set.getByName(u'botty')
        self.assertEqual(u'botty', person.name)
        self.assertTrue(person.hide_email_addresses)
        # Bots tend to flood email, so filtering is important.
        self.assertTrue(person.expanded_notification_footers)

        account = person.account
        openid = account.openid_identifiers.one()
        self.assertEqual(u'bottyid', openid.identifier)

        sshkey_set = getUtility(ISSHKeySet)
        self.assertIsNotNone(
            sshkey_set.getByPersonAndKeyText(person, sshkey_text))

        email = person.preferredemail
        self.assertEqual('webops+botty@canonical.com', email.email)
        self.assertEqual(EmailAddressStatus.PREFERRED, email.status)

        self.assertTrue(person.inTeam(person_set.getByName('rosetta-admins')))
        self.assertTrue(person.inTeam(person_set.getByName('simple-team')))

        self.assertEqual(1, script.txn.commit_count)
