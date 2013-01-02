# Copyright 20012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the compliation and configuration of the Lp mailman instance."""

__metaclass__ = type
__all__ = []

import os
import subprocess
import sys

from Mailman.mm_cfg import MAILMAN_SITE_LIST

from lp.services.config import config
from lp.services.mailman.config import configure_prefix
from lp.services.mailman.testing import MailmanTestCase
from lp.testing.layers import DatabaseFunctionalLayer


def site_list_callable(mlist):
    if mlist.internal_name() == MAILMAN_SITE_LIST:
        sys.exit(99)
    sys.exit(1)


def can_import_callable(mlist):
    try:
        import lp.services.mailman
        lp
    except ImportError:
        sys.exit(1)
    else:
        sys.exit(99)


class CommandsTestCase(MailmanTestCase):
    """Test mailman binary commands use the Lp compiled Mailman."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(CommandsTestCase, self).setUp()
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'team-1', 'team-1-owner')
        self.mm_list = self.makeMailmanList(self.mailing_list)
        self.lp_user_email = 'albatros@eg.dom'
        self.lp_user = self.factory.makePerson(
            name='albatros', email=self.lp_user_email)

    def tearDown(self):
        super(CommandsTestCase, self).tearDown()
        self.cleanMailmanList(self.mm_list)

    @staticmethod
    def withlist(callable):
        callable_path = '%s.%s' % (__name__, callable)
        site_list = 'unused_mailman_site_list'
        prefix_path = configure_prefix(config.mailman.build_prefix)
        mailman_bin = os.path.join(prefix_path, 'bin')
        command = './withlist -q -r %s %s' % (callable_path, site_list)
        return subprocess.call(command.split(), cwd=mailman_bin)

    def test_withlist_sitelist(self):
        # Mailman's site list must be the Lp configured one.
        self.assertEqual(99, self.withlist('site_list_callable'))

    def test_withlist_import_lp_mailman(self):
        # Lp's mailman can be imported.
        self.assertEqual(99, self.withlist('can_import_callable'))
