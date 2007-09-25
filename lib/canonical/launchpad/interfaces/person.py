# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Person interfaces."""

__metaclass__ = type

__all__ = [
    'AccountStatus',
    'IAdminRequestPeopleMerge',
    'INewPerson',
    'IObjectReassignment',
    'IPersonChangePassword',
    'IPersonClaim',
    'IPersonSet',
    'IPerson',
    'IRequestPeopleMerge',
    'ITeamContactAddressForm',
    'ITeamCreation',
    'ITeamReassignment',
    'ITeam',
    'JoinNotAllowed',
    'PersonCreationRationale',
    'TeamMembershipRenewalPolicy',
    'TeamMembershipStatus',
    'TeamSubscriptionPolicy',
    ]


from zope.formlib.form import NoInputData
from zope.schema import Bool, Choice, Datetime, Int, Text, TextLine
from zope.interface import Attribute, Interface
from zope.interface.exceptions import Invalid
from zope.interface.interface import invariant
from zope.component import getUtility

from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem
from canonical.launchpad.fields import (
    BlacklistableContentNameField, IconImageUpload, LogoImageUpload,
    MugshotImageUpload, PasswordField, StrippedTextLine)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces.mentoringoffer import (
    IHasMentoringOffers)
from canonical.launchpad.interfaces.specificationtarget import (
    IHasSpecifications)
from canonical.launchpad.interfaces.launchpad import (
    IHasLogo, IHasMugshot, IHasIcon)
from canonical.launchpad.interfaces.questioncollection import (
    IQuestionCollection, QUESTION_STATUS_DEFAULT_SEARCH)
from canonical.launchpad.interfaces.validation import (
    validate_new_team_email, validate_new_person_email)


class AccountStatus(DBEnumeratedType):
    """The status of a Launchpad account."""

    NOACCOUNT = DBItem(10, """
        No Launchpad account

        There's no Launchpad account for this Person record.
        """)

    ACTIVE = DBItem(20, """
        Active Launchpad account

        There's an active Launchpad account associated with this Person.
        """)

    DEACTIVATED = DBItem(30, """
        Deactivated Launchpad account

        The account associated with this Person has been deactivated by the
        Person himself.
        """)

    SUSPENDED = DBItem(40, """
        Suspended Launchpad account

        The account associated with this Person has been suspended by a
        Launchpad admin.
        """)


class PersonCreationRationale(DBEnumeratedType):
    """The rationale for the creation of a given person.

    Launchpad automatically creates user accounts under certain
    circumstances. The owners of these accounts may discover Launchpad
    at a later date and wonder why Launchpad knows about them, so we
    need to make it clear why a certain account was automatically created.
    """

    UNKNOWN = DBItem(1, """
        Unknown

        The reason for the creation of this person is unknown.
        """)

    BUGIMPORT = DBItem(2, """
        Existing user in another bugtracker from which we imported bugs.

        A bugzilla import or sf.net import, for instance. The bugtracker from
        which we were importing should be described in
        Person.creation_comment.
        """)

    SOURCEPACKAGEIMPORT = DBItem(3, """
        This person was mentioned in a source package we imported.

        When gina imports source packages, it has to create Person entries for
        the email addresses that are listed as maintainer and/or uploader of
        the package, in case they don't exist in Launchpad.
        """)

    POFILEIMPORT = DBItem(4, """
        This person was mentioned in a POFile imported into Rosetta.

        When importing POFiles into Rosetta, we need to give credit for the
        translations on that POFile to its last translator, which may not
        exist in Launchpad, so we'd need to create it.
        """)

    KEYRINGTRUSTANALYZER = DBItem(5, """
        Created by the keyring trust analyzer.

        The keyring trust analyzer is responsible for scanning GPG keys
        belonging to the strongly connected set and assign all email addresses
        registered on those keys to the people representing their owners in
        Launchpad. If any of these people doesn't exist, it creates them.
        """)

    FROMEMAILMESSAGE = DBItem(6, """
        Created when parsing an email message.

        Sometimes we parse email messages and want to associate them with the
        sender, which may not have a Launchpad account. In that case we need
        to create a Person entry to associate with the email.
        """)

    SOURCEPACKAGEUPLOAD = DBItem(7, """
        This person was mentioned in a source package uploaded.

        Some uploaded packages may be uploaded with a maintainer that is not
        registered in Launchpad, and in these cases, soyuz may decide to
        create the new Person instead of complaining.
        """)

    OWNER_CREATED_LAUNCHPAD = DBItem(8, """
        Created by the owner himself, coming from Launchpad.

        Somebody was navigating through Launchpad and at some point decided to
        create an account.
        """)

    OWNER_CREATED_SHIPIT = DBItem(9, """
        Created by the owner himself, coming from Shipit.

        Somebody went to one of the shipit sites to request Ubuntu CDs and was
        directed to Launchpad to create an account.
        """)

    OWNER_CREATED_UBUNTU_WIKI = DBItem(10, """
        Created by the owner himself, coming from the Ubuntu wiki.

        Somebody went to the Ubuntu wiki and was directed to Launchpad to
        create an account.
        """)

    USER_CREATED = DBItem(11, """
        Created by a user to represent a person which does not uses Launchpad.

        A user wanted to reference a person which is not a Launchpad user, so
        he created this "placeholder" profile.
        """)

    OWNER_CREATED_UBUNTU_SHOP = DBItem(12, """
        Created by the owner himself, coming from the Ubuntu Shop.

        Somebody went to the Ubuntu Shop and was directed to Launchpad to
        create an account.
        """)

    OWNER_CREATED_UNKNOWN_TRUSTROOT = DBItem(13, """
        Created by the owner himself, coming from unknown OpenID consumer.

        Somebody went to an OpenID consumer we don't know about and was
        directed to Launchpad to create an account.
        """)

    OWNER_SUBMITTED_HARDWARE_TEST = DBItem(14, """
        Created by a submission to the hardware database.

        Somebody without a Launchpad account made a submission to the
        hardware database.
        """)

class TeamMembershipRenewalPolicy(DBEnumeratedType):
    """TeamMembership Renewal Policy.

    How Team Memberships can be renewed on a given team.
    """

    NONE = DBItem(10, """
        invite them to apply for renewal

        Memberships can be renewed only by team administrators or by going
        through the normal workflow for joining the team.
        """)

    ONDEMAND = DBItem(20, """
        invite them to renew their own membership

        Memberships can be renewed by the members themselves a few days before
        it expires. After it expires the member has to go through the normal
        workflow for joining the team.
        """)

    AUTOMATIC = DBItem(30, """
        renew their membership automatically, also notifying the admins

        Memberships are automatically renewed when they expire and a note is
        sent to the member and to team admins.
        """)


class TeamMembershipStatus(DBEnumeratedType):
    """TeamMembership Status

    According to the policies specified by each team, the membership status of
    a given member can be one of multiple different statuses. More information
    can be found in the TeamMembership spec.
    """

    PROPOSED = DBItem(1, """
        Proposed

        You are a proposed member of this team. To become an active member
        your subscription has to be approved by one of the team's
        administrators.
        """)

    APPROVED = DBItem(2, """
        Approved

        You are an active member of this team.
        """)

    ADMIN = DBItem(3, """
        Administrator

        You are an administrator of this team.
        """)

    DEACTIVATED = DBItem(4, """
        Deactivated

        Your subscription to this team has been deactivated.
        """)

    EXPIRED = DBItem(5, """
        Expired

        Your subscription to this team is expired.
        """)

    DECLINED = DBItem(6, """
        Declined

        Your proposed subscription to this team has been declined.
        """)

    INVITED = DBItem(7, """
        Invited

        You have been invited as a member of this team. In order to become an
        actual member, you have to accept the invitation.
        """)

    INVITATION_DECLINED = DBItem(8, """
        Invitation declined

        You have been invited as a member of this team but the invitation has
        been declined.
        """)


class TeamSubscriptionPolicy(DBEnumeratedType):
    """Team Subscription Policies

    The policies that apply to a team and specify how new subscriptions must
    be handled. More information can be found in the TeamMembershipPolicies
    spec.
    """

    MODERATED = DBItem(1, """
        Moderated Team

        All subscriptions for this team are subjected to approval by one of
        the team's administrators.
        """)

    OPEN = DBItem(2, """
        Open Team

        Any user can join and no approval is required.
        """)

    RESTRICTED = DBItem(3, """
        Restricted Team

        New members can only be added by one of the team's administrators.
        """)


class PersonNameField(BlacklistableContentNameField):
    """A Person's name, which is unique."""

    errormessage = _("%s is already in use by another person or team.")

    @property
    def _content_iface(self):
        """Return the interface this field belongs to."""
        return IPerson

    def _getByName(self, name):
        """Return a Person by looking up his name."""
        return getUtility(IPersonSet).getByName(name, ignore_merged=False)


class IPersonChangePassword(Interface):
    """The schema used by Person +changepassword form."""

    currentpassword = PasswordField(
            title=_('Current password'), required=True, readonly=False,
            description=_("The password you use to log into Launchpad.")
            )

    password = PasswordField(
            title=_('New Password'), required=True, readonly=False,
            description=_("Enter the same password in each field.")
            )


class IPersonClaim(Interface):
    """The schema used by IPerson's +claim form."""

    emailaddress = TextLine(title=_('Email address'), required=True)


class INewPerson(Interface):
    """The schema used by IPersonSet's +newperson form."""

    emailaddress = StrippedTextLine(
        title=_('Email address'), required=True,
        constraint=validate_new_person_email)
    displayname = StrippedTextLine(title=_('Display name'), required=True)
    creation_comment = Text(
        title=_('Creation reason'), required=True,
        description=_("The reason why you're creating this profile."))


class IPerson(IHasSpecifications, IHasMentoringOffers, IQuestionCollection,
              IHasLogo, IHasMugshot, IHasIcon):
    """A Person."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    name = PersonNameField(
            title=_('Name'), required=True, readonly=False,
            constraint=name_validator,
            description=_(
                "A short unique name, beginning with a lower-case "
                "letter or number, and containing only letters, "
                "numbers, dots, hyphens, or plus signs.")
            )
    displayname = StrippedTextLine(
            title=_('Display Name'), required=True, readonly=False,
            description=_("Your name as you would like it displayed "
            "throughout Launchpad. Most people use their full name "
            "here.")
            )
    password = PasswordField(
            title=_('Password'), required=True, readonly=False)
    karma = Int(
            title=_('Karma'), readonly=False,
            description=_('The cached total karma for this person.')
            )
    homepage_content = Text(
        title=_("Homepage Content"), required=False,
        description=_(
            "The content of your home page. Edit this and it will be "
            "displayed for all the world to see."))
    # NB at this stage we do not allow individual people to have their own
    # icon, only teams get that. People can however have a logo and mugshot
    # The icon is only used for teams; that's why we use /@@/team as the
    # default image resource.
    icon = IconImageUpload(
        title=_("Icon"), required=False,
        default_image_resource='/@@/team',
        description=_(
            "A small image of exactly 14x14 pixels and at most 5kb in size, "
            "that can be used to identify this team. The icon will be "
            "displayed whenever the team name is listed - for example "
            "in listings of bugs or on a person's membership table."))
    logo = LogoImageUpload(
        title=_("Logo"), required=False,
        default_image_resource='/@@/person-logo',
        description=_(
            "An image of exactly 64x64 pixels that will be displayed in "
            "the heading of all pages related to you. Traditionally this "
            "is a logo, a small picture or a personal mascot. It should be "
            "no bigger than 50kb in size."))
    mugshot = MugshotImageUpload(
        title=_("Mugshot"), required=False,
        default_image_resource='/@@/person-mugshot',
        description=_(
            "A large image of exactly 192x192 pixels, that will be displayed "
            "on your home page in Launchpad. Traditionally this is a great "
            "big picture of your grinning face. Make the most of it! It "
            "should be no bigger than 100kb in size. "))
    addressline1 = TextLine(
            title=_('Address'), required=True, readonly=False,
            description=_('Your address (Line 1)')
            )
    addressline2 = TextLine(
            title=_('Address'), required=False, readonly=False,
            description=_('Your address (Line 2)')
            )
    city = TextLine(
            title=_('City'), required=True, readonly=False,
            description=_('The City/Town/Village/etc to where the CDs should '
                          'be shipped.')
            )
    province = TextLine(
            title=_('Province'), required=True, readonly=False,
            description=_('The State/Province/etc to where the CDs should '
                          'be shipped.')
            )
    country = Choice(
            title=_('Country'), required=True, readonly=False,
            vocabulary='CountryName',
            description=_('The Country to where the CDs should be shipped.')
            )
    postcode = TextLine(
            title=_('Postcode'), required=True, readonly=False,
            description=_('The Postcode to where the CDs should be shipped.')
            )
    phone = TextLine(
            title=_('Phone'), required=True, readonly=False,
            description=_('[(+CountryCode) number] e.g. (+55) 16 33619445')
            )
    organization = TextLine(
            title=_('Organization'), required=False, readonly=False,
            description=_('The Organization requesting the CDs')
            )
    languages = Attribute(_('List of languages known by this person'))
    translatable_languages = Attribute(
        _('Languages this person knows, apart from English'))

    hide_email_addresses = Bool(
        title=_("Hide my email addresses from other Launchpad users"),
        required=False, default=False)
    # this is not a date of birth, it is the date the person record was
    # created in this db
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    creation_rationale = Choice(
        title=_("Rationale for this entry's creation"), required=False,
        readonly=False, values=PersonCreationRationale.items)
    creation_comment = TextLine(
        title=_("Comment for this entry's creation"),
        description=_(
            "This comment may be displayed verbatim in a web page, so it "
            "has to follow some structural constraints, that is, it must "
            "be of the form: 'when %(action_details)s' (e.g 'when the "
            "foo package was imported into Ubuntu Breezy'). The only "
            "exception to this is when we allow users to create Launchpad "
            "profiles through the /people/+newperson page."),
        required=False, readonly=False)
    # XXX Guilherme Salgado 2006-11-10:
    # We can't use a Choice field here because we don't have a vocabulary
    # which contains valid people but not teams, and we don't really need one
    # appart from here.
    registrant = Attribute('The user who created this profile.')
    # bounty relations
    ownedBounties = Attribute('Bounties issued by this person.')
    reviewerBounties = Attribute('Bounties reviewed by this person.')
    claimedBounties = Attribute('Bounties claimed by this person.')
    subscribedBounties = Attribute(
        'Bounties to which this person subscribes.')

    sshkeys = Attribute(_('List of SSH keys'))

    timezone = Choice(
        title=_('Timezone'), required=True, readonly=False,
        description=_('The timezone of where you live.'),
        vocabulary='TimezoneName')

    openid_identifier = TextLine(
            title=_("Key used to generate opaque OpenID identities."),
            readonly=True, required=False,
            )

    account_status = Choice(
        title=_("The status of this person's account"), required=False,
        readonly=False, vocabulary=AccountStatus)

    account_status_comment = Text(
        title=_("Why are you deactivating your account?"), required=False,
        readonly=False)

    # Properties of the Person object.
    karma_category_caches = Attribute(
        'The caches of karma scores, by karma category.')
    is_valid_person = Bool(
        title=_("This is an active user and not a team."), readonly=True)
    is_valid_person_or_team = Bool(
        title=_("This is an active user or a team."), readonly=True)
    is_openid_enabled = Bool(
        title=_("This user can use Launchpad as an OpenID provider."),
        readonly=True)
    is_ubuntero = Bool(title=_("Ubuntero Flag"), readonly=True)
    activesignatures = Attribute("Retrieve own Active CoC Signatures.")
    inactivesignatures = Attribute("Retrieve own Inactive CoC Signatures.")
    signedcocs = Attribute("List of Signed Code Of Conduct")
    gpgkeys = Attribute("List of valid OpenPGP keys ordered by ID")
    pendinggpgkeys = Attribute("Set of fingerprints pending confirmation")
    inactivegpgkeys = Attribute(
        "List of inactive OpenPGP keys in LP Context, ordered by ID")
    ubuntuwiki = Attribute("The Ubuntu WikiName of this Person.")
    otherwikis = Attribute(
        "All WikiNames of this Person that are not the Ubuntu one.")
    allwikis = Attribute("All WikiNames of this Person.")
    ircnicknames = Attribute("List of IRC nicknames of this Person.")
    jabberids = Attribute("List of Jabber IDs of this Person.")
    branches = Attribute(
        "All branches related to this persion. They might be registered, "
        "authored or subscribed by this person.")
    authored_branches = Attribute("The branches whose author is this person.")
    registered_branches = Attribute(
        "The branches whose owner is this person and which either have no"
        "author or an author different from this person.")
    subscribed_branches = Attribute(
        "Branches to which this person " "subscribes.")
    myactivememberships = Attribute(
        "List of TeamMembership objects for Teams this Person is an active "
        "member of.")
    open_membership_invitations = Attribute(
        "All TeamMemberships which represent an invitation (to join a team) "
        "sent to this person.")
    teams_participated_in = Attribute(
        "Iterable of all Teams that this person is active in, recursive")
    teams_indirectly_participated_in = Attribute(
        "Iterable of all the teams in which this person is and indirect "
        "member.")
    teams_with_icons = Attribute(
        "Iterable of all Teams that this person is active in that have "
        "icons")
    guessedemails = Attribute(
        "List of emails with status NEW. These email addresses probably "
        "came from a gina or POFileImporter run.")
    validatedemails = Attribute("Emails with status VALIDATED")
    unvalidatedemails = Attribute(
        "Emails this person added in Launchpad but are not yet validated.")
    allmembers = Attribute(
        "List of all direct and indirect people and teams who, one way or "
        "another, are a part of this team. If you want a method to check if "
        "a given person is a member of a team, you should probably look at "
        "IPerson.inTeam().")
    activemembers = Attribute("List of members with ADMIN or APPROVED status")
    active_member_count = Attribute(
        "The number of real people who are members of this team.")
    all_member_count = Attribute(
        "The total number of real people who are members of this team, "
        "including subteams.")
    adminmembers = Attribute("List of members with ADMIN status")
    expiredmembers = Attribute("List of members with EXPIRED status")
    approvedmembers = Attribute("List of members with APPROVED status")
    proposedmembers = Attribute("List of members with PROPOSED status")
    inactivemembers = Attribute(
        "List of members with EXPIRED or DEACTIVATED status")
    deactivatedmembers = Attribute("List of members with DEACTIVATED status")
    invited_members = Attribute("List of members with INVITED status")
    pendingmembers = Attribute(
        "List of members with INVITED or PROPOSED status")
    specifications = Attribute(
        "Any specifications related to this person, either because the are "
        "a subscriber, or an assignee, or a drafter, or the creator. "
        "Sorted newest-first.")
    approver_specs = Attribute(
        "Specifications this person is supposed to approve in due "
        "course, newest first.")
    assigned_specs = Attribute(
        "Specifications assigned to this person, sorted newest first.")
    assigned_specs_in_progress = Attribute(
        "Specifications assigned to this person whose implementation is "
        "started but not yet completed, sorted newest first.")
    drafted_specs = Attribute(
        "Specifications being drafted by this person, sorted newest first.")
    created_specs = Attribute(
        "Specifications created by this person, sorted newest first.")
    feedback_specs = Attribute(
        "Specifications on which this person has been asked to provide "
        "feedback, sorted newest first.")
    subscribed_specs = Attribute(
        "Specifications this person has subscribed to, sorted newest first.")
    team_mentorships = Attribute(
        "All the offers of mentoring which are relevant to this team.")
    teamowner = Choice(title=_('Team Owner'), required=False, readonly=False,
                       vocabulary='ValidTeamOwner')
    teamownerID = Int(title=_("The Team Owner's ID or None"), required=False,
                      readonly=True)
    teamdescription = Text(
        title=_('Team Description'), required=False, readonly=False,
        description=_('Use plain text; URLs will be linkified'))

    preferredemail = TextLine(
        title=_("Preferred Email Address"),
        description=_("The preferred email address for this person. The one "
                      "we'll use to communicate with them."),
        readonly=True)

    preferredemail_sha1 = TextLine(
        title=_("SHA-1 Hash of Preferred Email"),
        description=_("The SHA-1 hash of the preferred email address and "
                      "a mailto: prefix as a hexadecimal string. This is "
                      "used as a key by FOAF RDF spec"),
        readonly=True)

    defaultmembershipperiod = Int(
        title=_('Subscription period'), required=False,
        description=_(
            "Number of days a new subscription lasts before expiring. "
            "You can customize the length of an individual subscription when "
            "approving it. Leave this empty or set to 0 for subscriptions to "
            "never expire."))

    defaultrenewalperiod = Int(
        title=_('Renewal period'),
        required=False,
        description=_(
            "Number of days a subscription lasts after being renewed. "
            "You can customize the lengths of individual renewals, but this "
            "is what's used for auto-renewed and user-renewed memberships."))

    defaultexpirationdate = Attribute(
        "The date, according to team's default values, in which a newly "
        "approved membership will expire.")

    defaultrenewedexpirationdate = Attribute(
        "The date, according to team's default values, in "
        "which a just-renewed membership will expire.")

    subscriptionpolicy = Choice(
        title=_('Subscription Policy'),
        required=True, vocabulary=TeamSubscriptionPolicy,
        default=TeamSubscriptionPolicy.MODERATED,
        description=_(
            "'Moderated' means all subscriptions must be approved. 'Open' "
            "means any user can join without approval. 'Restricted' means "
            "new members can be added only by a team administrator."))

    renewal_policy = Choice(
        title=_("When someone's membership is about to expire, Launchpad "
                "should notify them and"),
        required=True, vocabulary=TeamMembershipRenewalPolicy,
        default=TeamMembershipRenewalPolicy.NONE)

    merged = Int(
        title=_('Merged Into'), required=False, readonly=True,
        description=_(
            "When a Person is merged into another Person, this attribute "
            "is set on the Person referencing the destination Person. If "
            "this is set to None, then this Person has not been merged "
            "into another and is still valid"))

    translation_history = Attribute(
        "The set of POFileTranslator objects that represent work done "
        "by this translator.")

    translation_groups = Attribute(
        "The set of TranslationGroup objects this person is a member of.")

    # title is required for the Launchpad Page Layout main template
    title = Attribute('Person Page Title')

    is_trusted_on_shipit = Bool(
        title=_('Is this a trusted person on shipit?'))
    unique_displayname = TextLine(
        title=_('Return a string of the form $displayname ($name).'))
    browsername = Attribute(
        'Return a textual name suitable for display in a browser.')

    archive = Attribute(
        "The Archive owned by this person, his PPA.")

    entitlements = Attribute("List of Entitlements for this person or team.")

    @invariant
    def personCannotHaveIcon(person):
        """Only Persons can have icons."""
        # XXX Guilherme Salgado 2007-05-28:
        # This invariant is busted! The person parameter provided to this
        # method will always be an instance of zope.formlib.form.FormData
        # containing only the values of the fields included in the POSTed
        # form. IOW, person.inTeam() will raise a NoInputData just like
        # person.teamowner would as it's not present in most of the
        # person-related forms.
        if person.icon is not None and not person.isTeam():
            raise Invalid('Only teams can have an icon.')

    @invariant
    def defaultRenewalPeriodIsRequiredForSomeTeams(person):
        """Teams may specify a default renewal period.

        The team renewal period cannot be less than 1 day, and when the
        renewal policy is is 'On Demand' or 'Automatic', it cannot be None.
        """
        # The person arg is a zope.formlib.form.FormData instance.
        # Instead of checking 'not person.isTeam()' or 'person.teamowner',
        # we check for a field in the schema to identify this as a team.
        try:
            renewal_policy = person.renewal_policy
        except NoInputData:
            # This is not a team.
            return

        renewal_period = person.defaultrenewalperiod
        automatic, ondemand = [TeamMembershipRenewalPolicy.AUTOMATIC,
                               TeamMembershipRenewalPolicy.ONDEMAND]
        cannot_be_none = renewal_policy in [automatic, ondemand]
        if ((renewal_period is None and cannot_be_none)
            or (renewal_period is not None and renewal_period <= 0)):
            raise Invalid(
                'You must specify a default renewal period greater than 0.')

    def getActiveMemberships():
        """Return all active TeamMembership objects of this team.

        Active TeamMemberships are the ones with the ADMIN or APPROVED status.

        The results are ordered using Person.sortingColumns.
        """

    def getInvitedMemberships():
        """Return all TeamMemberships of this team with the INVITED status.

        The results are ordered using Person.sortingColumns.
        """

    def getInactiveMemberships():
        """Return all inactive TeamMemberships of this team.

        Inactive memberships are the ones with status EXPIRED or DEACTIVATED.

        The results are ordered using Person.sortingColumns.
        """

    def getProposedMemberships():
        """Return all TeamMemberships of this team with the PROPOSED status.

        The results are ordered using Person.sortingColumns.
        """

    def getBugContactPackages():
        """Return a list of packages for which this person is a bug contact.

        Returns a list of IDistributionSourcePackage's, ordered alphabetically
        (A to Z) by name.
        """

    def getBugContactOpenBugCounts(user):
        """Return open bug counts for this bug contact's packages.

            :user: The user doing the search. Private bugs that this
                   user doesn't have access to won't be included in the
                   count.

        Returns a list of dictionaries, where each dict contains:

            'package': The package the bugs are open on.
            'open': The number of open bugs.
            'open_critical': The number of open critical bugs.
            'open_unassigned': The number of open unassigned bugs.
            'open_inprogress': The number of open bugs that ar In Progress.
        """

    def setContactAddress(email):
        """Set the given email address as this team's contact address.

        This method must be used only for teams.
        """

    def setPreferredEmail(email):
        """Set the given email address as this person's preferred one.

        This method must be used only for people, not teams.
        """

    def getBranch(product_name, branch_name):
        """The branch associated to this person and product with this name.

        The product_name may be None.
        """

    def findPathToTeam(team):
        """Return the teams that cause this person to be a participant of the
        given team.

        If there is more than one path leading this person to the given team,
        only the one with the oldest teams is returned.

        This method must not be called if this person is not an indirect
        member of the given team.
        """

    def isTeam():
        """True if this Person is actually a Team, otherwise False."""

    def getProjectsAndCategoriesContributedTo(limit=10):
        """Return a list of dicts with projects and the contributions made
        by this person on that project.

        The list is limited to the :limit: projects this person is most
        active.

        The dictionaries containing the following keys:
            - project:    The project, which is either an IProduct or an
                          IDistribution.
            - categories: A dictionary mapping KarmaCategory titles to
                          the icons which represent that category.
        """

    def getOwnedOrDrivenPillars():
        """Return Distribution, Project Groups and Projects that this person
        owns or drives.
        """

    def assignKarma(action_name, product=None, distribution=None,
                    sourcepackagename=None):
        """Assign karma for the action named <action_name> to this person.

        This karma will be associated with the given product or distribution.
        If a distribution is given, then product must be None and an optional
        sourcepackagename may also be given. If a product is given, then
        distribution and sourcepackagename must be None.
        """

    def latestKarma(quantity=25):
        """Return the latest karma actions for this person.

        Return no more than the number given as quantity.
        """

    def iterTopProjectsContributedTo(limit=10):
        """Iterate over the top projects contributed to.

        Iterate no more than the given limit.
        """

    def inTeam(team):
        """Return True if this person is a member or the owner of <team>.

        This method is meant to be called by objects which implement either
        IPerson or ITeam, and it will return True when you ask if a Person is
        a member of himself (i.e. person1.inTeam(person1)).
        """

    def lastShippedRequest():
        """Return this person's last shipped request, or None."""

    def pastShipItRequests():
        """Return the requests made by this person that can't be changed
        anymore.

        Any request that is cancelled, denied or sent for shipping can't be
        changed.
        """

    def shippedShipItRequestsOfCurrentSeries():
        """Return all requests made by this person that were sent to the
        shipping company already.

        This only includes requests for CDs of
        ShipItConstants.current_distroseries.
        """

    def currentShipItRequest():
        """Return this person's unshipped ShipIt request, if there's one.

        Return None otherwise.
        """

    def searchTasks(search_params, *args):
        """Search IBugTasks with the given search parameters.

        :search_params: a BugTaskSearchParams object
        :args: any number of BugTaskSearchParams objects

        If more than one BugTaskSearchParams is given, return the union of
        IBugTasks which match any of them.

        Return an iterable of matching results.
        """

    def latestMaintainedPackages():
        """Return SourcePackageReleases maintained by this person.

        This method will only include the latest source package release
        for each source package name, distribution series combination.
        """

    def latestUploadedButNotMaintainedPackages():
        """Return SourcePackageReleases created by this person but
        not maintained by him.

        This method will only include the latest source package release
        for each source package name, distribution series combination.
        """

    def isUploader(distribution):
        """Return whether this person is an uploader for distribution.

        Returns True if this person is an uploader for distribution, or
        False otherwise.
        """

    def validateAndEnsurePreferredEmail(email):
        """Ensure this person has a preferred email.

        If this person doesn't have a preferred email, <email> will be set as
        this person's preferred one. Otherwise it'll be set as VALIDATED and
        this person will keep their old preferred email.

        This method is meant to be the only one to change the status of an
        email address, but as we all know the real world is far from ideal
        and we have to deal with this in one more place, which is the case
        when people explicitly want to change their preferred email address.
        On that case, though, all we have to do is use
        person.setPreferredEmail().
        """

    def hasParticipationEntryFor(team):
        """Return True when this person is a member of the given team.

        The person's membership may be direct or indirect.
        """

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
        login and thus can't 'join' another team. Instead, they're added
        as a member (using the addMember() method) by a team administrator.
        """

    def leave(team):
        """Leave the given team.

        If there's a membership entry for this person on the given team and
        its status is either APPROVED or ADMIN, we change the status to
        DEACTIVATED and remove the relevant entries in teamparticipation.

        Teams cannot call this method because they're not allowed to
        login and thus can't 'leave' another team. Instead, they have their
        subscription deactivated (using the setMembershipData() method) by
        a team administrator.
        """

    def addMember(person, reviewer, status=TeamMembershipStatus.APPROVED,
                  comment=None, force_team_add=False):
        """Add the given person as a member of this team.

        If the given person is already a member of this team we'll simply
        change its membership status. Otherwise a new TeamMembership is
        created with the given status.

        If the person is actually a team and force_team_add is False, the
        team will actually be invited to join this one. Otherwise the team
        is added as if it were a person.

        The given status must be either Approved, Proposed or Admin.

        The reviewer is the user who made the given person a member of this
        team.
        """

    def setMembershipData(person, status, reviewer, expires=None,
                          comment=None):
        """Set the attributes of the person's membership on this team.

        Set the status, dateexpires, reviewer and comment, where reviewer is
        the user responsible for this status change and comment is the comment
        left by the reviewer for the change.

        This method will ensure that we only allow the status transitions
        specified in the TeamMembership spec. It's also responsible for
        filling/cleaning the TeamParticipation table when the transition
        requires it.
        """

    def getMembersByStatus(status, orderby=None):
        """Return the people whose membership on this team match :status:.

        If no orderby is provided, Person.sortingColumns is used.
        """

    def getAdministratedTeams():
        """Return the teams that this person/team is an administrator of.

        This includes teams for which the person is the owner, a direct
        member with admin privilege, or member of a team with such
        privileges.
        """

    def getDirectAdministrators():
        """Return this team's administrators.

         This includes all direct members with admin rights and also
         the team owner. Note that some other persons/teams might have admin
         privilege by virtue of being a member of a team with admin rights.
        """

    def getTeamAdminsEmailAddresses():
        """Return a set containing the email addresses of all administrators
        of this team.
        """

    def getSubTeams():
        """Return all subteams of this team.

        A subteam is any team that is (either directly or indirectly) a
        member of this team. As an example, let's say we have this hierarchy
        of teams:

        Rosetta Translators
            Rosetta pt Translators
                Rosetta pt_BR Translators

        In this case, both 'Rosetta pt Translators' and 'Rosetta pt_BR
        Translators' are subteams of the 'Rosetta Translators' team, and all
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

        In this case, we will return both 'Rosetta pt Translators' and
        'Rosetta Translators', because we are member of both of them.
        """

    def getLatestApprovedMembershipsForPerson(limit=5):
        """Return the <limit> latest approved membrships for this person."""

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

    def getDirectAnswerQuestionTargets():
        """Return a list of IQuestionTargets that a person is subscribed to.

        This will return IQuestionTargets that the person is registered as an
        answer contact because he subscribed himself.
        """

    def getTeamAnswerQuestionTargets():
        """Return a list of IQuestionTargets that are indirect subscriptions.

        This will return IQuestionTargets that the person or team is
        registered as an answer contact because of his membership in a team.
        """

    def searchQuestions(search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, participation=None,
                        needs_attention=None):
        """Search the person's questions.

        See IQuestionCollection for the description of the standard search
        parameters.

        :participation: A list of QuestionParticipation that defines the set
        of relationship to questions that will be searched. If None or an
        empty sequence, all relationships are considered.

        :needs_attention: If this flag is true, only questions needing
        attention from the person will be included. Questions needing
        attention are those owned by the person in the ANSWERED or NEEDSINFO
        state, as well as, those not owned by the person but on which the
        person requested for more information or gave an answer and that are
        back in the OPEN state.
        """


class ITeam(IPerson, IHasIcon):
    """ITeam extends IPerson.

    The teamowner should never be None.
    """

    # Logo and Mugshot are here so that they can have a description on a
    # Team which is different to the description they have on a Person.
    logo = LogoImageUpload(
        title=_("Logo"), required=False,
        default_image_resource='/@@/team-logo',
        description=_(
            "An image of exactly 64x64 pixels that will be displayed in "
            "the heading of all pages related to the team. Traditionally "
            "this is a logo, a small picture or a personal mascot. It "
            "should be no bigger than 50kb in size."))
    mugshot = MugshotImageUpload(
        title=_("Mugshot"), required=False,
        default_image_resource='/@@/team-mugshot',
        description=_(
            "A large image of exactly 192x192 pixels, that will be displayed "
            "on the team page in Launchpad. It "
            "should be no bigger than 100kb in size. "))
    displayname = StrippedTextLine(
            title=_('Display Name'), required=True, readonly=False,
            description=_(
                "This team's name as you would like it displayed throughout "
                "Launchpad."))


class IPersonSet(Interface):
    """The set of Persons."""

    title = Attribute('Title')

    def topPeople():
        """Return the top 5 people by Karma score in the Launchpad."""

    def createPersonAndEmail(
            email, rationale, comment=None, name=None, displayname=None,
            password=None, passwordEncrypted=False,
            hide_email_addresses=False, registrant=None):
        """Create a new Person and an EmailAddress with the given email.

        The comment must be of the following form: "when %(action_details)s"
        (e.g. "when the foo package was imported into Ubuntu Breezy").

        Return the newly created Person and EmailAddress if everything went
        fine or a (None, None) tuple otherwise.

        Generate a unique nickname from the email address provided, create a
        Person with that nickname and then create an EmailAddress (with status
        NEW) for the new Person.
        """

    def ensurePerson(email, displayname, rationale, comment=None,
                     registrant=None):
        """Make sure that there is a person in the database with the given
        email address. If necessary, create the person, using the
        displayname given.

        The comment must be of the following form: "when %(action_details)s"
        (e.g. "when the foo package was imported into Ubuntu Breezy").

        XXX sabdfl 2005-06-14: this should be extended to be similar or
        identical to the other person creation argument lists, so we can
        call it and create a full person if needed. Email would remain the
        deciding factor, we would not try and guess if someone existed based
        on the displayname or other arguments.
        """

    def newTeam(teamowner, name, displayname, teamdescription=None,
                subscriptionpolicy=TeamSubscriptionPolicy.MODERATED,
                defaultmembershipperiod=None, defaultrenewalperiod=None):
        """Create and return a new Team with given arguments."""

    def get(personid):
        """Return the person with the given id or None if it's not found."""

    def getByEmail(email):
        """Return the person with the given email address.

        Return None if there is no person with the given email address.
        """

    def getByName(name, ignore_merged=True):
        """Return the person with the given name, ignoring merged persons if
        ignore_merged is True.

        Return None if there is no person with the given name.
        """

    def getByOpenIdIdentifier(openid_identity):
        """Return the person with the given OpenID identifier, or None."""

    def getAllTeams(orderBy=None):
        """Return all Teams.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def getPOFileContributors(pofile):
        """Return people that have contributed to the specified POFile."""

    def getPOFileContributorsByDistroSeries(distroseries, language):
        """Return people who translated strings in distroseries to language.

        The people that translated only IPOTemplate objects that are not
        current will not appear in the returned list.
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

    def updateStatistics(ztm):
        """Update statistics caches and commit."""

    def peopleCount():
        """Return the number of non-merged persons in the database as
           of the last statistics update.
        """

    def teamsCount():
        """Return the number of teams in the database as of the last
           statistics update.
        """

    def find(text, orderBy=None):
        """Return all non-merged Persons and Teams whose name, displayname or
        email address match <text>.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.

        While we don't have Full Text Indexes in the emailaddress table, we'll
        be trying to match the text only against the beginning of an email
        address.
        """

    def findPerson(text="", orderBy=None):
        """Return all non-merged Persons with at least one email address whose
        name, displayname or email address match <text>.

        If text is an empty string, all persons with at least one email
        address will be returned.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.

        While we don't have Full Text Indexes in the emailaddress table, we'll
        be trying to match the text only against the beginning of an email
        address.
        """

    def findTeam(text, orderBy=None):
        """Return all Teams whose name, displayname or email address
        match <text>.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.

        While we don't have Full Text Indexes in the emailaddress table, we'll
        be trying to match the text only against the beginning of an email
        address.
        """

    def getUbunteros(orderBy=None):
        """Return a set of person with valid Ubuntero flag.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.
        """

    def latest_teams(limit=5):
        """Return the latest teams registered, up to the limit specified."""

    def merge(from_person, to_person):
        """Merge a person into another."""

    def getTranslatorsByLanguage(language):
        """Return the list of translators for the given language.

        :arg language: ILanguage object for which we want to get the
            translators.

        Return None if there is no translator.
        """

class IRequestPeopleMerge(Interface):
    """This schema is used only because we want a very specific vocabulary."""

    dupeaccount = Choice(
        title=_('Duplicated Account'), required=True,
        vocabulary='PersonAccountToMerge',
        description=_("The duplicated account you found in Launchpad"))


class IAdminRequestPeopleMerge(Interface):
    """The schema used by admin merge accounts page."""

    dupe_account = Choice(
        title=_('Duplicated Account'), required=True,
        vocabulary='PersonAccountToMerge',
        description=_("The duplicated account found in Launchpad"))

    target_account = Choice(
        title=_('Account'), required=True,
        vocabulary='PersonAccountToMerge',
        description=_("The account to be merged on"))


class IObjectReassignment(Interface):
    """The schema used by the object reassignment page."""

    owner = Choice(title=_('Owner'), vocabulary='ValidOwner', required=True)


class ITeamReassignment(Interface):
    """The schema used by the team reassignment page."""

    owner = Choice(
        title=_('Owner'), vocabulary='ValidTeamOwner', required=True)


class ITeamCreation(ITeam):
    """An interface to be used by the team creation form.

    We need this special interface so we can allow people to specify a contact
    email address for a team upon its creation.
    """

    contactemail = TextLine(
        title=_("Contact Email Address"), required=False, readonly=False,
        description=_(
            "This is the email address we'll send all notifications to this "
            "team. If no contact address is chosen, notifications directed "
            "to this team will be sent to all team members. After finishing "
            "the team creation, a new message will be sent to this address "
            "with instructions on how to finish its registration."),
        constraint=validate_new_team_email)


class ITeamContactAddressForm(Interface):

    contact_address = TextLine(
        title=_("Contact Email Address"), required=False, readonly=False)


class JoinNotAllowed(Exception):
    """User is not allowed to join a given team."""
