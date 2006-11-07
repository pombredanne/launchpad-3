# Copyright 2005-2006 Canonical Ltd.  All rights reserved.

"""Interfaces for things which have Tickets."""

__metaclass__ = type

__all__ = [
    'ITicketTarget',
    'IManageSupportContacts',
    'ISearchTicketsForm',
    'TICKET_STATUS_DEFAULT_SEARCH',
    ]

import sets

from zope.interface import Interface
from zope.schema import Bool, Choice, List, Set, TextLine

from canonical.launchpad import _
from canonical.lp.dbschema import TicketSort, TicketStatus


TICKET_STATUS_DEFAULT_SEARCH = (
    TicketStatus.OPEN, TicketStatus.NEEDSINFO, TicketStatus.ANSWERED,
    TicketStatus.SOLVED)


class ITicketTarget(Interface):
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
                      owner=None, sort=None):
        """Search the object's tickets.

        :search_text: A string that is matched against the ticket
        title and description. If None, the search_text is not included as
        a filter criteria.

        :status: A sequence of TicketStatus Items. If None or an empty
        sequence, the status is not included as a filter criteria.

        :owner: The IPerson that created the ticket.

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

    registered_support_contacts = List(
        title=_("Registered Support Contacts"),
        description=_(
            "IPersons that registered as support contacts explicitely on "
            "this target. (support_contacts may include support contacts "
            "inherited from other context.)"),
        value_type=Choice(vocabulary="ValidPersonOrTeam"))


# These schemas are only used by browser/tickettarget.py and should really
# live there. See Bug #66950.
class IManageSupportContacts(Interface):
    """Schema for managing support contacts."""

    want_to_be_support_contact = Bool(
        title=_("Subscribe me automatically to new suppport request"),
        required=False)
    support_contact_teams = List(
        title=_("Team support contacts"),
        value_type=Choice(vocabulary="PersonActiveMembership"),
        required=False)


class ISearchTicketsForm(Interface):
    """Schema for the search ticket form."""

    search_text = TextLine(title=_('Search text:'), required=False)

    sort = Choice(title=_('Sort order:'), required=True,
                  vocabulary='TicketSort',
                  default=TicketSort.RELEVANCY)

    status = Set(title=_('Status:'), required=False,
                 value_type=Choice(vocabulary='TicketStatus'),
                 default=sets.Set(TICKET_STATUS_DEFAULT_SEARCH))
