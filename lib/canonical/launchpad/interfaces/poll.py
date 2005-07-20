# Copyright 2004 Canonical Ltd.  All rights reserved.

__all__ = ['IPoll', 'IPollSet', 'IPollSubset', 'IPollOption',
           'IPollOptionSet', 'IPollOptionSubset', 'IVote', 'IVoteCast',
           'PollStatus']

# Imports from zope
from zope.schema import Bool, Choice, Datetime, Int, Text, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.validators.name import valid_name
from canonical.lp.dbschema import PollSecrecy, PollAlgorithm


class IPoll(Interface):
    """A poll for a given proposition in a team."""

    id = Int(title=_('The unique ID'), required=True, readonly=True)

    team = Int(
        title=_('The team that this poll refers to.'), required=True,
        readonly=True)

    name = TextLine(
        title=_('The unique name of this poll.'),
        description=_('A short unique name, beginning with a lower-case '
                      'letter or number, and containing only letters, '
                      'numbers, dots, hyphens, or plus signs.'),
        required=True, readonly=False, constraint=valid_name)

    title = TextLine(
        title=_('The title of this poll.'), required=True, readonly=False)

    dateopens = Datetime(
        title=_('The date and time when this poll opens.'), required=True,
        readonly=False)

    datecloses = Datetime(
        title=_('The date and time when this poll closes.'), required=True,
        readonly=False)

    proposition = Text(
        title=_('The proposition that is going to be voted.'), required=True,
        readonly=False)

    type = Choice(
        title=_('The type of this poll.'), required=True,
        readonly=False, vocabulary='PollAlgorithm',
        default=PollAlgorithm.CONDORCET)

    allowspoilt = Bool(
        title=_('Users can spoil their votes?'), required=True,
        readonly=False, default=True)

    secrecy = Choice(
        title=_('The secrecy of the Poll.'), required=True,
        readonly=False, vocabulary='PollSecrecy',
        default=PollSecrecy.SECRET)

    def isOpen(when=None):
        """Return True if this Poll is still open.
        
        The optional <when> argument is used only by our tests, to test if the
        poll is/was/will be open at a specific date.
        """

    def personVoted(person):
        """Return True if <person> has already voted in this poll."""


class PollStatus:
    """A placeholder for the constants used when searching for polls."""

    OPEN_POLLS = 'open'
    CLOSED_POLLS = 'closed'
    NOT_YET_OPENED_POLLS = 'not-yet-opened'


class IPollSet(Interface):
    """The set of Poll objects."""

    def new(team, name, title, proposition, dateopens, datecloses,
            type, secrecy, allowspoilt):
        """Create a new Poll for the given team."""

    def selectByTeam(team,
                     status=frozenset([PollStatus.OPEN_POLLS,
                                       PollStatus.CLOSED_POLLS,
                                       PollStatus.NOT_YET_OPENED_POLLS]),
                     orderBy=None, when=None):
        """Return all Polls for the given team, filtered by status.
        
        <status> is a frozenset() containing as many values as you want from
        PollStatus.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Poll._defaultOrder.
        
        The optional <when> argument is used only by our tests, to test if the
        poll is/was/will-be open at a specific date.
        """

    def getByTeamAndName(team, name, default=None):
        """Return the Poll for the given team with the given name.

        Return <default> if there's no Poll with this name for that team.
        """


class IPollSubset(Interface):
    """The set of Poll objects for a given team."""

    team = Attribute(_("The team of these polls."))

    title = Attribute('Polls Page Title')

    def new(name, title, proposition, dateopens, datecloses, type, secrecy,
            allowspoilt):
        """Create a new Poll for this team."""

    def getAll():
        """Return all Polls of this team."""

    def getOpenPolls(when=None):
        """Return all Open Polls for this team ordered by the date they'll
        close.

        The optional <when> argument is used only by our tests, to test if the
        poll is/was/will be open at a specific date.
        """

    def getNotYetOpenedPolls(when=None):
        """Return all Not-Yet-Opened Polls for this team ordered by the date
        they'll open.

        The optional <when> argument is used only by our tests, to test if the
        poll is/was/will be open at a specific date.
        """

    def getClosedPolls(when=None):
        """Return all Closed Polls for this team ordered by the date they
        closed.

        The optional <when> argument is used only by our tests, to test if the
        poll is/was/will be open at a specific date.
        """

    def getByName(name, default=None):
        """Return the Poll of this team with the given name.

        Return <default> if there's no Poll with this name.
        """


class IPollOption(Interface):
    """An option to be voted in a given Poll."""

    id = Int(title=_('The unique ID'), required=True, readonly=True)

    poll = Int(
        title=_('The Poll to which this option refers to.'), required=True,
        readonly=True)

    name = TextLine(
        title=_('The name of this option.'), required=True, readonly=False)

    shortname = TextLine(
        title=_('The short name of this option. If not specified, this will '
                'be the same as the name'),
        required=False, readonly=False)

    active = Bool(
        title=_('Is this option active?'), required=True, readonly=False,
        default=True)

    title = Attribute('Poll Option Page Title')


class IPollOptionSet(Interface):
    """The set of PollOption objects."""

    def new(poll, name, shortname, active=True):
        """Create a new PollOption."""

    def selectByPoll(poll, only_active=False):
        """Return all PollOptions of the given poll.
        
        If <only_active> is True, then return only the active polls.
        """

    def getByPollAndId(poll, id, default=None):
        """Return the PollOption with the given id.

        Return <default> if there's no PollOption with the given id or if that
        PollOption is not in the given poll.
        """


class IPollOptionSubset(Interface):
    """The set of PollOption objects within a given poll."""

    poll = Attribute(_("The poll to which all PollOptions refer to."))

    title = Attribute('Poll Options Page Title')

    def new(name, shortname=None, active=True):
        """Create a new PollOption for this poll."""

    def getAll():
        """Return all PollOptions of this poll."""

    def get_default(id, default=None):
        """Return the PollOption of this poll with the given id.

        Return <default> if there's no PollOption with this id in this poll.
        """

    def getActive():
        """Return all PollOptions of this poll that are active."""


class IVoteCast(Interface):
    """Here we store who voted in a Poll, but not their votes."""

    id = Int(title=_('The unique ID'), required=True, readonly=True)

    person = Int(
        title=_('The Person that voted.'), required=False, readonly=True)

    poll = Int(
        title=_('The Poll in which the person voted.'), required=True,
        readonly=True)


class IVote(Interface):
    """Here we store the vote itself, linked to a special token.
    
    This token is given to the user when he votes, so he can change his vote
    later.
    """

    id = Int(
        title=_('The unique ID'), required=True, readonly=True)

    person = Int(
        title=_('The Person that voted.'), required=False, readonly=True)

    poll = Int(
        title=_('The Poll in which the person voted.'), required=True,
        readonly=True)

    option = Int(
        title=_('The PollOption choosen.'), required=True, readonly=False)

    preference = Int(
        title=_('The preference of the choosen PollOption'), required=True,
        readonly=False)

    token = Text(
        title=_('The token we give to the user.'), required=True, readonly=True)

