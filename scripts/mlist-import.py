#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Import a mailing list (well, parts of it)."""

# XXX BarryWarsaw 2008-11-24
# Things this script does NOT currently do.
#
# - Import archives.

__metaclass__ = type
__all__ = []


# pylint: disable-msg=W0403
import _pythonpath

from canonical.launchpad.scripts.base import LaunchpadScript


class MailingListImport(LaunchpadScript):
    """
    %prog [options]

    Import various mailing list artifacts into a Launchpad mailing
    list.  This script allows you to import e.g. the membership list
    from an external mailing list into a Launchpad hosted mailng list.
    """

    loglevel = logging.INFO
    description = 'Import data into a Launchpad mailing list.'

    def __init__(self, name, dbuser=None):
        self.usage = textwrap.dedent(self.__doc__)
        super(MailingListImport, self).__init__(name, dbuser)

    def main(self):
        """See `LaunchpadScript`."""
        team_name = None
        if len(self.args) == 0:
            self.parser.error('Missing team name')
        elif len(self.args) > 1:
            self.parser.error('Too many arguments')
        else:
            team_name = self.args[0]

        # All done; commit the database changes.
        self.txn.commit()
        return 0


if __name__ == '__main__':
    script = MailingListImport('scripts.mlist-import', 'mlist-import')
    status = script.lock_and_run()
    sys.exit(status)
