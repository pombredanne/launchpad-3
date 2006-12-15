# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for bug-related pagetests."""

import re
from canonical.launchpad.ftests.test_pages import (
    find_portlet, find_tag_by_id)

DIRECT_SUBS_PORTLET_INDEX = 0
INDIRECT_SUBS_PORTLET_INDEX = 1

def print_direct_subscribers(bug_page):
    print_subscribers(bug_page, DIRECT_SUBS_PORTLET_INDEX)


def print_indirect_subscribers(bug_page):
    print_subscribers(bug_page, INDIRECT_SUBS_PORTLET_INDEX)


def print_subscribers(bug_page, subscriber_portlet_index):
    """Print the subscribers listed in the subscriber portlet."""
    bug_id = re.search(r"bug #(\d+)", bug_page, re.IGNORECASE).group(1)
    subscriber_portlet = find_portlet(
        bug_page, 'Subscribers to bug %s' % bug_id)
    try:
        portlet = subscriber_portlet.fetch(
            'ul', "people")[subscriber_portlet_index]
    except IndexError:
        # No portlet with this index, as can happen if there are
        # no indirect subscribers, so just print an empty string
        print ""
    else:
        for li in portlet.fetch('li'):
            if li.a:
                print li.a.renderContents()


def print_bugs_table(content, table_id):
    """Print the bugs table with the given ID.

    The table is assumed to consist of rows of bugs whose first column
    is a bug ID, and whose second column is a bug title.
    """
    bugs_table = find_tag_by_id(content, table_id)

    for tr in bugs_table("tr"):
        if not tr.td:
            continue
        bug_id, bug_title = tr("td", limit=2)
        print bug_id.string, bug_title.a.string
