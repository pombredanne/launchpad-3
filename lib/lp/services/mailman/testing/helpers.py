# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper utilities."""

__metaclass__ = type
__all__ = [
    'apply_for_list',
    'collect_archive_message_ids',
    'create_list',
    'ensure_addresses_are_disabled',
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


import datetime
import errno
import os
import pickle
import re
from subprocess import (
    PIPE,
    Popen,
    )
import time

# This is where the Mailman command line scripts live.
import Mailman
from Mailman import mm_cfg
from Mailman.Errors import NotAMemberError
from Mailman.MailList import MailList
from Mailman.MemberAdaptor import (
    BYUSER,
    ENABLED,
    )
from Mailman.Utils import list_names
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import (
    login,
    logout,
    )
from canonical.launchpad.testing.browser import Browser
from lp.registry.interfaces.mailinglist import IMailingListSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.tests import mailinglists_helper
from lp.services.mailman.testing.layers import MailmanLayer
from lp.testing.factory import LaunchpadObjectFactory


MAILMAN_PKGDIR = os.path.dirname(Mailman.__file__)
MAILMAN_BINDIR = os.path.join(os.path.dirname(MAILMAN_PKGDIR), 'bin')

SPACE = ' '
MAILING_LIST_CHECK_INTERVAL = datetime.timedelta(seconds=10)
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
    result = MailmanLayer.xmlrpc_watcher.wait_for_create(list_name)
    if result is not None:
        # The watch timed out.
        print result
        return None
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
    browser.open('%s/people/+newteam' % MailmanLayer.appserver_root_url())
    browser.getControl(name='field.name').value = team_name
    browser.getControl('Display Name').value = displayname
    browser.getControl(name='field.subscriptionpolicy').displayValue = [
        'Open Team']
    browser.getControl('Create').click()
    # Create the mailing list.
    browser.getLink('Create a mailing list').click()
    browser.getControl('Create new Mailing List').click()
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
        person = LaunchpadObjectFactory().makePersonByName(first_name)
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
    # Unsubscribing does not make the person a non-member, but it does disable
    # all their addresses.
    addresses = [
        removeSecurityProxy(email).email
        for email in person.validatedemails
        ]
    addresses.append(removeSecurityProxy(person.preferredemail).email)
    logout()
    return ensure_addresses_are_disabled(team_name, *addresses)


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
    """Like mailinglists_helper.apply_for_list() but with the right rooturl.
    """
    mailinglists_helper.apply_for_list(
        browser, team_name, MailmanLayer.appserver_root_url(ensureSlash=True))


def _membership_test(team_name, people, predicate):
    """Test membership via the predicate.

    :param team_name: the name of the team/mailing list to test
    :type team_name: string
    :param people: the sequence of IPersons to check.  All validated emails
        from all persons are collected and checked for membership.
    :type people: sequence of IPersons
    :param predicate: A function taking two arguments.  The first argument is
        the sent of member addresses found in the Mailman MailList
        data structure.  The second argument is the set of validated email
        addresses for all the `people`.  The function should return a boolean
        indicating whether the condition being tested is satisfied or not.
    :type predicate: function
    :return: the string 'Timed out' if the predicate never succeeded, or None
        if it did.
    :rtype: string or None
    """
    member_addresses = set()
    for person in people:
        if isinstance(person, basestring):
            member_addresses.add(person)
        else:
            for email in person.validatedemails:
                member_addresses.add(removeSecurityProxy(email).email)
            # Also add the preferred address.
            preferred = removeSecurityProxy(person.preferredemail).email
            member_addresses.add(preferred)
    assert len(member_addresses) > 0, 'No valid addresses found'
    mailing_list = MailList(team_name, lock=False)
    until = datetime.datetime.now() + MAILING_LIST_CHECK_INTERVAL
    while True:
        members = set(
            mailing_list.getMemberCPAddresses(mailing_list.getMembers()))
        if predicate(members, member_addresses):
            # Every address in the arguments was a member.  Return None
            # on success, so that the doctest doesn't need an extra line to
            # match the output.
            return None
        # The predicate test failed.  See if we timed out.
        if datetime.datetime.now() > until:
            return 'Timed out'
        time.sleep(SECONDS_TO_SNOOZE)
        # Reload the mailing list data and go around again.
        mailing_list.Load()


def ensure_membership(team_name, *people):
    """Ensure that all the addresses are members of the mailing list."""
    def all_are_members(list_members, wanted_members):
        return list_members.issuperset(wanted_members)
    return _membership_test(team_name, people, all_are_members)


def ensure_nonmembership(team_name, *people):
    """Ensure that none of the addresses are members of the mailing list."""
    def none_are_members(list_members, unwanted_members):
        # The intersection of the two sets is empty.
        return len(list_members & unwanted_members) == 0
    return _membership_test(team_name, people, none_are_members)


def _ensure_addresses_are_in_state(team_name, state, addresses):
    """Ensure that addresses are in the specified state."""
    mailing_list = MailList(team_name, lock=False)
    until = datetime.datetime.now() + MAILING_LIST_CHECK_INTERVAL
    while True:
        for address in addresses:
            try:
                if mailing_list.getDeliveryStatus(address) != state:
                    break
            except NotAMemberError:
                # The address is not a member, so it can't be in the state.
                break
        else:
            # All addresses are in the specified state.  Return None on
            # success, so that the doctest doesn't need an extra line to match
            # the output.
            return None
        if datetime.datetime.now() > until:
            return 'Timed out'
        time.sleep(SECONDS_TO_SNOOZE)
        # Reload the mailing list data and go around again.
        mailing_list.Load()


def ensure_addresses_are_enabled(team_name, *addresses):
    """Ensure that addresses are subscribed and enabled."""
    _ensure_addresses_are_in_state(team_name, ENABLED, addresses)


def ensure_addresses_are_disabled(team_name, *addresses):
    """Ensure that addresses are subscribed but disabled."""
    # Use BYUSER because that's the non-enabled state that the implementation
    # uses to represent an unsubscribed team member.
    _ensure_addresses_are_in_state(team_name, BYUSER, addresses)
