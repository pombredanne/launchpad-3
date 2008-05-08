# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Person interfaces."""

__metaclass__ = type

__all__ = [
    'AccountStatus',
    'IAdminPeopleMergeSchema',
    'IAdminTeamMergeSchema',
    'IHasStanding',
    'INACTIVE_ACCOUNT_STATUSES',
    'INewPerson',
    'INewPersonForm',
    'InvalidName',
    'IObjectReassignment',
    'IPerson',
    'IPersonAdminWriteRestricted',
    'IPersonChangePassword',
    'IPersonClaim',
    'IPersonEditRestricted',
    'IPersonPublic',
    'IPersonSet',
    'IPersonViewRestricted',
    'IRequestPeopleMerge',
    'ITeam',
    'ITeamContactAddressForm',
    'ITeamCreation',
    'ITeamReassignment',
    'JoinNotAllowed',
    'NameAlreadyTaken',
    'PersonCreationRationale',
    'PersonVisibility',
    'PersonalStanding',
    'TeamContactMethod',
    'TeamMembershipRenewalPolicy',
    'TeamSubscriptionPolicy',
    ]


from zope.formlib.form import NoInputData
from zope.schema import Bool, Choice, Datetime, Int, Text, TextLine
from zope.interface import Attribute, Interface
from zope.interface.exceptions import Invalid
from zope.interface.interface import invariant
from zope.component import getUtility

from canonical.lazr import DBEnumeratedType, DBItem, EnumeratedType, Item
from canonical.lazr.rest.declarations import (
   collection_default_content, export_as_webservice_collection)

from canonical.launchpad import _

from canonical.launchpad.fields import (
    BlacklistableContentNameField, IconImageUpload, LogoImageUpload,
    MugshotImageUpload, PasswordField, PublicPersonChoice, StrippedTextLine)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces.specificationtarget import (
    IHasSpecifications)
from canonical.launchpad.interfaces.launchpad import (
    IHasIcon, IHasLogo, IHasMugshot)
from canonical.launchpad.interfaces.mailinglistsubscription import (
    MailingListAutoSubscribePolicy)
from canonical.launchpad.interfaces.mentoringoffer import (
    IHasMentoringOffers)
from canonical.launchpad.interfaces.questioncollection import (
    IQuestionCollection, QUESTION_STATUS_DEFAULT_SEARCH)
from canonical.launchpad.interfaces.teammembership import TeamMembershipStatus
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


INACTIVE_ACCOUNT_STATUSES = [
    AccountStatus.DEACTIVATED, AccountStatus.SUSPENDED]


class PersonalStanding(DBEnumeratedType):
    """A person's standing.

    Standing is currently (just) used to determine whether a person's posts to
    a mailing list require first-post moderation or not.  Any person with good
    or excellent standing may post directly to the mailing list without
    moderation.  Any person with unknown or poor standing must have their
    first-posts moderated.
    """

    UNKNOWN = DBItem(0, """
        Unknown standing

        Nothing about this person's standing is known.
        """)

    POOR = DBItem(100, """
        Poor standing

        This person has poor standing.
        """)

    GOOD = DBItem(200, """
        Good standing

        This person has good standing and may post to a mailing list without
        being subject to first-post moderation rules.
        """)

    EXCELLENT = DBItem(300, """
        Excellent standing

        This person has excellent standing and may post to a mailing list
        without being subject to first-post moderation rules.
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
        Created by a user to represent a person which does not use Launchpad.

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

    BUGWATCH = DBItem(15, """
        Created by the updating of a bug watch.

        A watch was made against a remote bug that the user submitted or
        commented on.
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


class TeamSubscriptionPolicy(DBEnumeratedType):
    """Team Subscription Policies

    The policies that apply to a team and specify how new subscriptions must
    be handled. More information can be found in the TeamMembershipPolicies
    spec.
    """

    MODERATED = DBItem(1, """
        Moderated Team

        All subscriptions for this team are subject to approval by one of
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


class PersonVisibility(DBEnumeratedType):
    """The visibility level of person or team objects.

    Currently, only teams can have their visibility set to something
    besides PUBLIC.
    """

    PUBLIC = DBItem(1, """
        Public

        Everyone can view all the attributes of this person.
        """)

    PRIVATE_MEMBERSHIP = DBItem(20, """
        Private Membership

        Only launchpad admins and team members can view the
        membership list for this team.
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
        title=_('Current password'), required=True, readonly=False)

    password = PasswordField(
        title=_('New password'), required=True, readonly=False)


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


# This has to be defined here to avoid circular import problems.
class IHasStanding(Interface):
    """An object that can have personal standing."""

    personal_standing = Choice(
        title=_('Personal standing'),
        required=True,
        vocabulary=PersonalStanding,
        description=_('The standing of a person for non-member mailing list '
                      'posting privileges.'))

    personal_standing_reason = Text(
        title=_('Reason for personal standing'),
        required=False,
        description=_("The reason the person's standing is what it is."))


class IPersonPublic(IHasSpecifications, IHasMentoringOffers,
                    IQuestionCollection, IHasLogo, IHasMugshot, IHasIcon):
    """Public attributes for a Person."""

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

    oauth_access_tokens = Attribute(_("Non-expired access tokens"))

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
    teamowner = PublicPersonChoice(
        title=_('Team Owner'), required=False, readonly=False,
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

    safe_email_or_blank = TextLine(
        title=_("Safe email for display"),
        description=_("The person's preferred email if they have"
                      "one and do not choose to hide it. Otherwise"
                      "the empty string."),
        readonly=True)

    preferredemail_sha1 = TextLine(
        title=_("SHA-1 Hash of Preferred Email"),
        description=_("The SHA-1 hash of the preferred email address and "
                      "a mailto: prefix as a hexadecimal string. This is "
                      "used as a key by FOAF RDF spec"),
        readonly=True)

    verbose_bugnotifications = Bool(
        title=_("Include bug descriptions when sending me bug notifications"),
        required=False, default=True)

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
        title=_(
            "When someone's membership is about to expire, "
            "notify them and"),
        required=True, vocabulary=TeamMembershipRenewalPolicy,
        default=TeamMembershipRenewalPolicy.NONE)

    mailing_list_auto_subscribe_policy = Choice(
        title=_('Mailing List Auto-subscription Policy'),
        required=True,
        vocabulary=MailingListAutoSubscribePolicy,
        default=MailingListAutoSubscribePolicy.ON_REGISTRATION,
        description=_(
            "This attribute determines whether a person is "
            "automatically subscribed to a team's mailing list when the "
            "person joins said team."))

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

    structural_subscriptions = Attribute(
        "The structural subscriptions for this person.")

    visibility_consistency_warning = Attribute(
        "Warning that a private team may leak membership info.")

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

    def convertToTeam(team_owner):
        """Convert this person into a team owned by the given team_owner.

        Also adds the given team owner as an administrator of the team.

        Only Person entries whose account_status is NOACCOUNT and which are
        not teams can be converted into teams.
        """

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

    def getBugSubscriberPackages():
        """Return the packages for which this person is a bug subscriber.

        Returns a list of IDistributionSourcePackage's, ordered alphabetically
        (A to Z) by name.
        """

    def getBugSubscriberOpenBugCounts(user):
        """Return open bug counts for this bug subscriber's packages.

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

        If the team has a contact address its status will be changed to
        VALIDATED.

        If the given email is None the team is left without a contact address.
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

    # XXX BarryWarsaw 29-Nov-2007 I'd prefer for this to be an Object() with a
    # schema of IMailingList, but setting that up correctly causes a circular
    # import error with interfaces.mailinglists that is too difficult to
    # unfunge for this one attribute.
    mailing_list = Attribute(
        _("The team's mailing list, if it has one, otherwise None."))

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

        <team> can be the id of a team, an SQLObject representing the
        ITeam, or the name of the team.
        """

    def clearInTeamCache():
        """Clears the person's inTeam cache.

        To be used when membership changes are enacted. Only meant to be
        used between TeamMembership and Person objects.
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

    def getLatestMaintainedPackages():
        """Return `SourcePackageRelease`s maintained by this person.

        This method will only include the latest source package release
        for each source package name, distribution series combination.
        """

    def getLatestUploadedButNotMaintainedPackages():
        """Return `SourcePackageRelease`s created by this person but
        not maintained by him.

        This method will only include the latest source package release
        for each source package name, distribution series combination.
        """

    def getLatestUploadedPPAPackages():
        """Return `SourcePackageRelease`s uploaded by this person to any PPA.

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

    def getAdministratedTeams():
        """Return the teams that this person/team is an administrator of.

        This includes teams for which the person is the owner, a direct
        member with admin privilege, or member of a team with such
        privileges.
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

    def isBugContributor(user):
        """Is the person a contributer to bugs in Launchpad?

        Return True if the user has any bugs assigned to him, either
        directly or by team participation.

        :user: The user doing the search. Private bugs that this
        user doesn't have access to won't be included in the
        count.
        """

    def isBugContributorInTarget(user, target):
        """Is the person a contributor to bugs in `target`?

        Return True if the user has any bugs assigned to him in the
        context of a specific target, either directly or by team
        participation.

        :user: The user doing the search. Private bugs that this
        user doesn't have access to won't be included in the
        count.

        :target: An object providing `IBugTarget` to search within.
        """

    def autoSubscribeToMailingList(mailinglist, requester=None):
        """Subscribe this person to a mailing list.

        This method takes the user's mailing list auto-subscription
        setting into account, and it may or may not result in a list
        subscription.  It will only subscribe the user to the mailing
        list if all of the following conditions are met:

          * The mailing list is not None.
          * The mailing list is in an unusable state.
          * The user is not already subscribed.
          * The user has a preferred address set.
          * The user's auto-subscribe preference is ALWAYS, or
          * The user's auto-subscribe preference is ON_REGISTRATION,
            and the requester is either themself or None.

        This method will not raise exceptions if any of the above are
        not true.  If you want these problems to raise exceptions
        consider using `IMailinglist.subscribe()` directly.

        :param mailinglist: The list to subscribe to.  No action is
        	taken if the list is None, or in an unusable state.

        :param requester: The person requesting the list subscription,
        	if not the user himself.  The default assumes the user
        	themself is making the request.

        :return: True if the user was subscribed, false if they weren't.
        """


class IPersonViewRestricted(Interface):
    """IPerson attributes that require launchpad.View permission."""

    active_member_count = Attribute(
        "The number of real people who are members of this team.")
    activemembers = Attribute("List of members with ADMIN or APPROVED status")
    adminmembers = Attribute("List of members with ADMIN status")
    all_member_count = Attribute(
        "The total number of real people who are members of this team, "
        "including subteams.")
    allmembers = Attribute(
        "List of all direct and indirect people and teams who, one way or "
        "another, are a part of this team. If you want a method to check if "
        "a given person is a member of a team, you should probably look at "
        "IPerson.inTeam().")
    approvedmembers = Attribute("List of members with APPROVED status")
    deactivated_member_count = Attribute("Number of deactivated members")
    deactivatedmembers = Attribute("List of members with DEACTIVATED status")
    expired_member_count = Attribute("Number of EXPIRED members.")
    expiredmembers = Attribute("List of members with EXPIRED status")
    inactivemembers = Attribute(
        "List of members with EXPIRED or DEACTIVATED status")
    inactive_member_count = Attribute("Number of inactive members")
    invited_members = Attribute("List of members with INVITED status")
    invited_member_count = Attribute("Number of members with INVITED status")
    pendingmembers = Attribute(
        "List of members with INVITED or PROPOSED status")
    proposedmembers = Attribute("List of members with PROPOSED status")
    proposed_member_count = Attribute("Number of PROPOSED members")

    def getDirectAdministrators():
        """Return this team's administrators.

         This includes all direct members with admin rights and also
         the team owner. Note that some other persons/teams might have admin
         privilege by virtue of being a member of a team with admin rights.
        """

    def getMembersByStatus(status, orderby=None):
        """Return the people whose membership on this team match :status:.

        If no orderby is provided, Person.sortingColumns is used.
        """


class IPersonEditRestricted(Interface):
    """IPerson attributes that require launchpad.Edit permission."""

    def join(team, requester=None, may_subscribe_to_list=True):
        """Join the given team if its subscriptionpolicy is not RESTRICTED.

        Join the given team according to the policies and defaults of that
        team:
        - If the team subscriptionpolicy is OPEN, the user is added as
          an APPROVED member with a NULL TeamMembership.reviewer.
        - If the team subscriptionpolicy is MODERATED, the user is added as
          a PROPOSED member and one of the team's administrators have to
          approve the membership.

        If may_subscribe_to_list is True, then also attempt to
        subscribe to the team's mailing list, depending on the list
        status and the person's auto-subscribe settings.

        :param requester: The person who requested the membership on
            behalf of a team or None when a person requests the
            membership for himself.

        :param may_subscribe_to_list: If True, also try subscribing to
            the team mailing list.
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

    def addMember(person, reviewer, status=TeamMembershipStatus.APPROVED,
                  comment=None, force_team_add=False,
                  may_subscribe_to_list=True):
        """Add the given person as a member of this team.

        If the given person is already a member of this team we'll simply
        change its membership status. Otherwise a new TeamMembership is
        created with the given status.

        If the person is actually a team and force_team_add is False, the
        team will actually be invited to join this one. Otherwise the team
        is added as if it were a person.

        If the the person is not a team, and may_subscribe_to_list
        is True, then the person may be subscribed to the team's
        mailing list, depending on the list status and the person's
        auto-subscribe settings.

        The given status must be either Approved, Proposed or Admin.

        The reviewer is the user who made the given person a member of this
        team.
        """

    def deactivateAllMembers(comment, reviewer):
        """Deactivate all the members of this team."""

    def acceptInvitationToBeMemberOf(team, comment):
        """Accept an invitation to become a member of the given team.

        There must be a TeamMembership for this person and the given team with
        the INVITED status. The status of this TeamMembership will be changed
        to APPROVED.
        """

    def declineInvitationToBeMemberOf(team, comment):
        """Decline an invitation to become a member of the given team.

        There must be a TeamMembership for this person and the given team with
        the INVITED status. The status of this TeamMembership will be changed
        to INVITATION_DECLINED.
        """

    def renewTeamMembership(team):
        """Renew the TeamMembership for this person on the given team.

        The given team's renewal policy must be ONDEMAND and the membership
        must be active (APPROVED or ADMIN) and set to expire in less than
        DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT days.
        """


class IPersonAdminWriteRestricted(Interface):
    """IPerson attributes that require launchpad.Admin permission to set."""

    visibility = Choice(
        title=_("Visibility"),
        description=_(
            "Public visibility is standard, and Private Membership"
            " means that a team's members are hidden."),
        required=True, vocabulary=PersonVisibility,
        default=PersonVisibility.PUBLIC)


class IPerson(IPersonPublic, IPersonViewRestricted, IPersonEditRestricted,
              IPersonAdminWriteRestricted, IHasStanding):
    """A Person."""


class INewPersonForm(IPerson):
    """Interface used to create new Launchpad accounts.

    The only change with `IPerson` is a customised Password field.
    """

    password = PasswordField(
        title=_('Create password'), required=True, readonly=False)


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
    export_as_webservice_collection()

    title = Attribute('Title')

    def topPeople():
        """Return the top 5 people by Karma score in the Launchpad."""

    def createPersonAndEmail(
            email, rationale, comment=None, name=None, displayname=None,
            password=None, passwordEncrypted=False,
            hide_email_addresses=False, registrant=None):
        """Create and return an `IPerson` and `IEmailAddress`.

        The newly created EmailAddress will have a status of NEW and will be
        linked to the newly created Person.

        If the given name is None, we generate a unique nickname from the
        email address given.

        :param email: The email address, as text.
        :param rationale: An item of `PersonCreationRationale` to be used as
            the person's creation_rationale.
        :param comment: A comment explaining why the person record was
            created (usually used by scripts which create them automatically).
            Must be of the following form: "when %(action_details)s"
            (e.g. "when the foo package was imported into Ubuntu Breezy").
        :param name: The person's name.
        :param displayname: The person's displayname.
        :param password: The person's password.
        :param passwordEncrypted: Whether or not the given password is
            encrypted.
        :param registrant: The user who created this person, if any.
        :param hide_email_addresses: Whether or not Launchpad should hide the
            person's email addresses from other users.
        :raises InvalidName: When the given name is not valid.
        :raises InvalidEmailAddress: When the given email is not valid.
        :raises NameAlreadyTaken: When the given name is already in use.
        :raises EmailAddressAlreadyTaken: When the given email is already in
            use.
        :raises NicknameGenerationError: When no name is provided and we can't
            generate a nickname from the given email address.
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
        """Return all Teams, ignoring the merged ones.

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

    @collection_default_content()
    def find(text="", orderBy=None):
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

    def findPerson(text="", orderBy=None, exclude_inactive_accounts=True):
        """Return all non-merged Persons with at least one email address whose
        name, displayname or email address match <text>.

        If text is an empty string, all persons with at least one email
        address will be returned.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in Person._defaultOrder.

        If exclude_inactive_accounts is True, any accounts whose
        account_status is any of INACTIVE_ACCOUNT_STATUSES will not be in the
        returned set.

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

    def merge(from_person, to_person, deactivate_members=False, user=None):
        """Merge a person/team into another.

        The old person/team (from_person) will be left as an atavism.

        When merging two person entries, from_person can't have email
        addresses associated with.

        When merging teams, from_person must have no IMailingLists
        associated with and no active members. If it has active members,
        though, it's possible to have them deactivated before the merge by
        passing deactivate_members=True. In that case the user who's
        performing the merge must be provided as well.

        We are not yet game to delete the `from_person` entry from the
        database yet. We will let it roll for a while and see what cruft
        develops. -- StuartBishop 20050812
        """

    def getTranslatorsByLanguage(language):
        """Return the list of translators for the given language.

        :arg language: ILanguage object for which we want to get the
            translators.

        Return None if there is no translator.
        """

    def getValidPersons(self, persons):
        """Get all the Persons that are valid.

        This method is more effective than looking at
        Person.is_valid_person_or_team, since it avoids issuing one DB
        query per person. It queries the ValidPersonOrTeamCache table,
        issuing one query for all the person records. This makes the
        method useful for filling the ORM cache, so that checks to
        .is_valid_person won't issue any DB queries.

        XXX: This method exists mainly to fill the ORM cache for
             ValidPersonOrTeamCache. It would be better to add a column
             to the Person table. If we do that, this method can go
             away. Bug 221901. -- Bjorn Tillenius, 2008-04-25
        """

    def getPeopleWithBranches(product=None):
        """Return the people who have branches.

        :param product: If supplied, only people who have branches in the
            specified product are returned.
        """

    def getSubscribersForTargets(targets, recipients=None):
        """Return the set of subscribers for `targets`.

        :param targets: The sequence of targets for which to get the
                        subscribers.
        :param recipients: An optional instance of
                           `BugNotificationRecipients`.
                           If present, all found subscribers will be
                           added to it.
        """

    def updatePersonalStandings():
        """Update the personal standings of some people.

        Personal standing controls whether a person can post to a mailing list
        they are not a member of without moderation.  A person starts out with
        Unknown standing.  Once they have at least one message approved for
        three different lists, this method will bump their standing to Good.
        If a person's standing is already Good, or Poor or Excellent, no
        change to standing is made.
        """


class IRequestPeopleMerge(Interface):
    """This schema is used only because we want a very specific vocabulary."""

    dupeaccount = Choice(
        title=_('Duplicated Account'), required=True,
        vocabulary='PersonAccountToMerge',
        description=_("The duplicated account you found in Launchpad"))


class IAdminPeopleMergeSchema(Interface):
    """The schema used by the admin merge people page."""

    dupe_person = Choice(
        title=_('Duplicated Person'), required=True,
        vocabulary='PersonAccountToMerge',
        description=_("The duplicated person found in Launchpad."))

    target_person = Choice(
        title=_('Target Person'), required=True,
        vocabulary='PersonAccountToMerge',
        description=_("The person to be merged on."))


class IAdminTeamMergeSchema(Interface):
    """The schema used by the admin merge teams page."""

    dupe_person = Choice(
        title=_('Duplicated Team'), required=True, vocabulary='ValidTeam',
        description=_("The duplicated team found in Launchpad."))

    target_person = Choice(
        title=_('Target Team'), required=True, vocabulary='ValidTeam',
        description=_("The team to be merged on."))


class IObjectReassignment(Interface):
    """The schema used by the object reassignment page."""

    owner = PublicPersonChoice(title=_('Owner'), vocabulary='ValidOwner', 
                               required=True)


class ITeamReassignment(Interface):
    """The schema used by the team reassignment page."""

    owner = PublicPersonChoice(
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


class TeamContactMethod(EnumeratedType):
    """The method used by Launchpad to contact a given team."""

    HOSTED_LIST = Item("""
        The Launchpad mailing list for this team

        Notifications directed to this team are sent to its Launchpad-hosted
        mailing list.
        """)

    NONE = Item("""
        Each member individually

        Notifications directed to this team will be sent to each of its
        members.
        """)

    EXTERNAL_ADDRESS = Item("""
        Another e-mail address

        Notifications directed to this team are sent to the contact address
        specified.
        """)


class ITeamContactAddressForm(Interface):

    contact_address = TextLine(
        title=_("Contact Email Address"), required=False, readonly=False)

    contact_method = Choice(
        title=_("How do people contact these team's members?"),
        required=True, vocabulary=TeamContactMethod)


class JoinNotAllowed(Exception):
    """User is not allowed to join a given team."""


class InvalidName(Exception):
    """The name given for a person is not valid."""


class NameAlreadyTaken(Exception):
    """The name given for a person is already in use by other person."""
