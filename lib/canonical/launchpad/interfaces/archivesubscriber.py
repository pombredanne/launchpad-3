# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""ArchiveSubscriber interface."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscriberStatus',
    'IArchiveSubscriber',
    'IArchiveSubscriberSet'
    ]

from zope.interface import Interface
from zope.schema import Datetime, Choice, Int, Text

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.interfaces.archive import IArchive
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr import DBEnumeratedType, DBItem
from canonical.lazr.fields import Reference


class ArchiveSubscriberStatus(DBEnumeratedType):
    """The status of an `ArchiveSubscriber`."""

    CURRENT = DBItem(1, """
        Active

        The subscription is current.
        """)

    EXPIRED = DBItem(2, """
        Expired

        The subscription has expired.
        """)

    CANCELLED = DBItem(3, """
        Cancelled

        The subscription was cancelled.
        """)


class IArchiveSubscriberView(Interface):
    """An interface for launchpad.View ops on archive subscribers."""

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

    subscriber = PublicPersonChoice(
        title=_("Subscriber"), required=True, vocabulary='ValidPersonOrTeam',
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

    cancelled_by = Reference(
        IPerson, title=_("Cancelled By"), required=False,
        description=_("The person who cancelled the subscription."))


class IArchiveSubscriberEdit(Interface):
    """An interface for launchpad.Edit ops on archive subscribers."""

    def cancel(cancelled_by):
        """Cancel a subscription.
        
        :param cancelled_by: An `IPerson` who is cancelling the subscription.

        Sets cancelled_by to the supplied person and date_cancelled to
        the current date/time.
        """


class IArchiveSubscriber(IArchiveSubscriberView, IArchiveSubscriberEdit):
    """An interface for archive subscribers."""


class IArchiveSubscriberSet(Interface):
    """An interface for the set of all archive subscribers."""

    def getBySubscriber(subscriber, archive=None, current_only=True):
        """Return all the subscriptions for a person.

        :param subscriber: An `IPerson` for whom to return all
            `ArchiveSubscriber` records.
        :param archive: An optional `IArchive` which restricts
            the results to that particular archive.
        :param current_only: Whether the result should only include current
            subscriptions (which is the default).
        """

    def getByArchive(archive, current_only=True):
        """Return all the subscripions for an archive.

        :param archive: An `IArchive` for which to return all
            `ArchiveSubscriber` records.
        :param current_only: Whether the result should only include current
            subscriptions (which is the default).
        """
