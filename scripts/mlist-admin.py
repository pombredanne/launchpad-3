#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

import sys
import optparse

import _pythonpath

from zope.component import getUtility
from canonical.lp import initZopeless
from canonical.launchpad.database import MailingListSet
from canonical.launchpad.interfaces import IPersonSet, MailingListStatus
from canonical.launchpad.scripts import execute_zcml_for_scripts


def handle(parser, status):
    list_set = MailingListSet()
    if parser.options.reviewer is None:
        parser.error('--reviewer is required.')
    reviewer = getUtility(IPersonSet).getByName(parser.options.reviewer)
    for team_name in parser.arguments:
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


def main():
    parser = optparse.OptionParser(usage="""\
%prog [options] [list|approve|decline] [team ...]

Manage administrative requests for team mailing lists.  Teams may request
mailing lists, but they do not get activated until a Launchpad administrator
approves the request.

Eventually this functionality will be moved into the Launchpad web u/i, but
until then, use this script to display and dispose of such administrative
requests.

Uses:

%prog list
    - Display the list of registered mailing lists awaiting approval.

%prog approve team[, team...]
    - Approve the mailing lists for the named teams.

%prog decline team[, team...]
    - Decline the mailing lists for the named teams.
""")
    parser.add_option('-r', '--reviewer',
                      default=None, type='string', help="""\
The name of the reviewer to use.  Required for 'approve' and 'decline'.""")
    options, arguments = parser.parse_args()
    if len(arguments) == 0:
        parser.error('No arguments given')

    # For convenience
    parser.options = options
    parser.arguments = arguments

    execute_zcml_for_scripts()
    ztm = initZopeless()

    # To keep things simple, and because this is a command line script, just
    # use the mailing list set directly instead of going through the component
    # architecture.
    command = arguments.pop(0)
    if command == 'list':
        list_set = MailingListSet()
        count = -1
        for count, mailing_list in enumerate(list_set.registered_lists):
            print mailing_list.team.name
        if count == -1:
            print 'No team mailing lists awaiting approval.'
    elif command == 'approve':
        handle(parser, MailingListStatus.APPROVED)
    elif command == 'decline':
        handle(parser, MailingListStatus.DECLINED)
    else:
        parser.error('Bad command: %s' % command)

    # Commit all our changes.
    ztm.commit()


if __name__ == '__main__':
    sys.exit(main())
