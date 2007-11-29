#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

import sys
import logging
import textwrap

# pylint: disable-msg=W0403
import _pythonpath

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    IMailingListSet, IPersonSet, MailingListStatus)
from canonical.launchpad.scripts.base import LaunchpadScript


class MailingListAdminScript(LaunchpadScript):
    """
    %prog [options] [list|approve|decline] [team ...]

    Manage administrative requests for team mailing lists.  Teams may request
    mailing lists, but they do not get activated until a Launchpad
    administrator approves the request.

    Eventually this functionality will be moved into the Launchpad web u/i,
    but until then, use this script to display and dispose of such
    administrative requests.

    Uses:

    %prog list
        - Display the list of registered mailing lists awaiting approval.

    %prog approve team[, team...]
        - Approve the mailing lists for the named teams.

    %prog decline team[, team...]
        - Decline the mailing lists for the named teams.
    """

    loglevel = logging.INFO
    description = 'Manage administrative requests for team mailing lists.'

    def __init__(self):
        self.usage = textwrap.dedent(self.__doc__)
        super(MailingListAdminScript, self).__init__('scripts.mlist_admin')

    def add_my_options(self):
        self.parser.add_option('-r', '--reviewer',
                          default=None, type='string', help="""\
The name of the reviewer to use.  Required for 'approve' and 'decline'.""")

    def main(self):
        if len(self.args) == 0:
            self.parser.error('No arguments given')

        command = self.args.pop(0)
        if command == 'list':
            list_set = getUtility(IMailingListSet)
            count = -1
            for count, mailing_list in enumerate(list_set.registered_lists):
                print mailing_list.team.name
            # pylint: disable-msg=W0631
            if count == -1:
                print 'No team mailing lists awaiting approval.'
        elif command == 'approve':
            self.handle(MailingListStatus.APPROVED)
        elif command == 'decline':
            self.handle(MailingListStatus.DECLINED)
        else:
            self.parser.error('Bad command: %s' % command)

        # Commit all our changes.
        self.txn.commit()

    def handle(self, status):
        list_set = getUtility(IMailingListSet)
        reviewer_name = self.options.reviewer
        if reviewer_name is None:
            self.parser.error('--reviewer is required.')
        reviewer = getUtility(IPersonSet).getByName(reviewer_name)
        for team_name in self.args:
            mailing_list = list_set.get(team_name)
            if mailing_list is None:
                print 'SKIPPED:', team_name, '(no team list yet)'
                continue
            if mailing_list.status != MailingListStatus.REGISTERED:
                print 'SKIPPED:', team_name, (
                    '(already %s)' % mailing_list.status.name)
                continue
            mailing_list.review(reviewer, status)
            print '%s:' % status.name, team_name


if __name__ == '__main__':
    script = MailingListAdminScript()
    status = script.run()
    sys.exit(status)
