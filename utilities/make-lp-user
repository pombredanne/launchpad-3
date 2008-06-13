#!/usr/bin/python2.4
import _pythonpath

import os
import sys

import transaction

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IPersonSet,
    ISSHKeySet,
    SSHKeyType,
    TeamMembershipStatus,
    )
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.testing.factory import LaunchpadObjectFactory

# Shut up, pyflakes.
_pythonpath = _pythonpath


DEFAULT_PASSWORD = 'test'
factory = LaunchpadObjectFactory()


def make_person(username):
    email = '%s@example.com' % username
    person = factory.makePerson(
        name=username, password=DEFAULT_PASSWORD, email=email)
    print "username: %s" % (username,)
    print "email:    %s" % (email,)
    print "password: %s" % (DEFAULT_PASSWORD,)
    return person


def add_person_to_teams(person, team_names):
    person_set = getUtility(IPersonSet)
    for team_name in team_names:
        team = person_set.getByName(team_name)
        team.addMember(
            person, person, status=TeamMembershipStatus.APPROVED)
    print "teams:    %s" % ' '.join(team_names)


def add_ssh_public_keys(person):
    ssh_dir = os.path.expanduser('~/.ssh')
    key_set = getUtility(ISSHKeySet)
    key_guesses = [
        (SSHKeyType.RSA, 'id_rsa.pub'),
        (SSHKeyType.DSA, 'id_dsa.pub'),
        ]
    for key_type, guessed_filename in key_guesses:
        guessed_filename = os.path.join(ssh_dir, guessed_filename)
        try:
            public_key_file = open(guessed_filename, 'r')
            try:
                public_key = public_key_file.read()
            finally:
                public_key_file.close()
        except (OSError, IOError):
            continue
        public_key = public_key.split()[1]
        key_set.new(person, key_type, public_key, 'Added by utility script.')
        print 'Registered SSH key: %s' % (guessed_filename,)


def main(arguments):
    execute_zcml_for_scripts()
    username, teams = arguments[0], arguments[1:]
    transaction.begin()
    person = make_person(username)
    add_person_to_teams(person, teams)
    add_ssh_public_keys(person)
    transaction.commit()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
