# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for a Support Request ("Ticket")."""

__metaclass__ = type

__all__ = [
    'ITicket',
    'ITicketSet',
    ]

from zope.component import getUtility
from zope.interface import implements, Interface, Attribute
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from zope.schema import Datetime, Int, Choice, Text, TextLine

from canonical.launchpad.helpers import request_languages
from canonical.launchpad.interfaces import (
    IHasOwner, ILanguageSet, IMessageTarget)
from canonical.lp.dbschema import TicketStatus, TicketPriority

from canonical.launchpad import _


class TicketLanguageVocabularyFactory:
    """Factory for a vocabulary with all languages a ticket can be written in.
    
    This includes the user's preferred languages (excluding English and all
    its variants), the language the ticket is written in, in case we're
    dealing with an existing ticket and English.
    """

    implements(IContextSourceBinder)

    def __call__(self, context):
        # XXX: This import must stay here to avoid circular imports.
        # -- Guilherme Salgado, 2006-10-05
        from canonical.launchpad.webapp.publisher import (
            get_current_browser_request)
        languages = set()
        for lang in request_languages(get_current_browser_request()):
            # Ignore English and all its variants.
            if not lang.code.startswith('en'):
                languages.add(lang)
        if (context is not None and ITicket.providedBy(context) and
            context.language.code != 'en'):
            languages.add(context.language)
        languages = list(languages)
        # Now we insert English as the first element, to make it the default
        # one.
        languages.insert(0, getUtility(ILanguageSet)['en'])
        terms = [SimpleTerm(lang, lang.code, lang.displayname)
                 for lang in languages]
        return SimpleVocabulary(terms)


class ITicket(IHasOwner, IMessageTarget):
    """A single support request, or trouble ticket."""

    id = Int(title=_('Ticket Number'), required=True, readonly=True,
        description=_("The ticket or tracking number for this support "
        "request."))
    title = TextLine(
        title=_('Summary'), required=True, description=_(
        "A one-line summary of the issue or problem."))
    description = Text(
        title=_('Description'), required=True, description=_(
        "Include as much detail as possible: what "
        u"you\N{right single quotation mark}re trying to achieve, what steps "
        "you take, what happens, and what you think should happen instead."))
    status = Choice(
        title=_('Status'), vocabulary='TicketStatus',
        default=TicketStatus.OPEN)
    priority = Choice(
        title=_('Priority'), vocabulary='TicketPriority',
        default=TicketPriority.NORMAL)
    language = Choice(
        title=_('Language'), source=TicketLanguageVocabularyFactory(),
        description=_('The language in which this request is written.'
                      '(<a href="/people/+editlanguages">Change your '
                      'preferred languages</a>)'))
    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    assignee = Choice(title=_('Assignee'), required=False,
        description=_("The person responsible for helping to resolve the "
        "support request."),
        vocabulary='ValidPersonOrTeam')
    answerer = Choice(title=_('Answered By'), required=False,
        description=_("The person who last provided a response intended to "
        "resolve the support request."),
        vocabulary='ValidPersonOrTeam')
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    datedue = Datetime(
        title=_('Date Due'), required=False, default=None,
        description=_("The date by which we should have resolved this support "
        "request."))
    datelastquery = Datetime(title=_("Date Last Queried"), required=True,
        description=_("The date on which we last heard from the "
        "customer (owner)."))
    datelastresponse = Datetime(title=_("Date last Responded"),
        required=False,
        description=_("The date on which we last communicated "
        "with the customer. The combination of datelastquery and "
        "datelastresponse tells us in whose court the ball is."))
    dateanswered = Datetime(title=_("Date Answered"), required=False,
        description=_(
            "The date on which the submitter confirmed that the ticket is "
            "Answered."))
    product = Choice(title=_('Upstream Product'), required=False,
        vocabulary='Product', description=_('Select the upstream product '
        'with which you need support.'))
    distribution = Choice(title=_('Distribution'), required=False,
        vocabulary='Distribution', description=_('Select '
        'the distribution for which you need support.'))
    sourcepackagename = Choice(title=_('Source Package'), required=False,
        vocabulary='SourcePackageName', description=_('The source package '
        'in the distribution which contains the software with which you '
        'are experiencing difficulties.'))
    whiteboard = Text(title=_('Status Whiteboard'), required=False,
        description=_('Up-to-date notes on the status of the request.'))
    # other attributes
    target = Attribute('The product or distribution to which this ticket '
        'belongs.')
    can_be_reopened = Attribute('Whether the ticket is in a state '
        'that can be "re-opened".')
    can_be_rejected = Attribute('Whether the ticket can be rejected.')
    is_resolved = Attribute("Whether the ticket is resolved.")
    # joins
    subscriptions = Attribute('The set of subscriptions to this ticket.')
    reopenings = Attribute("Records of times when this was reopened.")

    # workflow
    def reject(rejector):
        """Mark this ticket as rejected.

        This can only be done to tickets that are not CLOSED or ANSWERED. It
        will remember the dateclosed (rejection is the same as closing,
        effectively). It will also store this as the dateanswered, and it
        will remember the person who rejected it as the answerer.

        Returns True if the ticket was actually, rejected, False if for some
        reason no rejection happened (for example, it was already OPEN).
        """

    def reopen(reopener):
        """Open a ticket that has formerly been closed, or rejected."""

    def acceptAnswer(acceptor):
        """Mark the ticket as Answered.

        dateanswered will be set to the current time.
        """

    # subscription-related methods
    def subscribe(person):
        """Subscribe this person to the ticket."""

    def isSubscribed(person):
        """Return a boolean indicating whether the person is subscribed."""

    def unsubscribe(person):
        """Remove the person's subscription to this ticket."""

    def getSubscribers():
        """Return a list of Person that should be notified of changes to this
        ticket. That is the union of getDirectSubscribers() and
        getIndirectSubscribers().
        """

    def getDirectSubscribers():
        """Return the set of persons who are subscribed to this ticket."""

    def getIndirectSubscribers():
        """Return the set of persons who are implicitely subscribed to this
        ticket. That will be the ticket's target support contact list.
        """


class ITicketSet(Interface):
    """A container for tickets."""

    title = Attribute('Title')

    latest_tickets = Attribute("The 10 most recently created support "
        "requests in Launchpad.")

    def get(ticket_id, default=None):
        """Return the ticket with the given id.

        Return :default: if no such ticket exists.
        """

