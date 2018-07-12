# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the suspend-bot-account script."""

__metaclass__ = type

from lp.registry.scripts.suspendbotaccount import SuspendBotAccountScript
from lp.services.identity.interfaces.account import AccountStatus
from lp.services.log.logger import DevNullLogger
from lp.testing import TestCaseWithFactory
from lp.testing.faketransaction import FakeTransaction
from lp.testing.layers import ZopelessDatabaseLayer


class TestSuspendBotAccount(TestCaseWithFactory):
    """Test `suspend-bot-account`."""

    layer = ZopelessDatabaseLayer

    def makeScript(self, test_args):
        script = SuspendBotAccountScript(test_args=test_args)
        script.logger = DevNullLogger()
        script.txn = FakeTransaction()
        return script

    def test_suspendbotaccount(self):
        bot = self.factory.makePerson(email='webops+bot@canonical.com')
        script = self.makeScript(['--email', 'webops+bot@canonical.com'])
        script.main()
        self.assertEqual(AccountStatus.SUSPENDED, bot.account_status)

        self.assertEqual(1, script.txn.commit_count)
