# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Choice, Datetime, Int, Text, TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.lp import dbschema


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

    # XXX: This field is used only to generate the form to create a new person.
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
    administrators = Attribute(("List of ADMIN members of this Team.")) 
    expiredmembers = Attribute("List of EXPIRED members of this Team.")
    approvedmembers = Attribute("List of APPROVED Members of this Team.")
    proposedmembers = Attribute("List of PROPOSED members of this Team.")
    declinedmembers = Attribute("List of DECLINED members of this Team.")
    deactivatedmembers = Attribute("List of DEACTIVATED members of this Team.")

    subteams = Attribute(("List of subteams of this Team. That is, teams "
                          "which are members of this Team."))
    superteams = Attribute(("List of superteams of this Team. That is, teams "
                            "which this Team is a member of."))

    teamowner = Int(title=_('Team Owner'), required=False, readonly=False)
    teamdescription = Text(title=_('Team Description'), required=False, 
                           readonly=False)

    email = TextLine(
            title=_('Email Address'), required=True,
            description=_("Please give the email address for this Team. "))

    defaultmembershipperiod = TextLine(
            title=_('Period a Subscription Lasts'), required=False, 
            description=_("This is the number of days all "
                "subscriptions will last unless a different value "
                "is provided when the subscription is approved. A value of "
                "0 (zero) means that subscription will never expire."))

    defaultrenewalperiod = TextLine(
            title=_('Period a Subscription Lasts After a Renew'),
            required=False, 
            description=_("This is the number of days all "
                "subscriptions will last after being renewed. After this "
                "period the subscription is expired and must be renewed "
                "again. A value of 0 (zero) means that subscription renewal "
                "periods will be the same as the membership period."))

    subscriptionpolicy = Choice(
            title=_('Subscription Policy'),
            required=True, vocabulary='TeamSubscriptionPolicy',
            default=int(dbschema.TeamSubscriptionPolicy.MODERATED),
            description=_('How new subscriptions should be handled for this '
                          'team. "Moderated" means that all subscriptions must '
                          'be approved, "Open" means that any user can join '
                          'whitout approval and "Restricted" means that new '
                          'members can only be added by one of the '
                          'administrators of the team.'))

    def browsername():
        """Return a textual name suitable for display in a browser."""

    def assignKarma(karmafield, points=None):
        """Assign <points> worth of karma to this Person."""

    def addLanguage(language):
        """Add a new language to the list of know languages."""

    def removeLanguage(language):
        """Removed the language from the list of know languages."""

    def inTeam(team):
        """Return true if this person is in the given team."""

    def getMembershipsByStatus(status):
        """Return all TeamMembership rows with the given status for this team"""

    def hasMembershipEntryFor(team):
        """Tell if this person is a direct member of the given team."""

    def joinTeam(team):
        """Join the given team if its subscriptionpolicy is not RESTRICTED.

        Join the given team according to the policies and defaults of that
        team:
        - If the team subscriptionpolicy is OPEN, the user is added as
          an APPROVED member with a NULL TeamMembership.reviewer.
        - If the team subscriptionpolicy is MODERATED, the user is added as
          a PROPOSED member and one of the team's administrators have to
          approve the membership.
        """

    def unjoinTeam(team):
        """Unjoin the given team.

        If there's a membership entry for this person on the given team and
        its status is either APPROVED or ADMIN, we change the status to
        DEACTIVATED and remove the relevant entries in teamparticipation.
        """

    def hasMembershipEntryFor(team):
        """Tell if this person is a direct member of the given team."""

    def joinTeam(team):
        """Join the given team if its subscriptionpolicy is not RESTRICTED.

        Join the given team according to the policies and defaults of that
        team:
        - If the team subscriptionpolicy is OPEN, the user is added as
          an APPROVED member with a NULL TeamMembership.reviewer.
        - If the team subscriptionpolicy is MODERATED, the user is added as
          a PROPOSED member and one of the team's administrators have to
          approve the membership.
        """

    def unjoinTeam(team):
        """Unjoin the given team.

        If there's a membership entry for this person on the given team and
        its status is either APPROVED or ADMIN, we change the status to
        DEACTIVATED and remove the relevant entries in teamparticipation.
        """


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

    id = Int(title=_('ID'), required=True, readonly=True)
    email = Text(title=_('Email Address'), required=True, readonly=False)
    status = Int(title=_('Email Address Status'), required=True, readonly=False)
    person = Int(title=_('Person'), required=True, readonly=False)
    statusname = Attribute("StatusName")


class IEmailAddressSet(Interface):
    """The set of EmailAddresses."""

    def __getitem__(emailid):
        """Return the email address with the given id.

        Raise KeyError if there is no such email address.
        """

    def get(emailid, default=None):
        """Return the email address with the given id.

        Return the default value if there is no such email address.
        """

    def getByPerson(personid):
        """Return all email addresses for the given person."""

    def getByEmail(email, default=None):
        """Return the EmailAddress object for the given email.

        Return the default value if there is no such email address.
        """


class ITeamMembership(Interface):
    """TeamMembership for Users"""
    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("Team"), required=True, readonly=False)
    person = Int(title=_("Owner"), required=True, readonly=False)
    reviewer = Int(title=_("Reviewer"), required=False, readonly=False)

    datejoined = Text(title=_("Date Joined"), required=True, readonly=True)
    dateexpires = Text(title=_("Date Expires"), required=False, readonly=False)
    reviewercomment = Text(title=_("Reviewer Comment"), required=False, 
                           readonly=False)
    status= Int(title=_("If Membership was approved or not"), required=True,
                readonly=False)

    # Properties
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

    def getSuperTeams(teamID):
        """Return all superteams for the specified team."""

    def getAllMembers(team):
        """Return a list of (direct / indirect) members for the given team."""


class IRequestPeopleMerge(Interface):
    """This schema is used only because we want the PersonVocabulary."""

    dupeaccount = Choice(title=_('Duplicated Account'), required=True, 
                         vocabulary='Person',
                         description=_("The duplicated account you found in "
                                       "Launchpad"))

