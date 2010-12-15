# Copyright 20010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the Launchpad defaults monekypatch and mm_cfg."""

__metaclass__ = type
__all__ = []


from Mailman import mm_cfg

from canonical.testing.layers import FunctionalLayer
from lp.testing import TestCase


class TestMMCfgDefaultsTestCase(TestCase):
    """Test launchapd default overrides."""

    layer = FunctionalLayer

    def test_common_values(self):
        # Launchpad's boolean and string parameters.
        self.assertEqual('unused_mailman_site_list', mm_cfg.MAILMAN_SITE_LIST)
        self.assertEqual(None, mm_cfg.MTA)
        self.assertEqual(3, mm_cfg.DEFAULT_GENERIC_NONMEMBER_ACTION)
        self.assertEqual(False, mm_cfg.DEFAULT_SEND_REMINDERS)
        self.assertEqual(True, mm_cfg.DEFAULT_SEND_WELCOME_MSG)
        self.assertEqual(False, mm_cfg.DEFAULT_SEND_GOODBYE_MSG)
        self.assertEqual(False, mm_cfg.DEFAULT_DIGESTABLE)
        self.assertEqual(False, mm_cfg.DEFAULT_BOUNCE_NOTIFY_OWNER_ON_DISABLE)
        self.assertEqual(False, mm_cfg.DEFAULT_BOUNCE_NOTIFY_OWNER_ON_REMOVAL)
        self.assertEqual(True, mm_cfg.VERP_PERSONALIZED_DELIVERIES)
        self.assertEqual(False, mm_cfg.DEFAULT_FORWARD_AUTO_DISCARDS)
        self.assertEqual(False, mm_cfg.DEFAULT_BOUNCE_PROCESSING)

    def test_qrunners(self):
        # The queue runners used by Launchpad.
        runners = [pair[0] for pair in mm_cfg.QRUNNERS if pair[1] == 1]
        expected = [
            'ArchRunner', 'BounceRunner', 'IncomingRunner', 'OutgoingRunner',
            'VirginRunner', 'RetryRunner', 'XMLRPCRunner']
        self.assertEqual(expected, runners)

    def test_global_pipeline(self):
        # The ordered list of handlers used by Launchpad.
        # NB. This is a very important list when debuggin were a message
        # has been touched.
        expected = [
            'LaunchpadMember', 'SpamDetect', 'Approve', 'Replybot',
            'LPStanding', 'LPModerate', 'LPSize',
            'MimeDel', 'Scrubber', 'Emergency', 'Tagger', 'CalcRecips',
            'AvoidDuplicates', 'Cleanse', 'CleanseDKIM', 'CookHeaders',
            'LaunchpadHeaders', 'ToDigest', 'ToArchive', 'ToUsenet',
            'AfterDelivery', 'Acknowledge', 'ToOutgoing']
        self.assertEqual(expected, mm_cfg.GLOBAL_PIPELINE)


class TestMMCfgLaunchpadConfigTestCase(TestCase):
    """Test launchapd default overrides."""

    layer = FunctionalLayer

    def test_mail_server(self):
        # Launchpad's smtp config values.
        self.assertEqual('localhost', mm_cfg.SMTPHOST)
        self.assertEqual(9025, mm_cfg.SMTPPORT)

    def test_xmlrpc_server(self):
        # Launchpad's smtp config values.
        self.assertEqual(
            'http://xmlrpc-private.launchpad.dev:8087/mailinglists',
            mm_cfg.XMLRPC_URL)
        self.assertEqual(1, mm_cfg.XMLRPC_SLEEPTIME)
        self.assertEqual(25, mm_cfg.XMLRPC_SUBSCRIPTION_BATCH_SIZE)
        self.assertEqual('topsecret', mm_cfg.LAUNCHPAD_SHARED_SECRET)

    def test_messge_footer(self):
        # Launchpad's email footer.
        self.assertEqual(
            'http://help.launchpad.dev/ListHelp', mm_cfg.LIST_HELP_HEADER)
        self.assertEqual(
            'http://launchpad.dev/~$team_name',
            mm_cfg.LIST_SUBSCRIPTION_HEADERS)
        self.assertEqual(
            'http://lists.launchpad.dev/$team_name',
            mm_cfg.LIST_ARCHIVE_HEADER_TEMPLATE)
        self.assertEqual(
            'http://launchpad.dev/~$team_name',
            mm_cfg.LIST_OWNER_HEADER_TEMPLATE)
        self.assertEqual(
            "-- \n"
            "Mailing list: $list_owner\n"
            "Post to     : $list_post\n"
            "Unsubscribe : $list_unsubscribe\n"
            "More help   : $list_help\n",
            mm_cfg.DEFAULT_MSG_FOOTER)

    def test_message_rules(self):
        # Launchpad's rules for handling messages.
        self.assertEqual('gniTkrOFvY@example.com', mm_cfg.SITE_LIST_OWNER)
        self.assertEqual(40000, mm_cfg.LAUNCHPAD_SOFT_MAX_SIZE)
        self.assertEqual(1000000, mm_cfg.LAUNCHPAD_HARD_MAX_SIZE)
        self.assertEqual(1, mm_cfg.REGISTER_BOUNCES_EVERY)

    def test_archive_setup(self):
        # Launchpad's rules for setting up list archives.
        self.assertTrue('-add' in mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertTrue('-spammode' in mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertTrue('-umask 022'in mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertTrue(
            '-dbfile'
            '/var/tmp/mailman/archives/private/%(listname)s.mbox/mhonarc.db',
           mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertTrue(
            '-outdit /var/tmp/mailman/mhonarc/%(listname)s',
            mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertTrue(
            '-definevar ML-NAME=%(listname)s',
            mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertTrue(
            '-rcfile var/tmp/mailman/data/lp-mhonarc-common.mrc',
            mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertTrue(
            '-stderr /var/tmp/mailman/logs/mhonarc',
            mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertTrue(
            '-stdout /var/tmp/mailman/logs/mhonarc',
            mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
        self.assertEqual(
            mm_cfg.PRIVATE_EXTERNAL_ARCHIVER, mm_cfg.PUBLIC_EXTERNAL_ARCHIVER)
