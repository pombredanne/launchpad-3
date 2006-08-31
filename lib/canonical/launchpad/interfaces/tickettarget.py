# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for things which have Tickets."""

__metaclass__ = type

__all__ = [
    'IHasTickets',
    'ITicketTarget',
    'IManageSupportContacts',
    'TICKET_STATUS_DEFAULT_SEARCH',
    ]

from zope.interface import Interface
from zope.schema import Bool, Choice, List

from canonical.launchpad import _
from canonical.lp.dbschema import TicketStatus


class IHasTickets(Interface):
    """An object that has tickets attached to it.

    Thus far, this is true of people, distros, products.
    """

    def tickets(quantity=None):
        """Support tickets for this source package, sorted newest first.

        :quantity: An integer.

        If needed, you can limit the number of tickets returned by passing a
        number to the "quantity" parameter.
        """


TICKET_STATUS_DEFAULT_SEARCH = (TicketStatus.OPEN, TicketStatus.ANSWERED)


class ITicketTarget(IHasTickets):
    """An object that can have a new ticket created for  it."""

    def newTicket(owner, title, description, datecreated=None):
        """Create a new support request, or trouble ticket.

         A new ticket is created with status OPEN.

        The owner and all of the target support contacts will be subscribed
        to the ticket.

        :owner: An IPerson.
        :title: A string.
        :description: A string.
        :datecreated:  A datetime object that will be used for the datecreated
                attribute. Defaults to canonical.database.constants.UTC_NOW.
        """

    def getTicket(ticket_id):
        """Return the ticket number, if it is applicable to this target.

        :ticket_id: A ticket id.

        If there is no such ticket number for this target, return None
        """

    def searchTickets(search_text=None, status=TICKET_STATUS_DEFAULT_SEARCH,
                      sort=None):
        """Search the object's tickets.

        :search_text: A string that is matched against the ticket
        title and description. If None, the search_text is not included as
        a filter criteria.

        :status: A sequence of TicketStatus Items. If None or an empty
        sequence, the status is not included as a filter criteria.

        :sort:  An attribute of TicketSort. If None, a default value is used.
        When there is a search_text value, the default is to sort by RELEVANCY,
        otherwise results are sorted NEWEST_FIRST.
        """

    def findSimilarTickets(title):
        """Return tickets similar to title.

        Return a list of ticket similar to the title provided. These tickets
        should be found using a fuzzy search. The list should be ordered
        from the most similar ticket to the least similar ticket.

        :title: A phrase
        """

    def addSupportContact(person):
        """Adds a new support contact.

        :person: An IPerson.

        Returns True if the person was added, False if he already was a
        support contact.
        """

    def removeSupportContact(person):
        """Removes a support contact.

        :person: An IPerson.

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
