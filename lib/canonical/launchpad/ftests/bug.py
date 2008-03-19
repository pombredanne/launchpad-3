# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Helper functions for bug-related doctests and pagetests."""

import textwrap

from datetime import datetime, timedelta
from operator import attrgetter
from pytz import UTC

from BeautifulSoup import BeautifulSoup

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import sync
from canonical.launchpad.testing.pages import (
    extract_text, find_main_content, find_portlet, find_tag_by_id,
    find_tags_by_class)
from canonical.launchpad.interfaces import (
    BugTaskStatus, IDistributionSet, IBugTaskSet, IPersonSet, IProductSet,
    ISourcePackageNameSet, IBugSet, IBugWatchSet, CreateBugParams)


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
                sub_display = li.a.renderContents()
                if li.a.has_key('title'):
                    sub_display += (' (%s)' % li.a['title'])
                print sub_display


def print_bug_affects_table(content, highlighted_only=False):
    """Print information about all the bug tasks in the 'affects' table.

        :param highlighted_only: Only print the highlighted row
    """
    main_content = find_main_content(content)
    affects_table = main_content.first('table', {'class': 'listing'})
    if highlighted_only:
        tr_attrs = {'class': 'highlight'}
    else:
        tr_attrs = {}
    tr_tags = affects_table.tbody.findAll(
        'tr', attrs=tr_attrs, recursive=False)
    for tr in tr_tags:
        if tr.td.table:
            # Don't print the bugtask edit form.
            continue
        print extract_text(tr)


def print_remote_bugtasks(content):
    """Print the remote bugtasks of this bug.

    For each remote bugtask, print the target and the bugwatch.
    """
    affects_table = find_tags_by_class(content, 'listing')[0]
    for img in affects_table.findAll('img'):
        for key, value in img.attrs:
            if '@@/bug-remote' in value:
                target = extract_text(img.findAllPrevious('td')[-2])
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


def create_task_from_strings(bug, owner, product, watchurl=None):
    """Create a task, optionally linked to a watch."""
    bug = getUtility(IBugSet).get(bug)
    product = getUtility(IProductSet).getByName(product)
    owner = getUtility(IPersonSet).getByName(owner)
    task = getUtility(IBugTaskSet).createTask(bug, owner, product=product)
    if watchurl:
        [watch] = getUtility(IBugWatchSet).fromText(watchurl, bug, owner)
        task.bugwatch = watch
    return task


def create_bug_from_strings(
    distribution, sourcepackagename, owner, summary, description,
    status=None):
    """Create and return a bug."""
    distroset = getUtility(IDistributionSet)
    distribution = distroset.getByName(distribution)

    # XXX: would be really great if spnset consistently offered getByName.
    spnset = getUtility(ISourcePackageNameSet)
    sourcepackagename = spnset.queryByName(sourcepackagename)

    personset = getUtility(IPersonSet)
    owner = personset.getByName(owner)

    bugset = getUtility(IBugSet)
    params = CreateBugParams(owner, summary, description, status=status)
    params.setBugTarget(distribution=distribution,
                        sourcepackagename=sourcepackagename)
    return bugset.createBug(params)


def update_task_status(task_id, person, status):
    """Update a bugtask status."""
    task = getUtility(IBugTaskSet).get(task_id)
    person = getUtility(IPersonSet).getByName(person)
    task.transitionToStatus(status, person)


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
    for bugtask in sorted(set(bugtasks), key=attrgetter('id')):
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


def print_upstream_linking_form(browser):
    """Print the upstream linking form found via +choose-affected-product.

    The resulting output will look something like:
    (*) A checked option
        [A related text field]
    ( ) An unchecked option
    """
    soup = BeautifulSoup(browser.contents)

    link_upstream_how_radio_control = browser.getControl(
        name='field.link_upstream_how')
    link_upstream_how_buttons =  soup.findAll(
        'input', {'name': 'field.link_upstream_how'})

    wrapper = textwrap.TextWrapper(width=65, subsequent_indent='    ')
    for button in link_upstream_how_buttons:
        # Print the radio button.
        label = button.findParent('label')
        if label is None:
            label = soup.find('label', {'for': button['id']})
        if button.get('value') in link_upstream_how_radio_control.value:
            print wrapper.fill('(*) %s' % extract_text(label))
        else:
            print wrapper.fill('( ) %s' % extract_text(label))
        # Print related text field, if found. Assumes that the text
        # field is in the same table row as the radio button.
        text_field = button.findParent('tr').find('input', {'type':'text'})
        if text_field is not None:
            text_control = browser.getControl(name=text_field.get('name'))
            print '    [%s]' % text_control.value.ljust(10)
