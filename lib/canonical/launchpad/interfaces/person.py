# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Choice, Datetime, Int, Text, TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.lp.dbschema import TeamSubscriptionPolicy, TeamMembershipStatus


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
    ubuntite = Attribute("Ubuntite Flag")
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

    activemembers = Attribute("List of members with ADMIN or APPROVED status")
    administrators = Attribute("List of members with ADMIN status")
    expiredmembers = Attribute("List of members with EXPIRED status")
    approvedmembers = Attribute("List of members with APPROVED status")
    proposedmembers = Attribute("List of members with PROPOSED status")
    declinedmembers = Attribute("List of members with DECLINED status")
    inactivemembers = Attribute(("List of members with EXPIRED or "
                                 "DEACTIVATED status"))
    deactivatedmembers = Attribute("List of members with DEACTIVATED status")

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

    defaultmembershipperiod = Int(
            title=_('Number of days a subscription lasts'), required=False, 
            description=_("This is the number of days all "
                "subscriptions will last unless a different value is provided "
                "when the subscription is approved. After this " "period the "
                "subscription is expired and must be renewed. A value of 0 "
                "(zero) means that subscription will never expire."))

    defaultrenewalperiod = Int(
            title=_('Number of days a renewed subscription lasts'),
            required=False, 
            description=_("This is the number of days all "
                "subscriptions will last after being renewed. After this "
                "period the subscription is expired and must be renewed "
                "again. A value of 0 (zero) means that subscription renewal "
                "periods will be the same as the membership period."))

    subscriptionpolicy = Choice(
            title=_('Subscription Policy'),
            required=True, vocabulary='TeamSubscriptionPolicy',
            default=TeamSubscriptionPolicy.MODERATED,
            description=_('How new subscriptions should be handled for this '
                          'team. "Moderated" means that all subscriptions must '
                          'be approved, "Open" means that any user can join '
                          'whitout approval and "Restricted" means that new '
                          'members can only be added by one of the '
                          'administrators of the team.'))

    # title is required for the Launchpad Page Layout main template
    title = Attribute('Person Page Title')

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

    def join(team):
        """Join the given team if its subscriptionpolicy is not RESTRICTED.

        Join the given team according to the policies and defaults of that
        team:
        - If the team subscriptionpolicy is OPEN, the user is added as
          an APPROVED member with a NULL TeamMembership.reviewer.
        - If the team subscriptionpolicy is MODERATED, the user is added as
          a PROPOSED member and one of the team's administrators have to
          approve the membership.

        Teams cannot call this method because they're not allowed to
        login and thus can't "join" another team. Instead, they're added 
        as a member (using the addMember() method) by a team administrator.
        """

    def leave(team):
        """Leave the given team.

        If there's a membership entry for this person on the given team and
        its status is either APPROVED or ADMIN, we change the status to
        DEACTIVATED and remove the relevant entries in teamparticipation.

        Teams cannot call this method because they're not allowed to
        login and thus can't "leave" another team. Instead, they have their
        subscription deactivated (using the setMembershipStatus() method) by
        a team administrator.
        """

    def addMember(person, status=TeamMembershipStatus.APPROVED, expires=None,
                  reviewer=None, comment=None):
        """Add person as a member of this team.

        Make sure status is either APPROVED or PROPOSED and add a
        TeamMembership entry for this person with the given status, reviewer,
        expiration date and reviewer comment. This method is also responsible
        for filling the TeamParticipation table in case the status is APPROVED.
        """

    def setMembershipStatus(person, status, expires=None, reviewer=None,
                            comment=None):
        """Set the status of the person's membership on this team.

        This method will ensure that we only allow the status transitions
        specified in the TeamMembership spec. It's also responsible for
        filling/cleaning the TeamParticipation table when the transition
        requires it and setting the expiration date, reviewer and
        reviewercomment.
        """


class ITeam(IPerson):
    """ITeam extends IPerson.
    
    The teamowner should never be None."""


class IPersonSet(Interface):
    """The set of Persons."""

    title = Attribute('Title')

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

    def isUbuntite(user):
        """Return True if User has a valid Signed current version CoC."""

    def getUbuntites():
        """Return a set of person with valid Ubuntite flag."""

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
    person = Int(title=_("Member"), required=True, readonly=False)
    reviewer = Int(title=_("Reviewer"), required=False, readonly=False)

    datejoined = Text(title=_("Date Joined"), required=True, readonly=True)
    dateexpires = Text(title=_("Date Expires"), required=False, readonly=False)
    reviewercomment = Text(title=_("Reviewer Comment"), required=False, 
                           readonly=False)
    status= Int(title=_("If Membership was approved or not"), required=True,
                readonly=False)

    # Properties
    statusname = Attribute("Status Name")

    def isExpired():
        """Return True if this membership's status is EXPIRED."""


class ITeamMembershipSet(Interface):
    """A Set for TeamMembership objects."""

    def getByPersonAndTeam(personID, teamID, default=None):
        """Return the TeamMembership object for the given person and team.

        If there's no TeamMembership for this person in this team, return the
        default value.
        """


class ITeamMembershipSubset(Interface):
    """A Set for TeamMembership objects of a given team."""

    newmember = Choice(title=_('New member'), required=True, 
                       vocabulary='Person',
                       description=_("The user or team which is going to be "
                                     "added as the new member of this team."))

    team = Attribute(_("The team for which this subset is for."))

    def getByPersonName(name, default=None):
        """Return the TeamMembership object for the person with the given name.

        If there's no TeamMembership for this person in this team, return the
        default value.
        """


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

