#!/usr/bin/python
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

"""Writing of htaccess and htpasswd files."""

__metaclass__ = type

__all__ = [
    'htpasswd_credentials_for_archive',
    'write_htaccess',
    'write_htpasswd',
    ]


import crypt
from operator import attrgetter
import os

from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.interfaces.archiveauthtoken import IArchiveAuthTokenSet


HTACCESS_TEMPLATE = """
AuthType           Basic
AuthName           "Token Required"
AuthUserFile       %(path)s/.htpasswd
Require            valid-user
"""

BUILDD_USER_NAME = "buildd"


def write_htaccess(htaccess_filename, distroot):
    """Write a htaccess file for a private archive.

    :param htaccess_filename: Filename of the htaccess file.
    :param distroot: Archive root path
    """
    interpolations = {"path": distroot}
    file = open(htaccess_filename, "w")
    try:
        file.write(HTACCESS_TEMPLATE % interpolations)
    finally:
        file.close()


def write_htpasswd(filename, users):
    """Write out a new htpasswd file.

    :param filename: The file to create.
    :param users: Iterable over (user, password, salt) tuples.
    """
    if os.path.isfile(filename):
        os.remove(filename)

    file = open(filename, "a")
    try:
        for entry in users:
            user, password, salt = entry
            encrypted = crypt.crypt(password, salt)
            file.write("%s:%s\n" % (user, encrypted))
    finally:
        file.close()


def htpasswd_credentials_for_archive(archive, tokens=None):
    """Return credentials for an archive for use with write_htpasswd.

    :param archive: An `IArchive` (must be private)
    :param tokens: Optional iterable of `IArchiveAuthToken`s.
    :return: Iterable of tuples with (user, password, salt) for use with
        write_htpasswd.
    """
    assert archive.private, "Archive %r must be private" % archive

    if tokens is None:
        tokens = getUtility(IArchiveAuthTokenSet).getByArchive(archive)
    tokens = list(tokens)

    # The first .htpasswd entry is the buildd_secret.
    yield (BUILDD_USER_NAME, archive.buildd_secret, BUILDD_USER_NAME[:2])

    person_ids = map(attrgetter('person_id'), tokens)
    valid_persons = dict((person.id, person) for person in
        getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            person_ids, need_validity=True) if person.is_valid_person)
    usable_tokens = [(token, valid_persons[token.person_id])
        for token in tokens if token.person_id in valid_persons]
    # Iterate over tokens and write the appropriate htpasswd
    # entries for them.  Use a consistent sort order so that the
    # generated file can be compared to an existing one later.
    for token, person in sorted(usable_tokens, key=lambda item:item[0].id):
        yield (person.name, token.token, person.name[:2])
