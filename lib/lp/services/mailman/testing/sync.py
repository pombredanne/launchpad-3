# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for staging sync test."""

__metaclass__ = type
__all__ = [
    'SyncDetails',
    'dump_list_info',
    'prepare_for_sync',
    ]


import os
import shutil
import tempfile

from Mailman import mm_cfg
from Mailman.MailList import MailList
from Mailman.Utils import list_names
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.sqlbase import (
    commit,
    flush_database_caches,
    )
from canonical.launchpad.ftests import (
    login,
    logout,
    )
from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from lp.registry.interfaces.person import IPersonSet


class SyncDetails:
    """Details about the sync that just happened."""

    def __init__(self, source_dir, mhonarc_path):
        self.source_dir = source_dir
        self.mhonarc_path = mhonarc_path

    def cleanup(self):
        """Clean up all artifacts of the sync."""
        shutil.rmtree(self.source_dir)
        shutil.rmtree(self.mhonarc_path)


def prepare_for_sync():
    """Prepare a sync'd directory for mlist-sync.py.

    This simulates what happens in the real-world: the production Launchpad
    database is copied to staging, and then the Mailman data is copied to a
    temporary local directory on staging.  It is from this temporary location
    that the actual staging Mailman data is sync'd.

    Because of this, it's possible that a mailing list will exist in Mailman
    but not in Launchpad's database.  We simulate this by creating fake-team
    in Mailman only.

    Also, the Mailman data will have some incorrect hostnames that reflect
    production hostnames instead of staging hostnames.  We simulate this by
    hacking those production names into the Mailman lists.

    The Launchpad database will also have production hostnames in the mailing
    list data it knows about.

    Finally, after all this hackery, we copy the current Mailman tree to a
    temporary location.  Thus this temporary copy will look like production's
    Mailman database, and the sync will be more realistic.

    :return: An object containing the details of the sync.  The returned
        object will have a `source_dir` attribute indicating the sync source
        directory, and a `mhonarch_path` attribute indicating the path to the
        fake team's MHonArc archive.  The returned object will have a
        `cleanup()` method that must be called at the end of the test.
    :rtype: `SyncDetails`
    """
    # Tweak each of the mailing lists by essentially breaking their host_name
    # and web_page_urls.  These will get repaired by the sync script.  Do this
    # before we copy so that the production copy will have the busted values.
    # pylint: disable-msg=F0401
    team_names = list_names()
    for list_name in team_names:
        if list_name == mm_cfg.MAILMAN_SITE_LIST:
            continue
        mailing_list = MailList(list_name)
        try:
            mailing_list.host_name = 'lists.prod.launchpad.dev'
            mailing_list.web_page_url = 'http://lists.prod.launchpad.dev'
            mailing_list.Save()
        finally:
            mailing_list.Unlock()
    # Create a mailing list that exists only in Mailman.  The sync script will
    # end up deleting this because it represents a race condition between when
    # the production database was copied and when the Mailman data was copied.
    mlist = MailList()
    try:
        mhonarc_path = os.path.join(mm_cfg.VAR_PREFIX, 'mhonarc', 'fake-team')
        mlist.Create('fake-team', mm_cfg.SITE_LIST_OWNER, ' no password ')
        mlist.Save()
        os.makedirs(mhonarc_path)
    finally:
        mlist.Unlock()
    # Create a directory in which to put the simulated production database,
    # then copy our current Mailman stuff to it, lock, stock, and barrel.
    tempdir = tempfile.mkdtemp()
    source_dir = os.path.join(tempdir, 'production')
    shutil.copytree(config.mailman.build_var_dir, source_dir, symlinks=True)
    # Now, we have to mess up the production database by tweaking the email
    # addresses of all the mailing lists.
    login('foo.bar@canonical.com')
    email_set = getUtility(IEmailAddressSet)
    for list_name in team_names:
        if list_name == mm_cfg.MAILMAN_SITE_LIST:
            continue
        email = removeSecurityProxy(
            email_set.getByEmail(list_name + '@lists.launchpad.dev'))
        email.email = list_name + '@lists.prod.launchpad.dev'
    logout()
    commit()
    return SyncDetails(source_dir, mhonarc_path)


def dump_list_info():
    """Print a bunch of useful information related to sync'ing."""
    # Print interesting information about each mailing list.
    flush_database_caches()
    login('foo.bar@canonical.com')
    for list_name in sorted(list_names()):
        if list_name == mm_cfg.MAILMAN_SITE_LIST:
            continue
        mailing_list = MailList(list_name, lock=False)
        print mailing_list.internal_name()
        print '   ', mailing_list.host_name, mailing_list.web_page_url
        team = getUtility(IPersonSet).getByName(list_name)
        if team is None:
            print '    No Launchpad team:', list_name
        else:
            mlist_addresses = getUtility(IEmailAddressSet).getByPerson(team)
            for email in sorted(email.email for email in mlist_addresses):
                print '   ', email
    logout()
