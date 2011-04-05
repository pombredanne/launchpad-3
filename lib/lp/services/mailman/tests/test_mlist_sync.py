# Copyright 20010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the  mlist-sync script."""

__metaclass__ = type
__all__ = []

import os
import sys
from subprocess import Popen, PIPE

from canonical.config import config
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.database.sqlbase import rollback
from lp.services.mailman.testing import (
    MailmanTestCase,
    sync,
    )


class TestMListSync(MailmanTestCase):
    """Test mlist-sync script."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestMListSync, self).setUp()
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'team-1', 'team-1-owner')
        self.mm_list = self.makeMailmanList(self.mailing_list)

    def tearDown(self):
        super(TestMListSync, self).tearDown()
        self.cleanMailmanList(self.mm_list)

    def runMListSync(self, sync_details):
        """Run mlist-sync.py."""
        proc = Popen(
            ('scripts/mlist-sync.py', '--hostname',
             'lists.prod.launchpad.dev', sync_details.source_dir),
            stdout=PIPE, stderr=PIPE,
            cwd=config.root,
            env=dict(LPCONFIG=DatabaseFunctionalLayer.appserver_config_name,
                     PYTHONPATH=os.pathsep.join(sys.path),
                     PATH=os.environ.get('PATH')))
        stdout, stderr = proc.communicate()
        return proc.returncode, stderr

    def test_staging_sync(self):
        # List is synced with pdated URLs and email addresses.
        sync_details = sync.prepare_for_sync(team=self.team)
        self.addCleanup(sync_details.cleanup)
        returncode, stderr = self.runMListSync(sync_details)
        self.assertEqual(0, returncode, stderr)
        rollback()
        list_summary = [(
            'team-1',
            'lists.launchpad.dev',
            'http://lists.launchpad.dev/mailman/',
            'team-1@lists.launchpad.dev'),
            ]
        self.assertEqual(list_summary, sync.dump_list_info())
