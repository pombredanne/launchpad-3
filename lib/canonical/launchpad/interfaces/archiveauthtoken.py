# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""ArchiveAuthToken interface."""

__metaclass__ = type

__all__ = [
    'IArchiveAuthToken',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces.archive import IArchive
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr.fields import Reference


class IArchiveAuthToken(Interface):
    """An interface for Archive Authorisation Tokens."""

    id = Int(title=_('ID'), required=True, readonly=True)

    archive = Reference(
        IArchive, title=_("Archive"), required=True,
        description=_("The archive for this authorisation token."))

    person = Reference(
        IPerson, title=_("Person"), required=True,
        description=_("The person for this authorisation token."))

    date_created = Datetime(
        title=_("Date Created"), required=True,
        description=_("The timestamp when the token was created."))

    date_deactivated = Datetime(
        title=_("Date De-activated"), required=False,
        description=_("The timestamp when the token was de-activated."))

    token = TextLine(
        title=_("Token"), required=True,
        description=_("The access token to the archive for this person."))
