# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helper utilities."""

__metaclass__ = type
__all__ = [
    'apply_for_list',
    'collect_archive_message_ids',
    'create_list',
    'ensure_addresses_are_enabled',
    'ensure_membership',
    'ensure_nonmembership',
    'get_size',
    'pending_hold_ids',
    'print_mailman_hold',
    'review_list',
    'run_mailman',
    'subscribe',
    'unsubscribe',
    ]


import os
import re
import time
import errno
import pickle
import datetime
import transaction

from subprocess import Popen, PIPE
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login, logout
from canonical.launchpad.ftests import mailinglists_helper
from canonical.launchpad.interfaces.mailinglist import IMailingListSet
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.mailman.testing.layers import MailmanLayer
from canonical.launchpad.testing.browser import Browser

from Mailman import mm_cfg
from Mailman.Errors import NotAMemberError
from Mailman.MailList import MailList
from Mailman.MemberAdaptor import ENABLED
from Mailman.Utils import list_names


# This is where the Mailman command line scripts live.
import Mailman
MAILMAN_PKGDIR = os.path.dirname(Mailman.__file__)
MAILMAN_BINDIR = os.path.join(os.path.dirname(MAILMAN_PKGDIR), 'bin')

SPACE = ' '
MAILING_LIST_CHECK_INTERVAL = datetime.timedelta(seconds=5)
SECONDS_TO_SNOOZE = 0.1


def get_size(path):
    """Return the size of a file, or -1 if it doesn't exist."""
    try:
        return os.stat(path).st_size
    except OSError, error:
        if error.errno == errno.ENOENT:
            # Return -1 when the file does not exist, so it always
            # compares less than an existing but empty file.
            return -1
        # Some other error occurred.
        raise


def review_list(list_name, status='approve'):
    """Helper for approving a mailing list."""
    # Circular import.
    browser = Browser('foo.bar@canonical.com:test')
    browser.open('http://launchpad.dev:8085/+mailinglists')
    browser.getControl(name='field.' + list_name).value = [status]
    browser.getControl('Submit').click()
    result = MailmanLayer.xmlrpc_watcher.wait_for_create(list_name)
    if result is not None:
        # The watch timed out
        print result
        return
    login('foo.bar@canonical.com')
    mailing_list = getUtility(IMailingListSet).get(list_name)
    logout()
    return mailing_list


def create_list(team_name):
    """Do everything you need to do to make the team's list live."""
    displayname = SPACE.join(
        word.capitalize() for word in team_name.split('-'))
    browser = Browser('no-priv@canonical.com:test')
    # Create the team.
    browser.open('http://launchpad.dev:8085/people/+newteam')
    browser.getControl(name='field.name').value = team_name
    browser.getControl('Display Name').value = displayname
    browser.getControl(name='field.subscriptionpolicy').displayValue = [
        'Open Team']
    browser.getControl('Create').click()
    # Create the mailing list.
    browser.getLink('Configure mailing list').click()
    browser.getControl('Apply for Mailing List').click()
    mailing_list = review_list(team_name)
    # pylint: disable-msg=F0401
    assert team_name in list_names(), (
        'Mailing list was not created: %s (found: %s)' %
        (team_name, list_names()))
    result = ensure_membership(team_name, 'archive@mail-archive.dev')
    if result is not None:
        return result
    return mailing_list


def run_mailman(*args):
    """Run a Mailman script."""
    proc = Popen(args, stdout=PIPE, stderr=PIPE, cwd=MAILMAN_BINDIR)
    stdout, stderr = proc.communicate()
    assert len(stderr) == 0, stderr
    return stdout


def subscribe(first_name, team_name, use_alt_address=False):
    """Do everything you need to subscribe a person to a mailing list."""
    # Create the person if she does not already exist, and join her to the
    # team.
    login('foo.bar@canonical.com')
    person_set = getUtility(IPersonSet)
    person = person_set.getByName(first_name.lower())
    if person is None:
        person = mailinglists_helper.new_person(first_name)
    team = getUtility(IPersonSet).getByName(team_name)
    person.join(team)
    # Subscribe her to the list.
    mailing_list = getUtility(IMailingListSet).get(team_name)
    if use_alt_address:
        alternative_email = mailinglists_helper.get_alternative_email(person)
        mailing_list.subscribe(person, alternative_email)
    else:
        mailing_list.subscribe(person)
    transaction.commit()
    logout()
    return ensure_membership(team_name, person)


def unsubscribe(first_name, team_name):
    """Unsubscribe the named person from the team's mailing list."""
    login('foo.bar@canonical.com')
    person_set = getUtility(IPersonSet)
    person = person_set.getByName(first_name.lower())
    assert person is not None, 'No such person: %s' % first_name
    mailing_list = getUtility(IMailingListSet).get(team_name)
    mailing_list.unsubscribe(person)
    transaction.commit()
    logout()
    return ensure_nonmembership(team_name, person)


def pending_hold_ids(list_name):
    """Return the set of pending held messages in Mailman for the list.

    We do it this way in order to be totally safe, so that there's no
    possibility of leaving a locked list floating around.  doctest doesn't
    always do the right thing.
    """
    # The list must be locked to make this query.
    mailing_list = MailList(list_name)
    try:
        return mailing_list.GetHeldMessageIds()
    finally:
        mailing_list.Unlock()


def print_mailman_hold(list_name, hold_id):
    """Print the held message as Mailman sees it."""
    # The list must be locked to make this query.
    mailing_list = MailList(list_name)
    try:
        data = mailing_list.GetRecord(hold_id)
    finally:
        mailing_list.Unlock()
    held_file_name = data[4]
    path = os.path.join(mm_cfg.DATA_DIR, held_file_name)
    file_object = open(path)
    try:
        message = pickle.load(file_object)
    finally:
        file_object.close()
    print message.as_string()


def collect_archive_message_ids(team_name):
    """Collect all the X-Message-Id values in the team's archived messages."""
    mhonarc_path = os.path.join(mm_cfg.VAR_PREFIX, 'mhonarc', 'itest-one')
    message_ids = []
    # Unfortunately, there's nothing we can wait on to know whether the
    # archiver has run yet or not, because the archive runner does not log
    # messages when it completes.
    archived_files = []
    for count in range(3):
        try:
            archived_files = [file_name
                              for file_name in os.listdir(mhonarc_path)
                              if file_name.endswith('.html')]
        except OSError, error:
            if error.errno != errno.ENOENT:
                raise
            # Sleep and try again.
        if len(archived_files) > 0:
            break
        time.sleep(0.5)
    for html_file in archived_files:
        archive_file = open(os.path.join(mhonarc_path, html_file))
        try:
            data = archive_file.read()
        finally:
            archive_file.close()
        for line in data.splitlines():
            if line.startswith('<!DOCTYPE'):
                break
            mo = re.match('<!--X-Message-Id:\s*(?P<id>[\S]+)', line, re.I)
            if mo:
                message_ids.append(mo.group('id'))
                break
    return sorted(message_ids)


def apply_for_list(browser, team_name):
    """Like mailinglists_helper.apply_for_list() but with the right rooturl."""
    mailinglists_helper.apply_for_list(
        browser, team_name, 'http://launchpad.dev:8085/')


def _membership_test(team_name, people, predicate):
    """Test membership via the predicate."""
    member_addresses = set()
    for person in people:
        if isinstance(person, basestring):
            member_addresses.add(person)
        else:
            for email in person.validatedemails:
                member_addresses.add(removeSecurityProxy(email).email.lower())
    mailing_list = MailList(team_name, lock=False)
    until = datetime.datetime.now() + MAILING_LIST_CHECK_INTERVAL
    while True:
        members = set(mailing_list.getMembers())
        if predicate(members, member_addresses):
            # Every address in the arguments was a member.  For doctest
            # success convenience, return None.
            return None
        # At least one address was not a member.  See if we timed out.
        if datetime.datetime.now() > until:
            return 'Timed out'
        time.sleep(SECONDS_TO_SNOOZE)
        # Reload the mailing list data and go around again.
        mailing_list.Load()


def ensure_membership(team_name, *people):
    """Ensure that all the addresses are members of the mailing list."""
    def all_are_members(list_members, wanted_members):
        return list_members >= wanted_members
    return _membership_test(team_name, people, all_are_members)


def ensure_nonmembership(team_name, *people):
    """Ensure that none of the addresses are members of the mailing list."""
    def none_are_members(list_members, unwanted_members):
        # The intersection of the two sets is empty.
        return len(list_members & unwanted_members) == 0
    return _membership_test(team_name, people, none_are_members)


def ensure_addresses_are_enabled(team_name, *addresses):
    """Ensure that addresses are both subscribed and enabled."""
    mailing_list = MailList(team_name, lock=False)
    until = datetime.datetime.now() + MAILING_LIST_CHECK_INTERVAL
    while True:
        for address in addresses:
            try:
                if mailing_list.getDeliveryStatus(address) != ENABLED:
                    break
            except NotAMemberError:
                # The address can't be enabled because its not a member.
                break
        else:
            # All addresses are enabled.For doctest success convenience,
            # return None.
            return None
        if datetime.datetime.now() > until:
            return 'Timed out'
        time.sleep(SECONDS_TO_SNOOZE)
        # Reload the mailing list data and go around again.
        mailing_list.Load()
