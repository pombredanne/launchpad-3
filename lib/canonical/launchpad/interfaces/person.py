# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Datetime, Int, Text, TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IPerson(Interface):
    """A Person."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Unique Launchpad Name'), required=True, readonly=False,
            )
    displayname = TextLine(
            title=_('Display Name'), required=True, readonly=False,
            )
    givenname = TextLine(
            title=_('Given Name'), required=False, readonly=False,
            )
    familyname = TextLine(
            title=_('Family Name'), required=False, readonly=False,
            )
    password = Password(
            title=_('Password'), required=True, readonly=False,
            )
    teamowner = Int(
            title=_('Team Owner'), required=False, readonly=False,
            )
    teamdescription = Text(
            title=_('Team Description'), required=False, readonly=False,
            )
    # TODO: This should be required in the DB, defaulting to something
    karma = Int(
            title=_('Karma'), required=False, readonly=True,
            )
    # TODO: This should be required in the DB, defaulting to something
    karmatimestamp = Datetime(
            title=_('Karma Timestamp'), required=False, readonly=True,
            )
    languages = Attribute(_('List of know languages by this person'))
    sshkeys = Attribute(_('List of SSH keys'))

    timezone_name = TextLine(
        title=_('Timezone Name'), required=False, readonly=False
        )

    # XXX: These fields are used only to generate the form to create a
    # new person.
    email = TextLine(title=_('Email'), required=True)
    password2 = Password(title=_('Confirm Password'), required=True)

    # Properties of the Person object.
    gpg = Attribute("GPG")
    irc = Attribute("IRC")    
    bugs = Attribute("Bug")
    wiki = Attribute("Wiki")
    teams = Attribute("List of teams this Person is a member of.")
    emails = Attribute("Email")
    jabber = Attribute("Jabber")
    archuser = Attribute("Arch user")    
    packages = Attribute("A Selection of SourcePackageReleases")
    activities = Attribute("Karma")
    distroroles = Attribute(("List of Distribution Roles Played by this "
                             "Person/Team."))
    memberships = Attribute(("List of Membership objects for Teams this "
                             "Person is a member of. Either as a PROPOSED "
                             "or CURRENT member."))
    translations = Attribute("Translations")
    preferredemail = Attribute(("The preferred email address for this "
                                "person. The one we'll use to communicate "
                                "with him."))
    validatedemails = Attribute("Emails with status VALIDATED")
    distroreleaseroles = Attribute(("List of DistributionRelease Roles "
                                    "Played by this Person/Team."))
    notvalidatedemails = Attribute("Emails waiting validation.")

    # XXX: salgado: 2005-11-01: Is it possible to move this properties to
    # ITeam to ensure that they are acessible only via Persons marked
    # with the ITeam interface?
    currentmembers = Attribute("List of approved Members of this Team.")
    subteams = Attribute(("List of subteams of this Team. That is, teams "
                          "which are members of this Team."))
    members = Attribute(("List of approved members with MEMBER role on this "
                         "Team."))
    administrators = Attribute(("List of approved members with ADMIN role on "
                                "this Team.")) 
    proposedmembers = Attribute("List of members awaiting for approval.")

    def browsername():
        """Return a textual name suitable for display in a browser."""

    def addLanguage(language):
        """Adds a new language to the list of know languages."""

    def removeLanguage(language):
        """Removed the language from the list of know languages."""

    def inTeam(team_name):
        """Return true if this person is in the named team."""

    def getMembershipByMember(member):
        """Return a Membership object of the given member in this team."""


class ITeam(IPerson):
    """ITeam extends IPerson.
    
    The teamowner should never be None."""


class IPersonSet(Interface):
    """The set of Persons."""

    def __getitem__(personid):
        """Returns the person with the given id.

        Raises KeyError if there is no such person.
        """

    def new(*args, **kwargs):
        """Create a new Person with given keyword arguments.
        These keyword arguments will be passed to Person, which is an
        SQLBase class and will do all the checks needed before inserting
        anything in the database. Please refer to the Person implementation
        to see what keyword arguments are allowed."""

    def get(personid, default=None):
        """Returns the person with the given id.

        Returns the default value if there is no such person.
        """

    def getByEmail(email, default=None):
        """Returns the person with the given email address.

        Returns the default value if there is no such person.
        """
    
    def getByName(name):
        """Returns the person with the given name."""
    
    def getAll():
        """Returns all People in a database"""

    def getContributorsForPOFile(pofile):
        """Returns the list of persons that have an active contribution for a
        concrete POFile."""

    def createPerson(displayname, givenname, familyname, password, email):
        """Creates a new person."""


class IEmailAddress(Interface):
    """The object that stores the IPerson's emails."""
    id = Int(
        title=_('ID'), required=True, readonly=True,
        )
    email = Text(
        title=_('Email Address'), required=True,
        )
    status = Int(
        title=_('Email Address Status'), required=True,
        )
    person = Int(
        title=_('Person'), required=True,
        )
    statusname = Attribute("StatusName")


class IMembership(Interface):
    """Membership for Users"""
    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("Team"), required=True, readonly=False)
    person = Int(title=_("Owner"), required=True, readonly=False)

    role= Int(title=_("Role of the Person on the Team"), required=True,
              readonly=False)

    status= Int(title=_("If Membership was approved or not"), required=True,
                readonly=False)

    # Properties
    rolename = Attribute("Role Name")
    statusname = Attribute("Status Name")


class ITeamParticipation(Interface):
    """Team Participation for Users"""
    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("Team"), required=True, readonly=False)
    person = Int(title=_("Owner"), required=True, readonly=False)


class ITeamParticipationSet(Interface):
    """A set for ITeamParticipation objects."""

    def getSubTeams(teamID):
        """Return all subteams for the specified team."""

