# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""ArchiveSubscriber interface."""

__metaclass__ = type

__all__ = [
    'IArchiveSubscriber',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, Text

from canonical.launchpad import _
from canonical.launchpad.interfaces.archive import IArchive
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr import DBEnumeratedType, DBItem
from canonical.lazr.fields import Choice, Reference


class ArchiveSubscriberStatus(DBEnumeratedType):
    """The status of an `ArchiveSubscriber`."""

    ACTIVE = DBItem(1, """
        Active

        The subscription is active.
        """)

    EXPIRED = DBItem(2, """
        Expired

        The subscription has expired.
        """)

    CANCELLED = DBItem(3, """
        Cancelled

        The subscription was cancelled.
        """)


class IArchiveSubscriber(Interface):
    """An interface for archive subscribers."""

    id = Int(title=_('ID'), required=True, readonly=True)

    archive = Reference(
        IArchive, title=_("Archive"), required=True,
        description=_("The archive for this subscription."))

    registrant = Reference(
        IPerson, title=_("Registrant"), required=True,
        description=_("The person who registered this subscription."))

    date_created = Datetime(
        title=_("Date Created"), required=True,
        description=_("The timestamp when the subscription was created."))

    subscriber = Reference(
        IPerson, title=_("Subscriber"), required=True,
        description=_("The person who is subscribed."))

    date_expires = Datetime(
        title=_("Date of Expiration"), required=False,
        description=_("The timestamp when the subscription will expire."))

    status = Choice(
        title=_("Status"), required=True,
        vocabulary=ArchiveSubscriberStatus,
        description=_("The status of this subscription."))

    description = Text(
        title=_("Description"), required=False,
        description=_("Free text describing this subscription."))

    date_cancelled = Datetime(
        title=_("Date of Cancellation"), required=False,
        description=_("The timestamp when the subscription was cancelled."))


class IArchiveSubscriberSet(Interface):
    """An interface for the set of all archive subscribers."""
    def new(archive, registrant, subscriber, status=None, date_created=None,
            date_expires=None, description=None):
        """Make a new token.

        :param archive: An IArchive for the new token
        :param registrant: An IPerson who is creating this token
        :param subscriber: An IPerson whom this token is for
        :param status: Optional `ArchiveAuthTokenStatus`, defaults to ACTIVE
        :param date_created: Optional, defaults to now
        :param date_expires: Optional, defaults to None
        :param description: Optional, defaults to None

        :return: An object conforming to  IArchiveAuthToken
        """

