# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for things which have Tickets."""

__metaclass__ = type

__all__ = [
    'IHasTickets',
    'ITicketTarget',
    'IManageSupportContacts',
    'TicketSort',
    ]

from canonical.launchpad import _
from zope.interface import Interface
from zope.schema import Bool, Choice, List


class IHasTickets(Interface):
    """An object that has tickets attached to it.

    Thus far, this is true of people, distros, products.
    """

    def tickets(quantity=None):
        """Support tickets for this source package, sorted newest first.

        If needed, you can limit the number of tickets returned by passing a
        number to the "quantity" parameter.
        """


class TicketSort:
    """A class listing valid ticket search sort order."""

    RELEVANCY = 5
    """Sort by relevancy of the ticket toward the search text."""

    OLDEST_FIRST = 10
    """Sort tickets from oldset to newest."""

    NEWEST_FIRST = 15
    """Sort ticket from newest to oldest."""


class ITicketTarget(IHasTickets):
    """An object that can have a new ticket created for  it."""

    def newTicket(owner, title, description, when=None):
        """Create a new support request, or trouble ticket.

        A new tickets is created with status OPEN.

        The owner and all of the target support contacts will be subscribed
        to the ticket.
        """

    def getTicket(ticket_num):
        """Return the ticket number, if it is applicable to this target.

        If there is no such ticket number for this target, return None
        """

    def searchTickets(search_text=None, status=None, sort=None):
        """Search the object's tickets.

        search_text is a text query that should be matched against the
        tickets full text index. When search_text is None, all tickets should
        be considered as matching this criteria.

        status restricts the list of tickets that are searched. When status
        is None, the implementation is free to search the status it feels
        appropriate for the context. If status is the empty list, no filtering
        on status should be done.

        sort specifies the sort order of the returned tickets. It should be
        one of attributes defined in the TicketSort class.
        Default is implementation dependant."""

    def addSupportContact(person):
        """Adds a new support contact.

        Returns True if the person was added, False if he already was a
        support contact.
        """

    def removeSupportContact(person):
        """Removes a support contact.

        Returns True if the person was removed, False if he isn't a
        support contact.
        """

    support_contacts = List(
        title=_("Support Contacts"),
        description=_(
            "Persons that will be automatically subscribed to new support"
            " requests."),
        value_type=Choice(vocabulary="ValidPersonOrTeam"))


class IManageSupportContacts(Interface):
    """Schema for managing support contacts."""

    want_to_be_support_contact = Bool(
        title=_("Subscribe me automatically to new suppport request"),
        required=False)
    support_contact_teams = List(
        title=_("Team support contacts"),
        value_type=Choice(vocabulary="PersonActiveMembership"),
        required=False)
