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
            description=_("This is your name as your would like it "
                "displayed throughout The Launchpad. Most people "
                "use their full name here.")
            )
    givenname = TextLine(
            title=_('Given Name'), required=False, readonly=False,
            description=_("Your first name or given name, such as "
                "Mark, or Richard, or Joanna.")
            )
    familyname = TextLine(
            title=_('Family Name'), required=False, readonly=False,
            description=_("Your family name or given name, the name "
                "you acquire from your parents.")
            )
    password = Password(
            title=_('Password'), required=True, readonly=False,
            description=_("The password you will use to access "
                "Launchpad services. ")
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

    # XXX: These fields are used only to generate the form to create a
    # new person.
    email = TextLine(title=_('Email Address'), required=True,
            description=_("Please give your email address. You will "
                "log into the Launchpad using your email address and "
                "password. You will need to receive email at this "
                "address to complete your registration. We will never "
                "disclose, share or sell your personal information."))
    password2 = Password(title=_('Confirm Password'), required=True,
            description=_("Enter your password again to make certain "
                "it is correct."))

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
    memberships = Attribute(("List of TeamMembership objects for Teams this "
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

    def assignKarma(karmafield, points=None):
        """Assign <points> worth of karma to this Person."""

    def addLanguage(language):
        """Adds a new language to the list of know languages."""

    def removeLanguage(language):
        """Removed the language from the list of know languages."""

    def inTeam(team_name):
        """Return true if this person is in the named team."""

    def getMembershipByMember(member):
        """Return a TeamMembership object of the given member in this team."""


class ITeam(IPerson):
    """ITeam extends IPerson.
    
    The teamowner should never be None."""


class IPersonSet(Interface):
    """The set of Persons."""

    def __getitem__(personid):
        """Return the person with the given id.

        Raise KeyError if there is no such person.
        """

    def newPerson(*args, **kwargs):
        """Create a new Person with given keyword arguments.
        These keyword arguments will be passed to Person, which is an
        SQLBase class and will do all the checks needed before inserting
        anything in the database. Please refer to the Person implementation
        to see what keyword arguments are allowed."""

    def newTeam(*args, **kwargs):
        """Create a new Team with given keyword arguments.
        These keyword arguments will be passed to Person, which is an
        SQLBase class and will do all the checks needed before inserting
        anything in the database. Please refer to the Person implementation
        to see what keyword arguments are allowed."""

    def get(personid, default=None):
        """Return the person with the given id.

        Return the default value if there is no such person.
        """

    def getByEmail(email, default=None):
        """Return the person with the given email address.

        Return the default value if there is no such person.
        """

    def getByName(name, default=None):
        """Return the person with the given name.

        Return the default value if there is no such person.
        """
    
    def getAll():
        """Return all People in a database"""

    def getContributorsForPOFile(pofile):
        """Return the list of persons that have an active contribution for a
        concrete POFile."""


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


class ITeamMembership(Interface):
    """TeamMembership for Users"""
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

