#!/usr/bin/python
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Writing of htaccess and htpasswd files."""

__metaclass__ = type

__all__ = [
    'htpasswd_credentials_for_archive',
    'write_htaccess',
    'write_htpasswd',
    ]


import crypt
from operator import itemgetter
import os

from lp.registry.model.person import Person
from lp.services.database.interfaces import IStore
from lp.soyuz.model.archiveauthtoken import ArchiveAuthToken


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
        for user, password, salt in users:
            encrypted = crypt.crypt(password, salt)
            file.write("%s:%s\n" % (user, encrypted))
    finally:
        file.close()


def htpasswd_credentials_for_archive(archive):
    """Return credentials for an archive for use with write_htpasswd.

    :param archive: An `IArchive` (must be private)
    :return: Iterable of tuples with (user, password, salt) for use with
        write_htpasswd.
    """
    assert archive.private, "Archive %r must be private" % archive

    tokens = IStore(ArchiveAuthToken).find(
        (ArchiveAuthToken.person_id, ArchiveAuthToken.name,
            ArchiveAuthToken.token),
        ArchiveAuthToken.archive == archive,
        ArchiveAuthToken.date_deactivated == None)
    # We iterate tokens more than once - materialise it.
    tokens = list(tokens)

    # Preload map with person ID to person name.
    person_ids = map(itemgetter(0), tokens)
    names = dict(
        IStore(Person).find(
            (Person.id, Person.name), Person.id.is_in(set(person_ids))))

    # Format the user field by combining the token list with the person list
    # (when token has person_id) or prepending a '+' (for named tokens).
    output = []
    for person_id, token_name, token in tokens:
        if token_name:
            # A named auth token.
            output.append(('+' + token_name, token, token_name[:2]))
        else:
            # A subscription auth token.
            output.append((names[person_id], token, names[person_id][:2]))

    # The first .htpasswd entry is the buildd_secret.
    yield (BUILDD_USER_NAME, archive.buildd_secret, BUILDD_USER_NAME[:2])

    # Iterate over tokens and write the appropriate htpasswd entries for them.
    # Sort by name/person ID so the file can be compared later.
    for user, password, salt in sorted(output):
        yield (user, password, salt)
