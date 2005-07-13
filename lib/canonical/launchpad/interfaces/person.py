# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Person interfaces."""

__metaclass__ = type

__all__ = [
    'IPerson',
    'ITeam',
    'IPersonSet',
    'IEmailAddress',
    'IEmailAddressSet',
    'ITeamMembership',
    'ITeamMembershipSet',
    'ITeamMembershipSubset',
    'ITeamParticipation',
    'IRequestPeopleMerge',
    'IObjectReassignment',
    'ITeamReassignment',
    ]

from zope.schema import Choice, Datetime, Int, Text, TextLine, Password
from zope.interface import Interface, Attribute
from zope.component import getUtility
from zope.i18nmessageid import MessageIDFactory

from canonical.lp.dbschema import (
    TeamSubscriptionPolicy, TeamMembershipStatus, EmailAddressStatus)

_ = MessageIDFactory('launchpad')

def _valid_person_name(name):
    """See IPersonSet.nameIsValidForInsertion()."""
    return getUtility(IPersonSet).nameIsValidForInsertion(name)


class IPerson(Interface):
    """A Person."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Name'), required=True, readonly=True,
            constraint=_valid_person_name,
            description=_(
                "A short unique name, beginning with a lower-case "
                "letter or number, and containing only letters, "
                "numbers, dots, hyphens, or plus signs.")
            )
    displayname = TextLine(
            title=_('Display Name'), required=True, readonly=False,
            description=_("Your name as you would like it displayed "
            "throughout Launchpad. Most people use their full name "
            "here.")
            )
    givenname = TextLine(
            title=_('Given Name'), required=False, readonly=False,
            description=_("Your first name or given name, such as "
                "Mark, or Richard, or Joanna.")
            )
    familyname = TextLine(
            title=_('Family Name'), required=False, readonly=False,
            description=_("Your family name, the name "
                "you acquire from your parents.")
            )
    password = Password(
            title=_('Password'), required=True, readonly=False,
            description=_("The password you will use to access "
                "Launchpad services. ")
            )
    languages = Attribute(_('List of languages known by this person'))

    # this is not a date of birth, it is the date the person record was
    # created in this db
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    # bounty relations
    ownedBounties = Attribute('Bounties issued by this person.')
    reviewerBounties = Attribute('Bounties reviewed by this person.')
    claimedBounties = Attribute('Bounties claimed by this person.')
    subscribedBounties = Attribute('Bounties to which this person subscribes.')

    sshkeys = Attribute(_('List of SSH keys'))

    timezone = TextLine(
        title=_('Timezone Name'), required=False, readonly=False
        )

    # Properties of the Person object.
    karma = Attribute("The cached karma for this person.")
    ubuntite = Attribute("Ubuntite Flag")
    activesignatures = Attribute("Retrieve own Active CoC Signatures.")
    inactivesignatures = Attribute("Retrieve own Inactive CoC Signatures.")
    signedcocs = Attribute("List of Signed Code Of Conduct")
    gpgkeys = Attribute("List of GPGkeys")
    pendinggpgkeys = Attribute("Set of GPG fingerprints pending validation")
    inactivegpgkeys = Attribute("List of inactive GPG keys in LP Context")
    irc = Attribute("IRC")
    reportedbugs = Attribute("All BugTasks reported by this Person.")
    wiki = Attribute("Wiki")
    jabber = Attribute("Jabber")
    archuser = Attribute("Arch user")
    packages = Attribute("A Selection of SourcePackageReleases")
    maintainerships = Attribute("This person's Maintainerships")
    activities = Attribute("Karma")
    memberships = Attribute(("List of TeamMembership objects for Teams this "
                             "Person is a member of. Either active, inactive "
                             "or proposed member."))
    guessedemails = Attribute("List of emails with status NEW. These email "
                              "addresses probably came from a gina or "
                              "POFileImporter run.")
    validatedemails = Attribute("Emails with status VALIDATED")
    unvalidatedemails = Attribute("Emails this person added in Launchpad "
                                  "but are not yet validated.")

    allmembers = Attribute("List of all direct/indirect members of this team. "
                           "If you want a method to check if a given person is "
                           "a member of a team, you should probably look at "
                           "IPerson.inTeam().")
    activemembers = Attribute("List of members with ADMIN or APPROVED status")
    administrators = Attribute("List of members with ADMIN status")
    expiredmembers = Attribute("List of members with EXPIRED status")
    approvedmembers = Attribute("List of members with APPROVED status")
    proposedmembers = Attribute("List of members with PROPOSED status")
    declinedmembers = Attribute("List of members with DECLINED status")
    inactivemembers = Attribute(("List of members with EXPIRED or "
                                 "DEACTIVATED status"))
    deactivatedmembers = Attribute("List of members with DEACTIVATED status")

    teamowner = Choice(title=_('Team Owner'), required=False, readonly=False,
                       vocabulary='ValidTeamOwner')
    teamownerID = Int(title=_("The Team Owner's ID or None"), required=False,
                      readonly=True)
    teamdescription = Text(title=_('Team Description'), required=False,
                           readonly=False)

    preferredemail = TextLine(
            title=_("Preferred Email Address"), description=_(
                "The preferred email address for this person. The one "
                "we'll use to communicate with them."), readonly=False)

    preferredemail_sha1 = TextLine(title=_("SHA-1 Hash of Preferred Email"),
            description=_("The SHA-1 hash of the preferred email address as "
                "a hexadecimal string. This is used as a key by FOAF RDF spec"
                ), readonly=True)

    defaultmembershipperiod = Int(
            title=_('Number of days a subscription lasts'), required=False,
            description=_(
                "The number of days a new subscription lasts "
                "before expiring. You can customize the length "
                "of an individual subscription when approving it. "
                "A value of 0 means subscriptions never expire.")
                )

    defaultrenewalperiod = Int(
            title=_('Number of days a renewed subscription lasts'),
            required=False,
            description=_(
                "The number of days a subscription lasts after "
                "being renewed. You can customize the lengths of "
                "individual renewals. A value of 0 means "
                "renewals last as long as new memberships.")
                )

    defaultexpirationdate = Attribute(
            "The date, according to team's default values, in which a newly "
            "approved membership will expire.")

    defaultrenewedexpirationdate = Attribute(
            "The date, according to team's default values, in "
            "which a just-renewed membership will expire.")

    subscriptionpolicy = Choice(
            title=_('Subscription Policy'),
            required=True, vocabulary='TeamSubscriptionPolicy',
            default=TeamSubscriptionPolicy.MODERATED,
            description=_(
                '"Moderated" means all subscriptions must be '
                'approved. "Open" means any user can join '
                'without approval. "Restricted" means new '
                'members can be added only by a team '
                'administrator.')
            )

    merged = Int(title=_('Merged Into'), required=False, readonly=True,
            description=_(
                'When a Person is merged into another Person, this attribute '
                'is set on the Person referencing the destination Person. If '
                'this is set to None, then this Person has not been merged '
                'into another and is still valid')
                )

    # title is required for the Launchpad Page Layout main template
    title = Attribute('Person Page Title')

    browsername = Attribute(
        'Return a textual name suitable for display in a browser.')

    def isTeam():
        """True if this Person is actually a Team, otherwise False."""

    def assignKarma(action_name):
        """Assign karma for the action named <action_name> to this person."""

    def getKarmaPointsByCategory(category):
        """Return the cached karma of this person for all actions of the given
        category s(he) performed."""

    def inTeam(team):
        """Return True if this person is a member or the owner of <team>.

        This method is meant to be called by objects which implement either
        IPerson or ITeam, and it will return True when you ask if a Person is
        a member of himself (i.e. person1.inTeam(person1)).
        """

    def validateAndEnsurePreferredEmail(self, email):
        """Ensure this person has a preferred email.

        If this person doesn't have a preferred email, <email> will be set as
        this person's preferred one. Otherwise it'll be set as VALIDATED and
        this person will keep its old preferred email. This is why this method
        can't be called with person's preferred email as argument.

        This method is meant to be the only one to change the status of an
        email address, but as we all know the real world is far from ideal and
        we have to deal with this in one more place, which is the case when
        people explicitly want to change their preferred email address. On
        that case, though, all we have to do is assign the new preferred email
        to person.preferredemail.
        """

    def hasMembershipEntryFor(team):
        """Tell if this person is a direct member of the given team."""

    def hasParticipationEntryFor(team):
        """Tell if this person is a direct/indirect member of the given team."""

    def join(team):
        """Join the given team if its subscriptionpolicy is not RESTRICTED.

        Join the given team according to the policies and defaults of that
        team:
        - If the team subscriptionpolicy is OPEN, the user is added as
          an APPROVED member with a NULL TeamMembership.reviewer.
        - If the team subscriptionpolicy is MODERATED, the user is added as
          a PROPOSED member and one of the team's administrators have to
          approve the membership.

        This method returns True if this person was added as a member of
        <team> or False if that wasn't possible.

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

    def addMember(person, status=TeamMembershipStatus.APPROVED, reviewer=None,
                  comment=None):
        """Add person as a member of this team.

        Make sure status is either APPROVED or PROPOSED and add a
        TeamMembership entry for this person with the given status, reviewer,
        and reviewer comment. This method is also responsible for filling
        the TeamParticipation table in case the status is APPROVED.
        """

    def setMembershipStatus(person, status, expires=None, reviewer=None,
                            comment=None):
        """Set the status of the person's membership on this team.

        Also set all other attributes of TeamMembership, which are <comment>,
        <reviewer> and <dateexpires>. This method will ensure that we only
        allow the status transitions specified in the TeamMembership spec.
        It's also responsible for filling/cleaning the TeamParticipation
        table when the transition requires it and setting the expiration
        date, reviewer and reviewercomment.
        """

    def getSubTeams():
        """Return all subteams of this team.

        A subteam is any team that is (either directly or indirectly) a
        member of this team. As an example, let's say we have this hierarchy
        of teams:

        Rosetta Translators
            Rosetta pt Translators
                Rosetta pt_BR Translators

        In this case, both "Rosetta pt Translators" and "Rosetta pt_BR
        Translators" are subteams of the "Rosetta Translators" team, and all
        members of both subteams are considered members of "Rosetta
        Translators".
        """

    def getSuperTeams():
        """Return all superteams of this team.

        A superteam is any team that this team is a member of. For example,
        let's say we have this hierarchy of teams, and we are the
        "Rosetta pt_BR Translators":

        Rosetta Translators
            Rosetta pt Translators
                Rosetta pt_BR Translators

        In this case, we will return both "Rosetta pt Translators" and
        "Rosetta Translators", because we are member of both of them.
        """

    def subscriptionPolicyDesc():
        """Return a long description of this team's subscription policy."""

    def addLanguage(language):
        """Add a language to this person's preferences.

        :language: An object providing ILanguage.

        If the given language is already present, and IntegrityError will be
        raised. This will be fixed soon; here's the discussion on this topic:
        https://launchpad.ubuntu.com/malone/bugs/1317.
        """

    def removeLanguage(language):
        """Remove a language from this person's preferences.

        :language: An object providing ILanguage.

        If the given language is not present, nothing  will happen.
        """


class ITeam(IPerson):
    """ITeam extends IPerson.

    The teamowner should never be None.
    """


class IPersonSet(Interface):
    """The set of Persons."""

    title = Attribute('Title')

    def __getitem__(personid):
        """Return the person with the given id.

        Raise KeyError if there is no such person.
        """

    def nameIsValidForInsertion(name):
        """Return true if <name> is valid and is not yet in the database.

        <name> will be valid if valid_name(name) returns True.
        """

    def createPersonAndEmail(email, name=None, displayname=None, givenname=None,
            familyname=None, password=None, passwordEncrypted=False):
        """Create a new Person and an EmailAddress for that Person.

        Return the newly created Person and EmailAddress if everything went
        fine or a (None, None) tuple otherwise.

        Generate a unique nickname from the email address provided, create a
        Person with that nickname and then create an EmailAddress (with status
        NEW) for the new Person.
        """

    def ensurePerson(email, displayname):
        """Make sure that there is a person in the database with the given
        email address. If necessary, create the person, using the
        displayname given.

        XXX sabdfl 14/06/05 this should be extended to be similar or
        identical to the other person creation argument lists, so we can
        call it and create a full person if needed. Email would remain the
        deciding factor, we would not try and guess if someone existed based
        on the displayname or other arguments.
        """

    def newTeam(**kwargs):
        """Create a new Team with given keyword arguments.

        These keyword arguments will be passed to Person, which is an
        SQLBase class and will do all the checks needed before inserting
        anything in the database. Please refer to the Person implementation
        to see what keyword arguments are allowed.
        """

    def get(personid, default=None):
        """Return the person with the given id.

        Return the default value if there is no such person.
        """

    def getByEmail(email, default=None):
        """Return the person with the given email address.

        Return the default value if there is no such person.
        """

    def getByName(name, default=None):
        """Return the person with the given name, ignoring merged persons.

        Return the default value if there is no such person.
        """

    def getAllTeams(orderBy=None):
        """Return all Teams.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def getAllPersons(orderBy=None):
        """Return all Persons, ignoring the merged ones.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def getAllValidPersons(orderBy=None):
        """Return all valid persons, but not teams.

        A valid person is any person with a preferred email address.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def peopleCount():
        """Return the number of non-merged persons in the database."""

    def teamsCount():
        """Return the number of teams in the database."""

    def findByName(name, orderBy=None):
        """Return all non-merged Persons and Teams with name matching.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def findPersonByName(name, orderBy=None):
        """Return all not-merged Persons with name matching.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def findTeamByName(name, orderBy=None):
        """Return all Teams with name matching.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def getUbuntites(orderBy=None):
        """Return a set of person with valid Ubuntite flag.
        
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def merge(from_person, to_person):
        """Merge a person into another."""


class IEmailAddress(Interface):
    """The object that stores the IPerson's emails."""

    id = Int(title=_('ID'), required=True, readonly=True)
    email = Text(title=_('Email Address'), required=True, readonly=False)
    status = Int(title=_('Email Address Status'), required=True, readonly=False)
    person = Int(title=_('Person'), required=True, readonly=False)
    statusname = Attribute("StatusName")

    def destroySelf():
        """Delete this email from the database."""


class IEmailAddressSet(Interface):
    """The set of EmailAddresses."""

    def new(email, personID, status=EmailAddressStatus.NEW):
        """Create a new EmailAddress with the given email, pointing to person.

        Also make sure that the given status is an item of
        dbschema.EmailAddressStatus.
        """

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

    def getActiveMemberships(teamID, orderBy=None):
        """Return all active TeamMemberships for the given team.

        Active memberships are the ones with status APPROVED or ADMIN.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in TeamMembership._defaultOrder.
        """

    def getInactiveMemberships(teamID, orderBy=None):
        """Return all inactive TeamMemberships for the given team.

        Inactive memberships are the ones with status EXPIRED or DEACTIVATED.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in TeamMembership._defaultOrder.
        """

    def getProposedMemberships(teamID, orderBy=None):
        """Return all proposed TeamMemberships for the given team.

        Proposed memberships are the ones with status PROPOSED.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in TeamMembership._defaultOrder.
        """

    def getByPersonAndTeam(personID, teamID, default=None):
        """Return the TeamMembership object for the given person and team.

        If there's no TeamMembership for this person in this team, return the
        default value.
        """

    def getTeamMembersCount(teamID):
        """Return the number of members this team have.

        This includes active, inactive and proposed members.
        """


class ITeamMembershipSubset(Interface):
    """A Set for TeamMembership objects of a given team."""

    newmember = Choice(title=_('New member'), required=True,
                       vocabulary='ValidTeamMember',
                       description=_("The user or team which is going to be "
                                     "added as the new member of this team."))

    team = Attribute(_("The team for which this subset is for."))

    def getByPersonName(name, default=None):
        """Return the TeamMembership object for the person with the given name.

        If there's no TeamMembership for this person in this team, return the
        default value.
        """

    def getInactiveMemberships():
        """Return all TeamMembership objects for inactive members of this team.

        Inactive members are the ones with membership status of EXPIRED or
        DEACTIVATED.
        """

    def getActiveMemberships():
        """Return all TeamMembership objects for active members of this team.

        Active members are the ones with membership status of APPROVED or ADMIN.
        """

    def getProposedMemberships():
        """Return all TeamMembership objects for proposed members of this team.

        Proposed members are the ones with membership status of PROPOSED.
        """


class ITeamParticipation(Interface):
    """A TeamParticipation.

    A TeamParticipation object represents a person being a member of a team.
    Please note that because a team is also a person in Launchpad, we can
    have a TeamParticipation object representing a team that is a member of
    another team. We can also have an object that represents a person being a
    member of itself.
    """

    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("The team"), required=True, readonly=False)
    person = Int(title=_("The member"), required=True, readonly=False)


class IRequestPeopleMerge(Interface):
    """This schema is used only because we want a very specific vocabulary."""

    dupeaccount = Choice(title=_('Duplicated Account'), required=True,
                         vocabulary='PersonAccountToMerge',
                         description=_("The duplicated account you found in "
                                       "Launchpad"))


class IObjectReassignment(Interface):
    """The schema used by the object reassignment page."""

    owner = Choice(title=_('Owner'), vocabulary='ValidOwner', required=True)


class ITeamReassignment(Interface):
    """The schema used by the team reassignment page."""

    owner = Choice(title=_('Owner'), vocabulary='ValidTeamOwner', required=True)

