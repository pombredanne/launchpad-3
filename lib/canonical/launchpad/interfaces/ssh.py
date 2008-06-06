# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""SSH key interfaces."""

__metaclass__ = type

__all__ = [
    'ISSHKey',
    'ISSHKeySet',
    'SSHKeyType',
    ]

from zope.schema import Choice, Int, TextLine
from zope.interface import Interface

from canonical.lazr import DBEnumeratedType, DBItem
from canonical.launchpad import _


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


class ISSHKey(Interface):
    """SSH public key"""
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True, readonly=True)
    personID = Int(title=_('Owner ID'), required=True, readonly=True)
    keytype = Choice(title=_("Key type"), required=True,
                     vocabulary=SSHKeyType)
    keytext = TextLine(title=_("Key text"), required=True)
    comment = TextLine(title=_("Comment describing this key"),
                       required=True)

    def destroySelf():
        """Remove this SSHKey from the database."""


class ISSHKeySet(Interface):
    """The set of SSHKeys."""

    def new(person, keytype, keytext, comment):
        """Create a new SSHKey pointing to the given Person."""

    def getByID(id, default=None):
        """Return the SSHKey object for the given id.

        Return the given default if there's now object with the given id.
        """

    def getByPeople(people):
        """Return SSHKey object associated to the people provided."""

