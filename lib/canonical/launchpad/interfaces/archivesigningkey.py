# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""ArchiveSigningKey interface."""

__metaclass__ = type

__all__ = [
    'IArchiveSigningKey',
    ]

from zope.interface import Interface
from zope.schema import Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.archive import IArchive


class IArchiveSigningKey(Interface):
    """`ArchiveSigningKey` interface."""

    archive = Object(
        title=_('Corresponding IArchive'), required=True, schema=IArchive)

    def generateSigningKey():
        """Generate a new GPG secret/public key pair."""

    def signRepository():
        """Sign the corresponding repository."""


