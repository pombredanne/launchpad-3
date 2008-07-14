# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helper utilities."""

__metaclass__ = type
__all__ = [
    'collect_archive_message_ids',
    'create_list',
    'get_size',
    'pending_hold_ids',
    'print_mailman_hold',
    'review_list',
    'run_mailman',
    'subscribe',
    ]


import os
import re
import time
import errno
import pickle
import transaction

from subprocess import Popen, PIPE
from zope.component import getUtility

from canonical.launchpad.ftests import login, logout
from canonical.launchpad.ftests import mailinglists_helper
from canonical.launchpad.interfaces.mailinglist import IMailingListSet
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.testing.browser import Browser

from Mailman import mm_cfg
from Mailman.MailList import MailList
from Mailman.Utils import list_names


# This is where the Mailman command line scripts live.
import Mailman
MAILMAN_PKGDIR = os.path.dirname(Mailman.__file__)
MAILMAN_BINDIR = os.path.join(os.path.dirname(MAILMAN_PKGDIR), 'bin')

SPACE = ' '


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
    from canonical.launchpad.mailman.testing.logwatcher import LogWatcher
    # Watch Mailman's logs/serial file.
    serial_watcher = LogWatcher('serial')
    browser = Browser('foo.bar@canonical.com:test')
    browser.open('http://launchpad.dev:8085/+mailinglists')
    browser.getControl(name='field.' + list_name).value = [status]
    browser.getControl('Submit').click()
    serial_watcher.wait()
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
    browser.open('http://launchpad.dev/people/+newteam')
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
        'Mailing list was not created: %s' % list_names())
    return mailing_list


def run_mailman(*args):
    """Run a Mailman script."""
    proc = Popen(args, stdout=PIPE, stderr=PIPE, cwd=MAILMAN_BINDIR)
    stdout, stderr = proc.communicate()
    assert len(stderr) == 0, stderr
    return stdout


def subscribe(first_name, team_name):
    """Do everything you need to subscribe a person to a mailing list."""
    # Circular import.
    from canonical.launchpad.mailman.testing.logwatcher import LogWatcher
    # Create the person if she does not already exist, and join her to the
    # team.
    person_set = getUtility(IPersonSet)
    person = person_set.getByName(first_name.lower())
    if person is None:
        person = mailinglists_helper.new_person(first_name)
    team = getUtility(IPersonSet).getByName(team_name)
    person.join(team)
    # Subscribe her to the list.
    mailing_list = getUtility(IMailingListSet).get(team_name)
    mailing_list.subscribe(person)
    serial_watcher = LogWatcher('serial')
    transaction.commit()
    serial_watcher.wait()


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
