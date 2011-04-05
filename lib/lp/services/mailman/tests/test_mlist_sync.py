# Copyright 20010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the  mlist-sync script."""

__metaclass__ = type
__all__ = []

from contextlib import contextmanager
import os
import shutil
import sys
import tempfile
from textwrap import dedent
from transaction import commit
from subprocess import Popen, PIPE

from Mailman import mm_cfg
from Mailman.MailList import MailList
from Mailman.Utils import list_names

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import IPersonSet
from lp.services.mailman.testing import MailmanTestCase
from lp.testing import celebrity_logged_in


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
        self.email_address_set = getUtility(IEmailAddressSet)
        self.person_set = getUtility(IPersonSet)

    def tearDown(self):
        super(TestMListSync, self).tearDown()
        self.cleanMailmanList(self.mm_list)

    def setupProductionFiles(self):
        "Setup a production file structure to sync."
        tempdir = tempfile.mkdtemp()
        source_dir = os.path.join(tempdir, 'production')
        shutil.copytree(
            config.mailman.build_var_dir, source_dir, symlinks=True)
        mhonarc_path = os.path.join(
            mm_cfg.VAR_PREFIX, 'mhonarc', 'fake-team')
        return source_dir

    def runMListSync(self, source_dir):
        """Run mlist-sync.py."""
        IStore(self.team).flush()
        commit()
        proc = Popen(
            ('scripts/mlist-sync.py', '--hostname',
             'lists.prod.launchpad.dev', source_dir),
            stdout=PIPE, stderr=PIPE,
            cwd=config.root,
            env=dict(LPCONFIG=DatabaseFunctionalLayer.appserver_config_name,
                     PYTHONPATH=os.pathsep.join(sys.path),
                     PATH=os.environ.get('PATH')))
        stdout, stderr = proc.communicate()
        return proc.returncode, stderr

    def getListInfo(self):
        """Return a list of 4-tuples of Mailman mailing list info."""
        list_info = []
        for list_name in sorted(list_names()):
            if list_name == mm_cfg.MAILMAN_SITE_LIST:
                continue
            team = self.person_set.getByName(list_name)
            emails = []
            if team is None:
                emails.append('No Launchpad team: %s' % list_name)
            else:
                addresses = self.email_address_set.getByPerson(team)
                with celebrity_logged_in('admin'):
                    for email in sorted(email.email for email in addresses):
                        emails.append(email)
            mailing_list = MailList(list_name, lock=False)
            list_info.append(
                (mailing_list.internal_name(), mailing_list.host_name,
                 mailing_list.web_page_url, ' '.join(emails)))
        return list_info

    def test_staging_sync(self):
        # List is synced with updated URLs and email addresses.
        source_dir = self.setupProductionFiles()
        self.addCleanup(shutil.rmtree, source_dir)
        returncode, stderr = self.runMListSync(source_dir)
        self.assertEqual(0, returncode, stderr)
        #rollback()
        IStore(self.team).invalidate()
        list_summary = [(
            'team-1',
            'lists.launchpad.dev',
            'http://lists.launchpad.dev/mailman/',
            'team-1@lists.launchpad.dev'),
            ]
        self.assertEqual(list_summary, self.getListInfo())
