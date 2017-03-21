# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for PersonSet."""

__metaclass__ = type


from mock import MagicMock
from zope.component import getUtility
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.ssh import ISSHKeySet
from lp.registry.scripts.createbotaccount import CreateBotAccountScript
from lp.services.identity.interfaces.emailaddress import EmailAddressStatus
from lp.testing import TestCase
from lp.testing.layers import ZopelessDatabaseLayer


class CreateBotAccountTests(TestCase):
    """Test `IPersonSet`."""
    layer = ZopelessDatabaseLayer

    def test_createbotaccount(self):
        script = CreateBotAccountScript()

        class _opt:
            username = 'botty'
            openid = 'bottyid'
            email = ''
            teams = 'rosetta-admins,simple-team'
            sshkey = ('ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAIEA9BC4zfVrGsve6zh'
                      'jOiEftyNMjqV8YMv1lLMpbWqa7Eqr0ZL+oAoJQMq2w8Dk/1hrgJ'
                      '1pxdwxwQWogDHZTer8YDa89OSBWGenl++s6bk28h/ysZettSS82'
                      'BrfpoSUc8Cfz2K1SbI9kz5OhmE4nBVsJgsdiHp9WwwQiyRrjfAu'
                      'NhE= whatever@here.local.')

        script.options = _opt
        script.logger = MagicMock()
        script.txn = MagicMock()
        script.main()

        person_set = getUtility(IPersonSet)

        person = person_set.getByName(u'botty')
        self.assertEqual(person.name, u'botty')
        self.assertTrue(person.hide_email_addresses)
        # Bots tend to flood email, so filtering is important.
        self.assertTrue(person.expanded_notification_footers)

        account = person.account
        openid = account.openid_identifiers.one()
        self.assertEqual(openid.identifier, u'bottyid')

        sshkey_set = getUtility(ISSHKeySet)
        self.assertIsNotNone(
            sshkey_set.getByPersonAndKeyText(person, _opt.sshkey))

        email = person.preferredemail
        self.assertEqual(email.email, 'webops+botty@canonical.com')
        self.assertEqual(email.status, EmailAddressStatus.PREFERRED)

        self.assertTrue(person.inTeam(person_set.getByName('rosetta-admins')))
        self.assertTrue(person.inTeam(person_set.getByName('simple-team')))

        self.assertTrue(script.txn.commit.called)
