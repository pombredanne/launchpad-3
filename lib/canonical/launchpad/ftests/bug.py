# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for bug-related pagetests."""

import re
from canonical.launchpad.ftests.test_pages import (
    extract_text, find_main_content, find_portlet, find_tag_by_id)

DIRECT_SUBS_PORTLET_INDEX = 0
INDIRECT_SUBS_PORTLET_INDEX = 1

def print_direct_subscribers(bug_page):
    print_subscribers(bug_page, DIRECT_SUBS_PORTLET_INDEX)


def print_indirect_subscribers(bug_page):
    print_subscribers(bug_page, INDIRECT_SUBS_PORTLET_INDEX)


def print_subscribers(bug_page, subscriber_portlet_index):
    """Print the subscribers listed in the subscriber portlet."""
    bug_id = re.search(r"bug #(\d+)", bug_page, re.IGNORECASE).group(1)
    subscriber_portlet = find_portlet(bug_page, 'Subscribers')
    try:
        portlet = subscriber_portlet.fetch(
            'ul', "person")[subscriber_portlet_index]
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


def print_bugs_list(content, list_id):
    """Print the bugs list with the given ID.

    Right now this is quite simplistic, in that it just extracts the
    text from the element specified by list_id. If the bug listing
    becomes more elaborate then this function will be the place to
    cope with it.
    """
    bugs_list = find_tag_by_id(content, list_id).findAll(
        None, {'class': 'similar-bug'})
    for node in bugs_list:
        print extract_text(node)


def print_bugtasks(text):
    """Print all the bugtasks in the text."""
    print '\n'.join(extract_bugtasks(text))


def extract_bugtasks(text):
    """Extracts a list of strings for all the bugtasks in the text."""
    main_content = find_main_content(text)
    table = main_content.find('table', {'id': 'buglisting'})
    if table is None:
        return []
    return [extract_text(tr) for tr in table('tr') if tr.td is not None]
