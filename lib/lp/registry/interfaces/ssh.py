# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SSH key interfaces."""

__metaclass__ = type

__all__ = [
    'ISSHKey',
    'ISSHKeySet',
    'SSH_KEY_TYPE_TO_TEXT',
    'SSH_TEXT_TO_KEY_TYPE',
    'SSHKeyAdditionError',
    'SSHKeyType',
    ]

import httplib

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from lazr.restful.declarations import (
    error_status,
    export_as_webservice_entry,
    exported,
    )
from zope.interface import Interface
from zope.schema import (
    Choice,
    Int,
    TextLine,
    )

from lp import _


class SSHKeyType(DBEnumeratedType):
    """SSH key type

    SSH (version 2) can use RSA or DSA keys for authentication. See
    OpenSSH's ssh-keygen(1) man page for details.
    """

    RSA = DBItem(1, """
        RSA

        RSA
        """)

    DSA = DBItem(2, """
        DSA

        DSA
        """)


SSH_KEY_TYPE_TO_TEXT = {
    SSHKeyType.RSA: "ssh-rsa",
    SSHKeyType.DSA: "ssh-dss",
}


SSH_TEXT_TO_KEY_TYPE = {v: k for k, v in SSH_KEY_TYPE_TO_TEXT.items()}


class ISSHKey(Interface):
    """SSH public key"""

    export_as_webservice_entry('ssh_key')

    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True, readonly=True)
    personID = Int(title=_('Owner ID'), required=True, readonly=True)
    keytype = exported(Choice(title=_("Key type"), required=True,
                     vocabulary=SSHKeyType, readonly=True))
    keytext = exported(TextLine(title=_("Key text"), required=True,
                       readonly=True))
    comment = exported(TextLine(title=_("Comment describing this key"),
                       required=True, readonly=True))

    def destroySelf():
        """Remove this SSHKey from the database."""

    def getFullKeyText():
        """Get the full text of the SSH key."""


class ISSHKeySet(Interface):
    """The set of SSHKeys."""

    def new(person, sshkey, send_notification=True, dry_run=False):
        """Create a new SSHKey pointing to the given Person.

        :param person: The IPerson to add the ssh key to.
        :param sshkey: The full ssh key text.
        :param send_notification: Set to False to supress sending the user an
            email about the change.
        :param dry_run: Perform all the format and vaulnerability checks, but
            don't actually add the key. Causes the method to return None,
            rather than an instance of ISSHKey.
        """

    def getByID(id, default=None):
        """Return the SSHKey object for the given id.

        Return the given default if there's now object with the given id.
        """

    def getByPeople(people):
        """Return SSHKey object associated to the people provided."""

    def getByPersonAndKeyText(person, sshkey):
        """Get an SSH key for a person with a specific key text.

        :param person: The person who owns the key.
        :param sshkey: The full ssh key text.
        :raises SSHKeyAdditionError: If 'sshkey' is invalid.
        """


@error_status(httplib.BAD_REQUEST)
class SSHKeyAdditionError(Exception):
    """Raised when the SSH public key is invalid."""
