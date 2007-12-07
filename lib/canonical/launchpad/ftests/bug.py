# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Helper functions for bug-related doctests and pagetests."""

from datetime import datetime, timedelta
from pytz import UTC

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import sync
from canonical.launchpad.ftests.test_pages import (
    extract_text, find_main_content, find_portlet, find_tag_by_id,
    find_tags_by_class)
from canonical.launchpad.interfaces import (
    BugTaskStatus, CreateBugParams, IPersonSet)

DIRECT_SUBS_PORTLET_INDEX = 0
INDIRECT_SUBS_PORTLET_INDEX = 1

def print_direct_subscribers(bug_page):
    """Print the direct subscribers listed in a portlet."""
    print_subscribers(bug_page, DIRECT_SUBS_PORTLET_INDEX)


def print_indirect_subscribers(bug_page):
    """Print the indirect subscribers listed in a portlet."""
    print_subscribers(bug_page, INDIRECT_SUBS_PORTLET_INDEX)


def print_subscribers(bug_page, subscriber_portlet_index):
    """Print the subscribers listed in the subscriber portlet."""
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


def print_remote_bugtasks(content):
    """Print the remote bugtasks of this bug.

    For each remote bugtask, print the target and the bugwatch.
    """
    affects_table = find_tags_by_class(content, 'listing')[0]
    for img in affects_table.findAll('img'):
        for key, value in img.attrs:
            if '@@/bug-remote' in value:
                target = extract_text(img.findAllPrevious('td')[-1])
                print target, extract_text(img.findPrevious('a'))


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


def create_old_bug(
    title, days_old, target, status=BugTaskStatus.INCOMPLETE,
    with_message=True):
    """Create an aged bug.

    :title: A string. The bug title for testing.
    :days_old: An int. The bug's age in days.
    :target: A BugTarkget. The bug's target.
    :status: A BugTaskStatus. The status of the bug's single bugtask.
    :with_message: A Bool. Whether to create a reply message.
    """
    no_priv = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')
    params = CreateBugParams(
        owner=no_priv, title=title, comment='Something is broken.')
    bug = target.createBug(params)
    sample_person = getUtility(IPersonSet).getByEmail('test@canonical.com')
    if with_message is True:
        bug.newMessage(
            owner=sample_person, subject='Something is broken.',
            content='Can you provide more information?')
    bugtask = bug.bugtasks[0]
    bugtask.transitionToStatus(
        status, sample_person)
    date = datetime.now(UTC) - timedelta(days=days_old)
    removeSecurityProxy(bug).date_last_updated = date
    return bugtask


def summarize_bugtasks(bugtasks):
    """Summarize a sequence of bugtasks."""
    print 'ROLE  EXPIRE  AGE  STATUS  ASSIGNED  DUP  MILE  REPLIES'
    for bugtask in bugtasks:
        if len(bugtask.bug.bugtasks) == 1:
            title = bugtask.bug.title
        else:
            title = bugtask.target.name
        print '%s  %s  %s  %s  %s  %s  %s  %s' % (
            title,
            bugtask.pillar.enable_bug_expiration,
            (datetime.now(UTC) - bugtask.bug.date_last_updated).days,
            bugtask.status.title,
            bugtask.assignee is not None,
            bugtask.bug.duplicateof is not None,
            bugtask.milestone is not None,
            bugtask.bug.messages.count() == 1)


def sync_bugtasks(bugtasks):
    """Sync the bugtask and its bug to the database."""
    if not isinstance(bugtasks, list):
        bugtasks = [bugtasks]
    for bugtask in bugtasks:
        sync(bugtask)
        sync(bugtask.bug)
