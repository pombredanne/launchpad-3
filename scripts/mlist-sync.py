#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

import os
import sys
import shutil
import logging
import textwrap
import subprocess

# pylint: disable-msg=W0403
import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadScript


class MailingListSyncScript(LaunchpadScript):
    """
    %prog [options]

    Sync the mailing list data structures with the database.  This is
    necessary for example when the production database is copied to staging.

    XXX For now, we /know/ that production has no databases, so this script
    takes the cheap way out by deleting all lists except the site list.
    """

    loglevel = logging.INFO
    description = 'Sync the Mailman data structures with the database.'

    def __init__(self):
        self.usage = textwrap.dedent(self.__doc__)
        super(MailingListSyncScript, self).__init__('scripts.mlist_sync')

    def add_my_options(self):
        self.parser.add_option('-n', '--dry-run',
                               default=False, action='store_true', help="""\
Show the lists that would be deleted, but do not delete them.""")

    def main(self):
        """See `LaunchpadScript`."""
        if len(self.args) != 0:
            self.parser.error('Too many arguments')

        # Set up access to the Mailman package and import the defaults.
        mailman_path = config.mailman.build.prefix
        mailman_bin = os.path.join(mailman_path, 'bin')
        mhonarc_path = os.path.join(config.mailman.build.var_dir, 'mhonarc')
        sys.path.append(mailman_path)
        from Mailman import mm_cfg
        from Mailman import Utils

        deletable_lists = set(Utils.list_names())
        deletable_lists.remove(mm_cfg.MAILMAN_SITE_LIST)
        if len(deletable_lists) == 0:
            print 'Nothing to do.'
            return 0
        
        if self.options.dry_run:
            print 'Lists that would be deleted:'
            for list_name in sorted(deletable_lists):
                print '\t', list_name
                return 0

        # Deleting lists is done with the rmlist script, which unfortunately
        # is not importable in Mailman 2.1.  Because we also want to
        # completely delete the archives, we'll just shell out to rmlist.
        errors = 0
        for list_name in sorted(deletable_lists):
            print 'Removing all traces of mailing list:', list_name
            retcode = subprocess.call(
                ('./rmlist', '-a', list_name),
                cwd=mailman_bin)
            if retcode:
                print >> sys.stderr, 'Could not delete list:', list_name
                # For now, keep going.
                errors += 1
            # We also need to delete the mhonarc archives for this list, which
            # isn't done by rmlist.
            shutil.rmtree(os.path.join(mhonarc_path, list_name))
        return errors


if __name__ == '__main__':
    script = MailingListSyncScript()
    status = script.run()
    sys.exit(status)
