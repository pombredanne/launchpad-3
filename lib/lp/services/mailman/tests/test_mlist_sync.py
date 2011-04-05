# Copyright 20010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the  mlist-sync script."""

__metaclass__ = type
__all__ = []

from contextlib import contextmanager
import os
import sys
from textwrap import dedent
from transaction import commit
from subprocess import Popen, PIPE

from Mailman import mm_cfg

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.database.sqlbase import rollback
from lp.services.mailman.testing import (
    MailmanTestCase,
    sync,
    )


@contextmanager
def production_config():
    """Simulate a production Launchpad and mailman config."""
    host = 'lists.production.launchpad.dev'
    config.push('production', dedent("""\
        [mailman]
        build_host_name: %s
        """ % host))
    default_email_host = mm_cfg.DEFAULT_EMAIL_HOST
    mm_cfg.DEFAULT_EMAIL_HOST = host
    default_url_host = mm_cfg.DEFAULT_URL_HOST
    mm_cfg.DEFAULT_URL_HOST = host
    try:
        yield
    finally:
        mm_cfg.DEFAULT_URL_HOST = default_url_host
        mm_cfg.DEFAULT_EMAIL_HOST = default_email_host
        config.pop('production')


class TestMListSync(MailmanTestCase):
    """Test mlist-sync script."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestMListSync, self).setUp()
        with production_config():
            self.team = self.factory.makeTeam(name='team-1')
            self.mailing_list = self.factory.makeMailingList(
                self.team, self.team.teamowner)
            self.mm_list = self.makeMailmanList(self.mailing_list)

    def tearDown(self):
        super(TestMListSync, self).tearDown()
        self.cleanMailmanList(self.mm_list)

    def runMListSync(self, sync_details):
        """Run mlist-sync.py."""
        IStore(self.team).flush()
        commit()
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
        # List is synced with updated URLs and email addresses.
        sync_details = sync.prepare_for_sync()
        self.addCleanup(sync_details.cleanup)
        returncode, stderr = self.runMListSync(sync_details)
        self.assertEqual(0, returncode, stderr)
        #rollback()
        IStore(self.team).invalidate()
        list_summary = [(
            'team-1',
            'lists.launchpad.dev',
            'http://lists.launchpad.dev/mailman/',
            'team-1@lists.launchpad.dev'),
            ]
        self.assertEqual(list_summary, sync.dump_list_info())
