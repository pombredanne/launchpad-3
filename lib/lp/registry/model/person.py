# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# vars() causes W0612
# pylint: disable-msg=E0611,W0212,W0612,C0322

"""Implementation classes for a Person."""

__metaclass__ = type
__all__ = [
    'AlreadyConvertedException',
    'get_recipients',
    'generate_nick',
    'IrcID',
    'IrcIDSet',
    'JabberID',
    'JabberIDSet',
    'JoinTeamEvent',
    'NicknameGenerationError',
    'Owner',
    'Person',
    'person_sort_key',
    'PersonLanguage',
    'PersonSet',
    'SSHKey',
    'SSHKeySet',
    'TeamInvitationEvent',
    'ValidPersonCache',
    'WikiName',
    'WikiNameSet',
    ]

from datetime import (
    datetime,
    timedelta,
    )
from operator import attrgetter
import random
import re
import subprocess
import weakref

from lazr.delegates import delegates
from lazr.restful.utils import get_current_browser_request
import pytz
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLMultipleJoin,
    SQLObjectNotFound,
    StringCol,
    )
from sqlobject.sqlbuilder import (
    AND,
    OR,
    SQLConstant,
    )
from storm.base import Storm
from storm.expr import (
    Alias,
    And,
    Desc,
    Exists,
    In,
    Join,
    LeftJoin,
    Min,
    Not,
    Or,
    Select,
    SQL,
    Union,
    Upper,
    )
from storm.info import ClassAlias
from storm.locals import (
    Int,
    Reference,
    )
from storm.store import (
    EmptyResultSet,
    Store,
    )
from zope.component import (
    adapter,
    getUtility,
    )
from zope.component.interfaces import ComponentLookupError
from zope.event import notify
from zope.interface import (
    alsoProvides,
    classImplements,
    implementer,
    implements,
    )
from zope.lifecycleevent import ObjectCreatedEvent
from zope.publisher.interfaces import Unauthorized
from zope.security.checker import (
    canAccess,
    canWrite,
    )
from zope.security.proxy import (
    ProxyFactory,
    removeSecurityProxy,
    )

from canonical.config import config
from canonical.database import postgresql
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor,
    quote,
    quote_like,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad import _
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.account import (
    Account,
    AccountPassword,
    )
from canonical.launchpad.database.emailaddress import (
    EmailAddress,
    HasOwnerMixin,
    )
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.database.logintoken import LoginToken
from canonical.launchpad.database.oauth import (
    OAuthAccessToken,
    OAuthRequestToken,
    )
from canonical.launchpad.helpers import (
    ensure_unicode,
    get_contact_email_addresses,
    get_email_template,
    shortlist,
    )
from canonical.launchpad.interfaces.account import (
    AccountCreationRationale,
    AccountStatus,
    AccountSuspendedError,
    IAccount,
    IAccountSet,
    INACTIVE_ACCOUNT_STATUSES,
    )
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus,
    IEmailAddress,
    IEmailAddressSet,
    InvalidEmailAddress,
    )
from canonical.launchpad.interfaces.launchpad import (
    IHasIcon,
    IHasLogo,
    IHasMugshot,
    )
from canonical.launchpad.interfaces.launchpadstatistic import (
    ILaunchpadStatisticSet,
    )
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.interfaces.lpstorm import (
    IMasterObject,
    IMasterStore,
    IStore,
    )
from canonical.launchpad.webapp.dbpolicy import MasterDatabasePolicy
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.answers.model.questionsperson import QuestionsPersonMixin
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.validators.email import valid_email
from lp.app.validators.name import (
    sanitize_name,
    valid_name,
    )
from lp.blueprints.enums import (
    SpecificationDefinitionStatus,
    SpecificationFilter,
    SpecificationImplementationStatus,
    SpecificationSort,
    )
from lp.blueprints.model.specification import (
    HasSpecificationsMixin,
    Specification,
    )
from lp.bugs.interfaces.bugtarget import IBugTarget
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    IBugTaskSet,
    )
from lp.bugs.model.bugtarget import HasBugsBase
from lp.bugs.model.bugtask import get_related_bugtasks_search_params
from lp.bugs.model.structuralsubscription import StructuralSubscription
from lp.code.interfaces.branchcollection import IBranchCollection
from lp.code.model.hasbranches import (
    HasBranchesMixin,
    HasMergeProposalsMixin,
    HasRequestedReviewsMixin,
    )
from lp.registry.errors import (
    InvalidName,
    JoinNotAllowed,
    NameAlreadyTaken,
    PPACreationError,
    )
from lp.registry.interfaces.codeofconduct import ISignedCodeOfConductSet
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.gpg import IGPGKeySet
from lp.registry.interfaces.irc import (
    IIrcID,
    IIrcIDSet,
    )
from lp.registry.interfaces.jabber import (
    IJabberID,
    IJabberIDSet,
    )
from lp.registry.interfaces.mailinglist import (
    IMailingListSet,
    MailingListStatus,
    PostedMessageStatus,
    PURGE_STATES,
    )
from lp.registry.interfaces.mailinglistsubscription import (
    MailingListAutoSubscribePolicy,
    )
from lp.registry.interfaces.person import (
    CLOSED_TEAM_POLICY,
    ClosedTeamSubscriptionPolicy,
    ImmutableVisibilityError,
    IPerson,
    IPersonSet,
    IPersonSettings,
    ITeam,
    OPEN_TEAM_POLICY,
    OpenTeamSubscriptionPolicy,
    PersonalStanding,
    PersonCreationRationale,
    PersonVisibility,
    TeamMembershipRenewalPolicy,
    TeamSubscriptionPolicy,
    validate_public_person,
    validate_subscription_policy,
    )
from lp.registry.interfaces.personnotification import IPersonNotificationSet
from lp.registry.interfaces.persontransferjob import IPersonMergeJobSource
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.role import IPersonRoles
from lp.registry.interfaces.ssh import (
    ISSHKey,
    ISSHKeySet,
    SSHKeyAdditionError,
    SSHKeyCompromisedError,
    SSHKeyType,
    )
from lp.registry.interfaces.teammembership import (
    IJoinTeamEvent,
    ITeamInvitationEvent,
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.registry.interfaces.wikiname import (
    IWikiName,
    IWikiNameSet,
    )
from lp.registry.model.codeofconduct import SignedCodeOfConduct
from lp.registry.model.karma import (
    Karma,
    KarmaAction,
    KarmaAssignedEvent,
    KarmaCache,
    KarmaCategory,
    KarmaTotalCache,
    )
from lp.registry.model.personlocation import PersonLocation
from lp.registry.model.pillar import PillarName
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.teammembership import (
    TeamMembership,
    TeamMembershipSet,
    TeamParticipation,
    )
from lp.services.openid.model.openididentifier import OpenIdIdentifier
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.services.salesforce.interfaces import (
    ISalesforceVoucherProxy,
    REDEEMABLE_VOUCHER_STATUSES,
    VOUCHER_STATUSES,
    )
from lp.services.worlddata.model.language import Language
from lp.soyuz.enums import (
    ArchivePurpose,
    ArchiveStatus,
    )
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriberSet
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.publishing import SourcePackagePublishingHistory
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
from lp.translations.model.hastranslationimports import (
    HasTranslationImportsMixin,
    )


class AlreadyConvertedException(Exception):
    """Raised when an attempt to claim a team that has been claimed."""


class JoinTeamEvent:
    """See `IJoinTeamEvent`."""

    implements(IJoinTeamEvent)

    def __init__(self, person, team):
        self.person = person
        self.team = team


class TeamInvitationEvent:
    """See `IJoinTeamEvent`."""

    implements(ITeamInvitationEvent)

    def __init__(self, member, team):
        self.member = member
        self.team = team


class ValidPersonCache(SQLBase):
    """Flags if a Person is active and usable in Launchpad.

    This is readonly, as this is a view in the database.

    Note that it performs poorly at least some of the time, and if
    EmailAddress and Person are already being queried, its probably better to
    query Account directly. See bug
    https://bugs.launchpad.net/launchpad/+bug/615237 for some
    corroborating information.
    """


def validate_person_visibility(person, attr, value):
    """Validate changes in visibility.

    * Prevent teams with inconsistent connections from being made private.
    * Prevent private teams from any transition.
    """

    # Prohibit any visibility changes for private teams.  This rule is
    # recognized to be Draconian and may be relaxed in the future.
    if person.visibility == PersonVisibility.PRIVATE:
        raise ImmutableVisibilityError(
            'A private team cannot change visibility.')

    # If transitioning to a non-public visibility, check for existing
    # relationships that could leak data.
    if value != PersonVisibility.PUBLIC:
        warning = person.visibilityConsistencyWarning(value)
        if warning is not None:
            raise ImmutableVisibilityError(warning)

    return value


_person_sort_re = re.compile("(?:[^\w\s]|[\d_])", re.U)


def person_sort_key(person):
    """Identical to `person_sort_key` in the database."""
    # Strip noise out of displayname. We do not have to bother with
    # name, as we know it is just plain ascii.
    displayname = _person_sort_re.sub(u'', person.displayname.lower())
    return "%s, %s" % (displayname.strip(), person.name)


class PersonSettings(Storm):
    "The relatively rarely used settings for person (not a team)."

    implements(IPersonSettings)

    __storm_table__ = 'PersonSettings'

    personID = Int("person", default=None, primary=True)
    person = Reference(personID, "Person.id")

    selfgenerated_bugnotifications = BoolCol(notNull=True, default=False)


def readonly_settings(message, interface):
    """Make an object that disallows writes to values on the interface.

    When you write, the message is raised in a NotImplementedError.
    """
    # We will make a class that has properties for each field on the
    # interface (we expect every name on the interface to correspond to a
    # zope.schema field).  Each property will have a getter that will
    # return the interface default for that name; and it will have a
    # setter that will raise a hopefully helpful error message
    # explaining why writing is not allowed.
    # This is the setter we are going to use for every property.
    def unwritable(self, value):
        raise NotImplementedError(message)
    # This will become the dict of the class.
    data = {}
    # The interface.names() method returns the names on the interface.  If
    # "all" is True, then you will also get the names on base
    # interfaces.  That is unlikely to be needed here, but would be the
    # expected behavior if it were.
    for name in interface.names(all=True):
        # This next line is a work-around for a classic problem of
        # closures in a loop. Closures are bound (indirectly) to frame
        # locals, which are a mutable collection. Therefore, if we
        # naively make closures for each different value within a loop,
        # each closure will be bound to the value as it is at the *end
        # of the loop*. That's usually not what we want. To prevent
        # this, we make a helper function (which has its own locals)
        # that returns the actual closure we want.
        closure_maker = lambda result: lambda self: result
        # Now we make a property with the name-specific getter and the generic
        # setter, and put it in the dictionary of the class we are making.
        data[name] = property(
            closure_maker(interface[name].default), unwritable)
    # Now we have all the attributes we want.  We will make the class...
    cls = type('Unwritable' + interface.__name__, (), data)
    # ...specify that the class implements the interface that we are working
    # with...
    classImplements(cls, interface)
    # ...and return an instance.  We should only need one, since it is
    # read-only.
    return cls()

_readonly_person_settings = readonly_settings(
    'Teams do not support changing this attribute.', IPersonSettings)


class Person(
    SQLBase, HasBugsBase, HasSpecificationsMixin, HasTranslationImportsMixin,
    HasBranchesMixin, HasMergeProposalsMixin, HasRequestedReviewsMixin,
    QuestionsPersonMixin):
    """A Person."""

    implements(IPerson, IHasIcon, IHasLogo, IHasMugshot)

    def __init__(self, *args, **kwargs):
        super(Person, self).__init__(*args, **kwargs)
        # Initialize our PersonSettings object/record.
        if not self.is_team:
            # This is a Person, not a team.  Teams may want a TeamSettings
            # in the future.
            settings = PersonSettings()
            settings.person = self

    @cachedproperty
    def _person_settings(self):
        if self.is_team:
            # Teams need to provide these attributes for reading in order for
            # things like snapshots to work, but they are not actually
            # pertinent to teams, so they are not actually implemented for
            # writes.
            return _readonly_person_settings
        else:
            # This is a person.
            return IStore(PersonSettings).find(
                PersonSettings,
                PersonSettings.person == self).one()

    delegates(IPersonSettings, context='_person_settings')

    sortingColumns = SQLConstant(
        "person_sort_key(Person.displayname, Person.name)")
    # Redefine the default ordering into Storm syntax.
    _storm_sortingColumns = ('Person.displayname', 'Person.name')
    # When doing any sort of set operations (union, intersect, except_) with
    # SQLObject we can't use sortingColumns because the table name Person is
    # not available in that context, so we use this one.
    _sortingColumnsForSetOperations = SQLConstant(
        "person_sort_key(displayname, name)")
    _defaultOrder = sortingColumns
    _visibility_warning_marker = object()
    _visibility_warning_cache = _visibility_warning_marker

    account = ForeignKey(dbName='account', foreignKey='Account', default=None)

    def _validate_name(self, attr, value):
        """Check that rename is allowed."""
        # Renaming a team is prohibited for any team that has a non-purged
        # mailing list.  This is because renaming a mailing list is not
        # trivial in Mailman 2.1 (see Mailman FAQ item 4.70).  We prohibit
        # such renames in the team edit details view, but just to be safe, we
        # also assert that such an attempt is not being made here.  To do
        # this, we must override the SQLObject method for setting the 'name'
        # database column.  Watch out for when SQLObject is creating this row,
        # because in that case self.name isn't yet available.
        if self.name is None:
            mailing_list = None
        else:
            mailing_list = getUtility(IMailingListSet).get(self.name)
        can_rename = (self._SO_creating or
                      not self.is_team or
                      mailing_list is None or
                      mailing_list.status == MailingListStatus.PURGED)
        assert can_rename, 'Cannot rename teams with mailing lists'
        # Everything's okay, so let SQLObject do the normal thing.
        return value

    name = StringCol(dbName='name', alternateID=True, notNull=True,
                     storm_validator=_validate_name)

    def __repr__(self):
        displayname = self.displayname.encode('ASCII', 'backslashreplace')
        return '<Person at 0x%x %s (%s)>' % (id(self), self.name, displayname)

    displayname = StringCol(dbName='displayname', notNull=True)

    teamdescription = StringCol(dbName='teamdescription', default=None)
    homepage_content = StringCol(default=None)
    icon = ForeignKey(
        dbName='icon', foreignKey='LibraryFileAlias', default=None)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    mugshot = ForeignKey(
        dbName='mugshot', foreignKey='LibraryFileAlias', default=None)

    def _get_password(self):
        # We have to remove the security proxy because the password is
        # needed before we are authenticated. I'm not overly worried because
        # this method is scheduled for demolition -- StuartBishop 20080514
        password = IStore(AccountPassword).find(
            AccountPassword, accountID=self.accountID).one()
        if password is None:
            return None
        else:
            return password.password

    def _set_password(self, value):
        account = IMasterStore(Account).get(Account, self.accountID)
        assert account is not None, 'No account for this Person.'
        account.password = value

    password = property(_get_password, _set_password)

    def _get_account_status(self):
        account = IStore(Account).get(Account, self.accountID)
        if account is not None:
            return account.status
        else:
            return AccountStatus.NOACCOUNT

    def _set_account_status(self, value):
        assert self.accountID is not None, 'No account for this Person'
        account = IMasterStore(Account).get(Account, self.accountID)
        account.status = value

    # Deprecated - this value has moved to the Account table.
    # We provide this shim for backwards compatibility.
    account_status = property(_get_account_status, _set_account_status)

    def _get_account_status_comment(self):
        account = IStore(Account).get(Account, self.accountID)
        if account is not None:
            return account.status_comment

    def _set_account_status_comment(self, value):
        assert self.accountID is not None, 'No account for this Person'
        account = IMasterStore(Account).get(Account, self.accountID)
        account.status_comment = value

    # Deprecated - this value has moved to the Account table.
    # We provide this shim for backwards compatibility.
    account_status_comment = property(
            _get_account_status_comment, _set_account_status_comment)

    teamowner = ForeignKey(dbName='teamowner', foreignKey='Person',
                           default=None,
                           storm_validator=validate_public_person)

    sshkeys = SQLMultipleJoin('SSHKey', joinColumn='person')

    renewal_policy = EnumCol(
        enum=TeamMembershipRenewalPolicy,
        default=TeamMembershipRenewalPolicy.NONE)
    subscriptionpolicy = EnumCol(
        dbName='subscriptionpolicy',
        enum=(ClosedTeamSubscriptionPolicy, OpenTeamSubscriptionPolicy,
              TeamSubscriptionPolicy),
        default=TeamSubscriptionPolicy.MODERATED,
        storm_validator=validate_subscription_policy)
    defaultrenewalperiod = IntCol(dbName='defaultrenewalperiod', default=None)
    defaultmembershipperiod = IntCol(dbName='defaultmembershipperiod',
                                     default=None)
    mailing_list_auto_subscribe_policy = EnumCol(
        enum=MailingListAutoSubscribePolicy,
        default=MailingListAutoSubscribePolicy.ON_REGISTRATION)

    merged = ForeignKey(dbName='merged', foreignKey='Person', default=None)

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    creation_rationale = EnumCol(enum=PersonCreationRationale, default=None)
    creation_comment = StringCol(default=None)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', default=None,
        storm_validator=validate_public_person)
    hide_email_addresses = BoolCol(notNull=True, default=False)
    verbose_bugnotifications = BoolCol(notNull=True, default=True)

    signedcocs = SQLMultipleJoin('SignedCodeOfConduct', joinColumn='owner')
    _ircnicknames = SQLMultipleJoin('IrcID', joinColumn='person')
    jabberids = SQLMultipleJoin('JabberID', joinColumn='person')

    entitlements = SQLMultipleJoin('Entitlement', joinColumn='person')
    visibility = EnumCol(
        enum=PersonVisibility,
        default=PersonVisibility.PUBLIC,
        storm_validator=validate_person_visibility)

    personal_standing = EnumCol(
        enum=PersonalStanding, default=PersonalStanding.UNKNOWN,
        notNull=True)

    personal_standing_reason = StringCol(default=None)

    @cachedproperty
    def ircnicknames(self):
        return list(self._ircnicknames)

    @cachedproperty
    def languages(self):
        """See `IPerson`."""
        results = Store.of(self).find(
            Language, And(Language.id == PersonLanguage.languageID,
                          PersonLanguage.personID == self.id))
        results.order_by(Language.englishname)
        return list(results)

    def getLanguagesCache(self):
        """Return this person's cached languages.

        :raises AttributeError: If the cache doesn't exist.
        """
        return get_property_cache(self).languages

    def setLanguagesCache(self, languages):
        """Set this person's cached languages.

        Order them by name if necessary.
        """
        get_property_cache(self).languages = sorted(
            languages, key=attrgetter('englishname'))

    def deleteLanguagesCache(self):
        """Delete this person's cached languages, if it exists."""
        del get_property_cache(self).languages

    def addLanguage(self, language):
        """See `IPerson`."""
        person_language = Store.of(self).find(
            PersonLanguage, And(PersonLanguage.languageID == language.id,
                                PersonLanguage.personID == self.id)).one()
        if person_language is not None:
            # Nothing to do.
            return
        PersonLanguage(person=self, language=language)
        self.deleteLanguagesCache()

    def removeLanguage(self, language):
        """See `IPerson`."""
        person_language = Store.of(self).find(
            PersonLanguage, And(PersonLanguage.languageID == language.id,
                                PersonLanguage.personID == self.id)).one()
        if person_language is None:
            # Nothing to do.
            return
        PersonLanguage.delete(person_language.id)
        self.deleteLanguagesCache()

    def _init(self, *args, **kw):
        """Mark the person as a team when created or fetched from database."""
        SQLBase._init(self, *args, **kw)
        if self.teamownerID is not None:
            alsoProvides(self, ITeam)

    def convertToTeam(self, team_owner):
        """See `IPerson`."""
        if self.is_team:
            raise AlreadyConvertedException(
                "%s has already been converted to a team." % self.name)
        assert self.account_status == AccountStatus.NOACCOUNT, (
            "Only Person entries whose account_status is NOACCOUNT can be "
            "converted into teams.")
        # Teams don't have Account records
        if self.account is not None:
            account_id = self.account.id
            self.account = None
            Account.delete(account_id)
        self.creation_rationale = None
        self.teamowner = team_owner
        alsoProvides(self, ITeam)
        # Add the owner as a team admin manually because we know what we're
        # doing and we don't want any email notifications to be sent.
        TeamMembershipSet().new(
            team_owner, self, TeamMembershipStatus.ADMIN, team_owner)

    @property
    def oauth_access_tokens(self):
        """See `IPerson`."""
        return Store.of(self).find(
            OAuthAccessToken,
            OAuthAccessToken.person == self,
            Or(OAuthAccessToken.date_expires == None,
               OAuthAccessToken.date_expires > UTC_NOW))

    @property
    def oauth_request_tokens(self):
        """See `IPerson`."""
        return Store.of(self).find(
            OAuthRequestToken,
            OAuthRequestToken.person == self,
            Or(OAuthRequestToken.date_expires == None,
               OAuthRequestToken.date_expires > UTC_NOW))

    @cachedproperty
    def location(self):
        """See `IObjectWithLocation`."""
        return PersonLocation.selectOneBy(person=self)

    @property
    def time_zone(self):
        """See `IHasLocation`."""
        if self.location is None:
            return None
        # Wrap the location with a security proxy to make sure the user has
        # enough rights to see it.
        return ProxyFactory(self.location).time_zone

    @property
    def latitude(self):
        """See `IHasLocation`."""
        if self.location is None:
            return None
        # Wrap the location with a security proxy to make sure the user has
        # enough rights to see it.
        return ProxyFactory(self.location).latitude

    @property
    def longitude(self):
        """See `IHasLocation`."""
        if self.location is None:
            return None
        # Wrap the location with a security proxy to make sure the user has
        # enough rights to see it.
        return ProxyFactory(self.location).longitude

    def setLocationVisibility(self, visible):
        """See `ISetLocation`."""
        assert not self.is_team, 'Cannot edit team location.'
        if self.location is None:
            get_property_cache(self).location = PersonLocation(
                person=self, visible=visible)
        else:
            self.location.visible = visible

    def setLocation(self, latitude, longitude, time_zone, user):
        """See `ISetLocation`."""
        assert not self.is_team, 'Cannot edit team location.'
        assert ((latitude is None and longitude is None) or
                (latitude is not None and longitude is not None)), (
            "Cannot set a latitude without longitude (and vice-versa).")

        if self.location is not None:
            self.location.time_zone = time_zone
            self.location.latitude = latitude
            self.location.longitude = longitude
            self.location.last_modified_by = user
            self.location.date_last_modified = UTC_NOW
        else:
            get_property_cache(self).location = PersonLocation(
                person=self, time_zone=time_zone, latitude=latitude,
                longitude=longitude, last_modified_by=user)

    # specification-related joins
    @property
    def assigned_specs(self):
        return shortlist(Specification.selectBy(
            assignee=self, orderBy=['-datecreated']))

    @property
    def assigned_specs_in_progress(self):
        replacements = sqlvalues(assignee=self)
        replacements['started_clause'] = Specification.started_clause
        replacements['completed_clause'] = Specification.completeness_clause
        query = """
            (assignee = %(assignee)s)
            AND (%(started_clause)s)
            AND NOT (%(completed_clause)s)
            """ % replacements
        return Specification.select(query, orderBy=['-date_started'], limit=5)

    @property
    def unique_displayname(self):
        """See `IPerson`."""
        return "%s (%s)" % (self.displayname, self.name)

    @property
    def has_any_specifications(self):
        """See `IHasSpecifications`."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    @property
    def valid_specifications(self):
        return self.specifications(filter=[SpecificationFilter.VALID])

    def specifications(self, sort=None, quantity=None, filter=None,
                       prejoin_people=True):
        """See `IHasSpecifications`."""

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # if no filter was passed (None or []) then we must decide the
            # default filtering, and for a person we want related incomplete
            # specs
            filter = [SpecificationFilter.INCOMPLETE]

        # now look at the filter and fill in the unsaid bits

        # defaults for completeness: if nothing is said about completeness
        # then we want to show INCOMPLETE
        completeness = False
        for option in [
            SpecificationFilter.COMPLETE,
            SpecificationFilter.INCOMPLETE]:
            if option in filter:
                completeness = True
        if completeness is False:
            filter.append(SpecificationFilter.INCOMPLETE)

        # defaults for acceptance: in this case we have nothing to do
        # because specs are not accepted/declined against a person

        # defaults for informationalness: we don't have to do anything
        # because the default if nothing is said is ANY

        # if no roles are given then we want everything
        linked = False
        roles = set([
            SpecificationFilter.CREATOR,
            SpecificationFilter.ASSIGNEE,
            SpecificationFilter.DRAFTER,
            SpecificationFilter.APPROVER,
            SpecificationFilter.FEEDBACK,
            SpecificationFilter.SUBSCRIBER])
        for role in roles:
            if role in filter:
                linked = True
        if not linked:
            for role in roles:
                filter.append(role)

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'Specification.definition_status',
                     'Specification.name']
        elif sort == SpecificationSort.DATE:
            order = ['-Specification.datecreated', 'Specification.id']

        # figure out what set of specifications we are interested in. for
        # products, we need to be able to filter on the basis of:
        #
        #  - role (owner, drafter, approver, subscriber, assignee etc)
        #  - completeness.
        #  - informational.
        #

        # in this case the "base" is quite complicated because it is
        # determined by the roles so lets do that first

        base = '(1=0'  # we want to start with a FALSE and OR them
        if SpecificationFilter.CREATOR in filter:
            base += ' OR Specification.owner = %(my_id)d'
        if SpecificationFilter.ASSIGNEE in filter:
            base += ' OR Specification.assignee = %(my_id)d'
        if SpecificationFilter.DRAFTER in filter:
            base += ' OR Specification.drafter = %(my_id)d'
        if SpecificationFilter.APPROVER in filter:
            base += ' OR Specification.approver = %(my_id)d'
        if SpecificationFilter.SUBSCRIBER in filter:
            base += """ OR Specification.id in
                (SELECT specification FROM SpecificationSubscription
                 WHERE person = %(my_id)d)"""
        if SpecificationFilter.FEEDBACK in filter:
            base += """ OR Specification.id in
                (SELECT specification FROM SpecificationFeedback
                 WHERE reviewer = %(my_id)d)"""
        base += ') '

        # filter out specs on inactive products
        base += """AND (Specification.product IS NULL OR
                        Specification.product NOT IN
                         (SELECT Product.id FROM Product
                          WHERE Product.active IS FALSE))
                """

        base = base % {'my_id': self.id}

        query = base
        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += (' AND Specification.implementation_status = %s' %
                quote(SpecificationImplementationStatus.INFORMATIONAL))

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness = Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # Filter for validity. If we want valid specs only then we should
        # exclude all OBSOLETE or SUPERSEDED specs
        if SpecificationFilter.VALID in filter:
            query += (
                ' AND Specification.definition_status NOT IN ( %s, ''%s ) ' %
                sqlvalues(SpecificationDefinitionStatus.OBSOLETE,
                          SpecificationDefinitionStatus.SUPERSEDED))

        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base

        # Filter for specification text
        for constraint in filter:
            if isinstance(constraint, basestring):
                # a string in the filter is a text search filter
                query += ' AND Specification.fti @@ ftq(%s) ' % quote(
                    constraint)

        results = Specification.select(query, orderBy=order,
            limit=quantity)
        if prejoin_people:
            results = results.prejoin(['assignee', 'approver', 'drafter'])
        return results

    # XXX: Tom Berger 2008-04-14 bug=191799:
    # The implementation of these functions
    # is no longer appropriate, since it now relies on subscriptions,
    # rather than package bug supervisors.
    def getBugSubscriberPackages(self):
        """See `IPerson`."""
        # Avoid circular imports.
        from lp.registry.model.distributionsourcepackage import (
            DistributionSourcePackage,
            )
        from lp.registry.model.distribution import Distribution
        origin = (
            StructuralSubscription,
            Join(
                Distribution,
                StructuralSubscription.distributionID == Distribution.id),
            Join(
                SourcePackageName,
                StructuralSubscription.sourcepackagenameID ==
                    SourcePackageName.id)
            )
        result = Store.of(self).using(*origin).find(
            (Distribution, SourcePackageName),
            StructuralSubscription.subscriberID == self.id)
        result.order_by(SourcePackageName.name)

        def decorator(row):
            return DistributionSourcePackage(*row)

        return DecoratedResultSet(result, decorator)

    def findPathToTeam(self, team):
        """See `IPerson`."""
        # This is our guarantee that _getDirectMemberIParticipateIn() will
        # never return None
        assert self.hasParticipationEntryFor(team), (
            "%s doesn't seem to be a member/participant in %s"
            % (self.name, team.name))
        assert team.is_team, "You can't pass a person to this method."
        path = [team]
        team = self._getDirectMemberIParticipateIn(team)
        while team != self:
            path.insert(0, team)
            team = self._getDirectMemberIParticipateIn(team)
        return path

    def _getDirectMemberIParticipateIn(self, team):
        """Return a direct member of the given team that this person
        participates in.

        If there are more than one direct member of the given team that this
        person participates in, the one with the oldest creation date is
        returned.
        """
        query = AND(
            TeamMembership.q.teamID == team.id,
            TeamMembership.q.personID == Person.q.id,
            OR(TeamMembership.q.status == TeamMembershipStatus.ADMIN,
               TeamMembership.q.status == TeamMembershipStatus.APPROVED),
            TeamParticipation.q.teamID == Person.q.id,
            TeamParticipation.q.personID == self.id)
        clauseTables = ['TeamMembership', 'TeamParticipation']
        member = Person.selectFirst(
            query, clauseTables=clauseTables, orderBy='datecreated')
        assert member is not None, (
            "%(person)s is an indirect member of %(team)s but %(person)s "
            "is not a participant in any direct member of %(team)s"
            % dict(person=self.name, team=team.name))
        return member

    @property
    def is_team(self):
        """See `IPerson`."""
        return self.teamownerID is not None

    def isTeam(self):
        """Deprecated. Use is_team instead."""
        return self.is_team

    @property
    def mailing_list(self):
        """See `IPerson`."""
        return getUtility(IMailingListSet).get(self.name)

    def _customizeSearchParams(self, search_params):
        """No-op, to satisfy a requirement of HasBugsBase."""
        pass

    def searchTasks(self, search_params, *args, **kwargs):
        """See `IHasBugs`."""
        prejoins = kwargs.pop('prejoins', [])
        if search_params is None and len(args) == 0:
            # this method is called via webapi directly
            # calling this method on a Person object directly via the
            # webservice API means searching for user related tasks
            user = kwargs.pop('user')
            search_params = get_related_bugtasks_search_params(
                user, self, **kwargs)
            return getUtility(IBugTaskSet).search(
                *search_params, prejoins=prejoins)
        if len(kwargs) > 0:
            # if keyword arguments are supplied, use the deault
            # implementation in HasBugsBase.
            return HasBugsBase.searchTasks(
                self, search_params, prejoins=prejoins, **kwargs)
        else:
            # Otherwise pass all positional arguments to the
            # implementation in BugTaskSet.
            return getUtility(IBugTaskSet).search(
                search_params, *args, prejoins=prejoins)

    def getProjectsAndCategoriesContributedTo(self, limit=5):
        """See `IPerson`."""
        contributions = []
        # Pillars names have no concept of active. Extra pillars names are
        # requested because deactivated pillars will be filtered out.
        extra_limit = limit + 5
        results = self._getProjectsWithTheMostKarma(limit=extra_limit)
        for pillar_name, karma in results:
            pillar = getUtility(IPillarNameSet).getByName(
                pillar_name, ignore_inactive=True)
            if pillar is not None:
                contributions.append(
                    {'project': pillar,
                     'categories': self._getContributedCategories(pillar)})
            if len(contributions) == limit:
                break
        return contributions

    def _getProjectsWithTheMostKarma(self, limit=10):
        """Return the names and karma points of of this person on the
        product/distribution with that name.

        The results are ordered descending by the karma points and limited to
        the given limit.
        """
        # We want this person's total karma on a given context (that is,
        # across all different categories) here; that's why we use a
        # "KarmaCache.category IS NULL" clause here.
        query = """
            SELECT PillarName.name, KarmaCache.karmavalue
            FROM KarmaCache
            JOIN PillarName ON
                COALESCE(KarmaCache.distribution, -1) =
                COALESCE(PillarName.distribution, -1)
                AND
                COALESCE(KarmaCache.product, -1) =
                COALESCE(PillarName.product, -1)
            WHERE person = %(person)s
                AND KarmaCache.category IS NULL
                AND KarmaCache.project IS NULL
            ORDER BY karmavalue DESC, name
            LIMIT %(limit)s;
            """ % sqlvalues(person=self, limit=limit)
        cur = cursor()
        cur.execute(query)
        return cur.fetchall()

    def getOwnedOrDrivenPillars(self):
        """See `IPerson`."""
        find_spec = (PillarName, SQL('kind'), SQL('displayname'))
        origin = SQL("""
            PillarName
            JOIN (
                SELECT name, 3 as kind, displayname
                FROM product
                WHERE
                    active = True AND
                    (driver = %(person)s
                    OR owner = %(person)s)
                UNION
                SELECT name, 2 as kind, displayname
                FROM project
                WHERE
                    active = True AND
                    (driver = %(person)s
                    OR owner = %(person)s)
                UNION
                SELECT name, 1 as kind, displayname
                FROM distribution
                WHERE
                    driver = %(person)s
                    OR owner = %(person)s
                ) _pillar
                ON PillarName.name = _pillar.name
            """ % sqlvalues(person=self))
        results = IStore(self).using(origin).find(find_spec)
        results = results.order_by('kind', 'displayname')

        def get_pillar_name(result):
            pillar_name, kind, displayname = result
            return pillar_name

        return DecoratedResultSet(results, get_pillar_name)

    def getOwnedProjects(self, match_name=None):
        """See `IPerson`."""
        # Import here to work around a circular import problem.
        from lp.registry.model.product import Product

        clauses = ["""
            SELECT DISTINCT Product.id
            FROM Product, TeamParticipation
            WHERE TeamParticipation.person = %(person)s
            AND owner = TeamParticipation.team
            AND Product.active IS TRUE
            """ % sqlvalues(person=self)]

        # We only want to use the extra query if match_name is not None and it
        # is not the empty string ('' or u'').
        if match_name:
            like_query = "'%%' || %s || '%%'" % quote_like(match_name)
            quoted_query = quote(match_name)
            clauses.append(
                """(Product.name LIKE %s OR
                    Product.displayname LIKE %s OR
                    fti @@ ftq(%s))""" % (like_query,
                                          like_query,
                                          quoted_query))
        query = " AND ".join(clauses)
        results = Product.select("""id IN (%s)""" % query,
                                 orderBy=['displayname'])
        return results

    def getAllCommercialSubscriptionVouchers(self, voucher_proxy=None):
        """See `IPerson`."""
        if voucher_proxy is None:
            voucher_proxy = getUtility(ISalesforceVoucherProxy)
        commercial_vouchers = voucher_proxy.getAllVouchers(self)
        vouchers = {}
        for status in VOUCHER_STATUSES:
            vouchers[status] = []
        for voucher in commercial_vouchers:
            assert voucher.status in VOUCHER_STATUSES, (
                "Voucher %s has unrecognized status %s" %
                (voucher.voucher_id, voucher.status))
            vouchers[voucher.status].append(voucher)
        return vouchers

    def getRedeemableCommercialSubscriptionVouchers(self, voucher_proxy=None):
        """See `IPerson`."""
        if voucher_proxy is None:
            voucher_proxy = getUtility(ISalesforceVoucherProxy)
        vouchers = voucher_proxy.getUnredeemedVouchers(self)
        for voucher in vouchers:
            assert voucher.status in REDEEMABLE_VOUCHER_STATUSES, (
                "Voucher %s has invalid status %s" %
                (voucher.voucher_id, voucher.status))
        return vouchers

    def iterTopProjectsContributedTo(self, limit=10):
        getByName = getUtility(IPillarNameSet).getByName
        for name, ignored in self._getProjectsWithTheMostKarma(limit=limit):
            yield getByName(name)

    def _getContributedCategories(self, pillar):
        """Return the KarmaCategories to which this person has karma on the
        given pillar.

        The given pillar must be either an IProduct or an IDistribution.
        """
        if IProduct.providedBy(pillar):
            where_clause = "product = %s" % sqlvalues(pillar)
        elif IDistribution.providedBy(pillar):
            where_clause = "distribution = %s" % sqlvalues(pillar)
        else:
            raise AssertionError(
                "Pillar must be a product or distro, got %s" % pillar)
        replacements = sqlvalues(person=self)
        replacements['where_clause'] = where_clause
        query = """
            SELECT DISTINCT KarmaCategory.id
            FROM KarmaCategory
            JOIN KarmaCache ON KarmaCache.category = KarmaCategory.id
            WHERE %(where_clause)s
                AND category IS NOT NULL
                AND person = %(person)s
            """ % replacements
        cur = cursor()
        cur.execute(query)
        ids = ",".join(str(id) for [id] in cur.fetchall())
        return KarmaCategory.select("id IN (%s)" % ids)

    @property
    def karma_category_caches(self):
        """See `IPerson`."""
        store = Store.of(self)
        conditions = And(
            KarmaCache.category == KarmaCategory.id,
            KarmaCache.person == self.id,
            KarmaCache.product == None,
            KarmaCache.project == None,
            KarmaCache.distribution == None,
            KarmaCache.sourcepackagename == None)
        result = store.find((KarmaCache, KarmaCategory), conditions)
        result = result.order_by(KarmaCategory.title)
        return [karma_cache for (karma_cache, category) in result]

    @cachedproperty
    def karma(self):
        """See `IPerson`."""
        # May also be loaded from _members
        cache = KarmaTotalCache.selectOneBy(person=self)
        if cache is None:
            # Newly created accounts may not be in the cache yet, meaning the
            # karma updater script hasn't run since the account was created.
            return 0
        else:
            return cache.karma_total

    @property
    def is_valid_person_or_team(self):
        """See `IPerson`."""
        # Teams are always valid
        if self.isTeam():
            return True

        return self.is_valid_person

    @cachedproperty
    def is_valid_person(self):
        """See `IPerson`."""
        # This is prepopulated by various queries in and out of person.py.
        if self.is_team:
            return False
        try:
            ValidPersonCache.get(self.id)
            return True
        except SQLObjectNotFound:
            return False

    @property
    def is_probationary(self):
        """See `IPerson`.

        Users without karma have not demostrated their intentions may not
        have the same privileges as users who have made contributions.
        """
        return not self.isTeam() and self.karma == 0

    def assignKarma(self, action_name, product=None, distribution=None,
                    sourcepackagename=None, datecreated=None):
        """See `IPerson`."""
        # Teams don't get Karma. Inactive accounts don't get Karma.
        # The system user and janitor, does not get karma.
        # No warning, as we don't want to place the burden on callsites
        # to check this.
        if (not self.is_valid_person
            or self.id == getUtility(ILaunchpadCelebrities).janitor.id):
            return None

        if product is not None:
            assert distribution is None and sourcepackagename is None
        elif distribution is not None:
            assert product is None
        else:
            raise AssertionError(
                'You must provide either a product or a distribution.')

        try:
            action = KarmaAction.byName(action_name)
        except SQLObjectNotFound:
            raise AssertionError(
                "No KarmaAction found with name '%s'." % action_name)

        if datecreated is None:
            datecreated = UTC_NOW
        karma = Karma(
            person=self, action=action, product=product,
            distribution=distribution, sourcepackagename=sourcepackagename,
            datecreated=datecreated)
        notify(KarmaAssignedEvent(self, karma))
        return karma

    def latestKarma(self, quantity=25):
        """See `IPerson`."""
        return Karma.selectBy(person=self,
            orderBy='-datecreated')[:quantity]

    # This is to cache TeamParticipation information as that's used tons of
    # times in each request.
    _inTeam_cache = None

    def inTeam(self, team):
        """See `IPerson`."""
        if team is None:
            return False

        # Translate the team name to an ITeam if we were passed a team.
        if isinstance(team, (str, unicode)):
            team = PersonSet().getByName(team)
            if team is None:
                # No team, no membership.
                return False

        if self.id == team.id:
            # A team is always a member of itself.
            return True

        if not team.is_team:
            # It is possible that this team is really a user since teams
            # are users are often interchangable.
            return False

        if self._inTeam_cache is None:
            # Initialize cache
            self._inTeam_cache = {}
        else:
            # Retun from cache or fall through.
            try:
                return self._inTeam_cache[team.id]
            except KeyError:
                pass

        tp = TeamParticipation.selectOneBy(team=team, person=self)
        in_team = tp is not None
        self._inTeam_cache[team.id] = in_team
        return in_team

    def hasParticipationEntryFor(self, team):
        """See `IPerson`."""
        return bool(TeamParticipation.selectOneBy(person=self, team=team))

    def leave(self, team):
        """See `IPerson`."""
        assert not ITeam.providedBy(self)
        self.retractTeamMembership(team, self)

    def join(self, team, requester=None, may_subscribe_to_list=True):
        """See `IPerson`."""
        if self in team.activemembers:
            return

        if requester is None:
            assert not self.is_team, (
                "You need to specify a reviewer when a team joins another.")
            requester = self

        proposed = TeamMembershipStatus.PROPOSED
        approved = TeamMembershipStatus.APPROVED

        if team.subscriptionpolicy == TeamSubscriptionPolicy.RESTRICTED:
            raise JoinNotAllowed("This is a restricted team")
        elif (team.subscriptionpolicy == TeamSubscriptionPolicy.MODERATED
            or team.subscriptionpolicy == TeamSubscriptionPolicy.DELEGATED):
            status = proposed
        elif team.subscriptionpolicy == TeamSubscriptionPolicy.OPEN:
            status = approved
        else:
            raise AssertionError(
                "Unknown subscription policy: %s" % team.subscriptionpolicy)

        # XXX Edwin Grubbs 2007-12-14 bug=117980
        # removeSecurityProxy won't be necessary after addMember()
        # is configured to call a method on the new member, so the
        # security configuration will verify that the logged in user
        # has the right permission to add the specified person to the team.
        naked_team = removeSecurityProxy(team)
        naked_team.addMember(
            self, reviewer=requester, status=status,
            force_team_add=True,
            may_subscribe_to_list=may_subscribe_to_list)

    def clearInTeamCache(self):
        """See `IPerson`."""
        self._inTeam_cache = {}

    #
    # ITeam methods
    #
    @property
    def super_teams(self):
        """See `IPerson`."""
        query = """
            Person.id = TeamParticipation.team AND
            TeamParticipation.person = %s AND
            TeamParticipation.team != %s
            """ % sqlvalues(self.id, self.id)
        return Person.select(query, clauseTables=['TeamParticipation'])

    @property
    def sub_teams(self):
        """See `IPerson`."""
        query = """
            Person.id = TeamParticipation.person AND
            TeamParticipation.team = %s AND
            TeamParticipation.person != %s AND
            Person.teamowner IS NOT NULL
            """ % sqlvalues(self.id, self.id)
        return Person.select(query, clauseTables=['TeamParticipation'])

    def getTeamAdminsEmailAddresses(self):
        """See `IPerson`."""
        assert self.is_team
        to_addrs = set()
        for admin in self.adminmembers:
            to_addrs.update(get_contact_email_addresses(admin))
        return sorted(to_addrs)

    def addMember(self, person, reviewer, comment=None, force_team_add=False,
                  status=TeamMembershipStatus.APPROVED,
                  may_subscribe_to_list=True):
        """See `IPerson`."""
        assert self.is_team, "You cannot add members to a person."
        assert status in [TeamMembershipStatus.APPROVED,
                          TeamMembershipStatus.PROPOSED,
                          TeamMembershipStatus.ADMIN], (
            "You can't add a member with this status: %s." % status.name)

        event = JoinTeamEvent
        tm = TeamMembership.selectOneBy(person=person, team=self)
        if tm is not None:
            if tm.status == TeamMembershipStatus.ADMIN or (
                tm.status == TeamMembershipStatus.APPROVED and status ==
                TeamMembershipStatus.PROPOSED):
                status = tm.status
        if person.is_team:
            assert not self.hasParticipationEntryFor(person), (
                "Team '%s' is a member of '%s'. As a consequence, '%s' can't "
                "be added as a member of '%s'"
                % (self.name, person.name, person.name, self.name))
            # By default, teams can only be invited as members, meaning that
            # one of the team's admins will have to accept the invitation
            # before the team is made a member. If force_team_add is True,
            # or the user is also an admin of the proposed member, then
            # we'll add a team as if it was a person.
            is_reviewer_admin_of_new_member = (
                person in reviewer.getAdministratedTeams())
            if not force_team_add and not is_reviewer_admin_of_new_member:
                if tm is None or tm.status not in (
                    TeamMembershipStatus.PROPOSED,
                    TeamMembershipStatus.APPROVED,
                    TeamMembershipStatus.ADMIN,
                    ):
                    status = TeamMembershipStatus.INVITED
                    event = TeamInvitationEvent
                else:
                    if tm.status == TeamMembershipStatus.PROPOSED:
                        status = TeamMembershipStatus.APPROVED
                    else:
                        status = tm.status

        status_changed = True
        expires = self.defaultexpirationdate
        if tm is None:
            tm = TeamMembershipSet().new(
                person, self, status, reviewer, dateexpires=expires,
                comment=comment)
            # Accessing the id attribute ensures that the team
            # creation has been flushed to the database.
            tm.id
            notify(event(person, self))
        else:
            # We can't use tm.setExpirationDate() here because the reviewer
            # here will be the member themselves when they join an OPEN team.
            tm.dateexpires = expires
            status_changed = tm.setStatus(status, reviewer, comment)

        if not person.is_team and may_subscribe_to_list:
            person.autoSubscribeToMailingList(self.mailing_list,
                                              requester=reviewer)
        return (status_changed, tm.status)

    # The three methods below are not in the IPerson interface because we want
    # to protect them with a launchpad.Edit permission. We could do that by
    # defining explicit permissions for all IPerson methods/attributes in
    # the zcml but that's far from optimal given the size of IPerson.
    def acceptInvitationToBeMemberOf(self, team, comment):
        """Accept an invitation to become a member of the given team.

        There must be a TeamMembership for this person and the given team with
        the INVITED status. The status of this TeamMembership will be changed
        to APPROVED.
        """
        tm = TeamMembership.selectOneBy(person=self, team=team)
        assert tm is not None
        assert tm.status == TeamMembershipStatus.INVITED
        tm.setStatus(
            TeamMembershipStatus.APPROVED, getUtility(ILaunchBag).user,
            comment=comment)

    def declineInvitationToBeMemberOf(self, team, comment):
        """Decline an invitation to become a member of the given team.

        There must be a TeamMembership for this person and the given team with
        the INVITED status. The status of this TeamMembership will be changed
        to INVITATION_DECLINED.
        """
        tm = TeamMembership.selectOneBy(person=self, team=team)
        assert tm is not None
        assert tm.status == TeamMembershipStatus.INVITED
        tm.setStatus(
            TeamMembershipStatus.INVITATION_DECLINED,
            getUtility(ILaunchBag).user, comment=comment)

    def retractTeamMembership(self, team, user, comment=None):
        """See `IPerson`"""
        # Include PROPOSED and INVITED so that teams can retract mistakes
        # without involving members of the other team.
        active_and_transitioning = {
            TeamMembershipStatus.ADMIN: TeamMembershipStatus.DEACTIVATED,
            TeamMembershipStatus.APPROVED: TeamMembershipStatus.DEACTIVATED,
            TeamMembershipStatus.PROPOSED: TeamMembershipStatus.DECLINED,
            TeamMembershipStatus.INVITED:
                TeamMembershipStatus.INVITATION_DECLINED,
            }
        constraints = And(
            TeamMembership.personID == self.id,
            TeamMembership.teamID == team.id,
            TeamMembership.status.is_in(active_and_transitioning.keys()))
        tm = Store.of(self).find(TeamMembership, constraints).one()
        if tm is not None:
            # Flush the cache used by the inTeam method.
            self._inTeam_cache = {}
            new_status = active_and_transitioning[tm.status]
            tm.setStatus(new_status, user, comment=comment)

    def renewTeamMembership(self, team):
        """Renew the TeamMembership for this person on the given team.

        The given team's renewal policy must be ONDEMAND and the membership
        must be active (APPROVED or ADMIN) and set to expire in less than
        DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT days.
        """
        tm = TeamMembership.selectOneBy(person=self, team=team)
        assert tm.canBeRenewedByMember(), (
            "This membership can't be renewed by the member himself.")

        assert (team.defaultrenewalperiod is not None
                and team.defaultrenewalperiod > 0), (
            'Teams with a renewal policy of ONDEMAND must specify '
            'a default renewal period greater than 0.')
        # Keep the same status, change the expiration date and send a
        # notification explaining the membership has been renewed.
        tm.dateexpires += timedelta(days=team.defaultrenewalperiod)
        tm.sendSelfRenewalNotification()

    def setMembershipData(self, person, status, reviewer, expires=None,
                          comment=None):
        """See `IPerson`."""
        tm = TeamMembership.selectOneBy(person=person, team=self)
        assert tm is not None
        tm.setExpirationDate(expires, reviewer)
        tm.setStatus(status, reviewer, comment=comment)

    @cachedproperty
    def administrated_teams(self):
        return list(self.getAdministratedTeams())

    def getAdministratedTeams(self):
        """See `IPerson`."""
        owner_of_teams = Person.select('''
            Person.teamowner = TeamParticipation.team
            AND TeamParticipation.person = %s
            AND Person.merged IS NULL
            ''' % sqlvalues(self),
            clauseTables=['TeamParticipation'])
        admin_of_teams = Person.select('''
            Person.id = TeamMembership.team
            AND TeamMembership.status = %(admin)s
            AND TeamMembership.person = TeamParticipation.team
            AND TeamParticipation.person = %(person)s
            AND Person.merged IS NULL
            ''' % sqlvalues(person=self, admin=TeamMembershipStatus.ADMIN),
            clauseTables=['TeamParticipation', 'TeamMembership'])
        return admin_of_teams.union(
            owner_of_teams, orderBy=self._sortingColumnsForSetOperations)

    def getDirectAdministrators(self):
        """See `IPerson`."""
        assert self.is_team, 'Method should only be called on a team.'
        owner = Person.select("id = %s" % sqlvalues(self.teamowner))
        return self.adminmembers.union(
            owner, orderBy=self._sortingColumnsForSetOperations)

    def getMembersByStatus(self, status, orderBy=None):
        """See `IPerson`."""
        query = ("TeamMembership.team = %s AND TeamMembership.status = %s "
                 "AND TeamMembership.person = Person.id" %
                 sqlvalues(self.id, status))
        if orderBy is None:
            orderBy = Person.sortingColumns
        return Person.select(
            query, clauseTables=['TeamMembership'], orderBy=orderBy)

    def _getEmailsByStatus(self, status):
        return Store.of(self).find(
            EmailAddress,
            EmailAddress.personID == self.id,
            EmailAddress.status == status)

    def subscriptionPolicyMustBeClosed(self):
        """See `ITeam`"""
        assert self.is_team, "This method must only be used for teams."

        # Does this team own or is the security contact for any pillars.
        roles = IPersonRoles(self)
        if roles.isPillarOwner() or roles.isSecurityContact():
            return True

        # Does this team have any PPAs
        for ppa in self.ppas:
            if ppa.status != ArchiveStatus.DELETED:
                return True

        # Does this team have any super teams that are closed.
        for team in self.super_teams:
            if team.subscriptionpolicy in CLOSED_TEAM_POLICY:
                return True

        # Does this team subscribe or is assigned to any private bugs.
        # Circular imports.
        from lp.bugs.model.bug import Bug
        from lp.bugs.model.bugsubscription import BugSubscription
        from lp.bugs.model.bugtask import BugTask
        # The team cannot be open if it is subscribed to or assigned to
        # private bugs.
        private_bugs_involved = IStore(Bug).execute(Union(
            Select(
                Bug.id,
                tables=(
                    Bug,
                    Join(BugSubscription, BugSubscription.bug_id == Bug.id)),
                where=And(
                    Bug.private == True,
                    BugSubscription.person_id == self.id)),
            Select(
                Bug.id,
                tables=(
                    Bug,
                    Join(BugTask, BugTask.bugID == Bug.id)),
                where=And(Bug.private == True, BugTask.assignee == self.id)),
            limit=1))
        if private_bugs_involved.rowcount:
            return True

        # We made it here, so let's return False.
        return False

    def subscriptionPolicyMustBeOpen(self):
        """See `ITeam`"""
        assert self.is_team, "This method must only be used for teams."

        # The team must be open if any of it's members are open.
        for member in self.activemembers:
            if member.subscriptionpolicy in OPEN_TEAM_POLICY:
                return True
        return False

    @property
    def wiki_names(self):
        """See `IPerson`."""
        result = Store.of(self).find(WikiName, WikiName.person == self.id)
        return result.order_by(WikiName.wiki, WikiName.wikiname)

    @property
    def title(self):
        """See `IPerson`."""
        return self.displayname

    @property
    def allmembers(self):
        """See `IPerson`."""
        return self._members(direct=False)

    @property
    def all_members_prepopulated(self):
        """See `IPerson`."""
        return self._members(direct=False, need_karma=True,
            need_ubuntu_coc=True, need_location=True, need_archive=True,
            need_preferred_email=True, need_validity=True)

    @staticmethod
    def _validity_queries(person_table=None):
        """Return storm expressions and a decorator function for validity.

        Preloading validity implies preloading preferred email addresses.

        :param person_table: The person table to join to. Only supply if
            ClassAliases are in use.
        :return: A dict with four keys joins, tables, conditions, decorators

        * joins are additional joins to use. e.g. [LeftJoin,LeftJoin]
        * tables are tables to use e.g. [EmailAddress, Account]
        * decorators are callbacks to call for each row. Each decorator takes
        (Person, column) where column is the column in the result set for that
        decorators type.
        """
        if person_table is None:
            person_table = Person
            email_table = EmailAddress
            account_table = Account
        else:
            email_table = ClassAlias(EmailAddress)
            account_table = ClassAlias(Account)
        origins = []
        columns = []
        decorators = []
        # Teams don't have email, so a left join
        origins.append(
            LeftJoin(email_table, And(
                email_table.personID == person_table.id,
                email_table.status == EmailAddressStatus.PREFERRED)))
        columns.append(email_table)
        origins.append(
            LeftJoin(account_table, And(
                person_table.accountID == account_table.id,
                account_table.status == AccountStatus.ACTIVE)))
        columns.append(account_table)

        def handleemail(person, column):
            #-- preferred email caching
            if not person:
                return
            email = column
            get_property_cache(person).preferredemail = email

        decorators.append(handleemail)

        def handleaccount(person, column):
            #-- validity caching
            if not person:
                return
            # valid if:
            valid = (
                # -- valid account found
                column is not None
                # -- preferred email found
                and person.preferredemail is not None)
            get_property_cache(person).is_valid_person = valid
        decorators.append(handleaccount)
        return dict(
            joins=origins,
            tables=columns,
            decorators=decorators)

    def _members(self, direct, need_karma=False, need_ubuntu_coc=False,
        need_location=False, need_archive=False, need_preferred_email=False,
        need_validity=False):
        """Lookup all members of the team with optional precaching.

        :param direct: If True only direct members are returned.
        :param need_karma: The karma attribute will be cached.
        :param need_ubuntu_coc: The is_ubuntu_coc_signer attribute will be
            cached.
        :param need_location: The location attribute will be cached.
        :param need_archive: The archive attribute will be cached.
        :param need_preferred_email: The preferred email attribute will be
            cached.
        :param need_validity: The is_valid attribute will be cached.
        """
        # TODO: consolidate this with getMembersWithPreferredEmails.
        #       The difference between the two is that
        #       getMembersWithPreferredEmails includes self, which is arguably
        #       wrong, but perhaps deliberate.
        origin = [Person]
        if not direct:
            origin.append(Join(
                TeamParticipation, TeamParticipation.person == Person.id))
            conditions = And(
                # Members of this team,
                TeamParticipation.team == self.id,
                # But not the team itself.
                TeamParticipation.person != self.id)
        else:
            origin.append(Join(
                TeamMembership, TeamMembership.personID == Person.id))
            conditions = And(
                # Membership in this team,
                TeamMembership.team == self.id,
                # And approved or admin status
                TeamMembership.status.is_in([
                    TeamMembershipStatus.APPROVED,
                    TeamMembershipStatus.ADMIN]))
        # Use a PersonSet object that is not security proxied to allow
        # manipulation of the object.
        person_set = PersonSet()
        return person_set._getPrecachedPersons(
            origin, conditions, store=Store.of(self),
            need_karma=need_karma,
            need_ubuntu_coc=need_ubuntu_coc,
            need_location=need_location,
            need_archive=need_archive,
            need_preferred_email=need_preferred_email,
            need_validity=need_validity)

    def _getMembersWithPreferredEmails(self):
        """Helper method for public getMembersWithPreferredEmails.

        We can't return the preferred email address directly to the
        browser code, since it would circumvent the security restrictions
        on accessing person.preferredemail.
        """
        store = Store.of(self)
        origin = [
            Person,
            Join(TeamParticipation, TeamParticipation.person == Person.id),
            Join(EmailAddress, EmailAddress.person == Person.id),
            ]
        conditions = And(
            TeamParticipation.team == self.id,
            EmailAddress.status == EmailAddressStatus.PREFERRED)
        return store.using(*origin).find((Person, EmailAddress), conditions)

    def getMembersWithPreferredEmails(self):
        """See `IPerson`."""
        result = self._getMembersWithPreferredEmails()
        person_list = []
        for person, email in result:
            get_property_cache(person).preferredemail = email
            person_list.append(person)
        return person_list

    def getMembersWithPreferredEmailsCount(self):
        """See `IPerson`."""
        result = self._getMembersWithPreferredEmails()
        return result.count()

    @property
    def all_member_count(self):
        """See `IPerson`."""
        return self.allmembers.count()

    @property
    def invited_members(self):
        """See `IPerson`."""
        return self.getMembersByStatus(TeamMembershipStatus.INVITED)

    @property
    def invited_member_count(self):
        """See `IPerson`."""
        return self.invited_members.count()

    @property
    def deactivatedmembers(self):
        """See `IPerson`."""
        return self.getMembersByStatus(TeamMembershipStatus.DEACTIVATED)

    @property
    def deactivated_member_count(self):
        """See `IPerson`."""
        return self.deactivatedmembers.count()

    @property
    def expiredmembers(self):
        """See `IPerson`."""
        return self.getMembersByStatus(TeamMembershipStatus.EXPIRED)

    @property
    def expired_member_count(self):
        """See `IPerson`."""
        return self.expiredmembers.count()

    @property
    def proposedmembers(self):
        """See `IPerson`."""
        return self.getMembersByStatus(TeamMembershipStatus.PROPOSED)

    @property
    def proposed_member_count(self):
        """See `IPerson`."""
        return self.proposedmembers.count()

    @property
    def adminmembers(self):
        """See `IPerson`."""
        return self.getMembersByStatus(TeamMembershipStatus.ADMIN)

    @property
    def approvedmembers(self):
        """See `IPerson`."""
        return self.getMembersByStatus(TeamMembershipStatus.APPROVED)

    @property
    def activemembers(self):
        """See `IPerson`."""
        return self.approvedmembers.union(
            self.adminmembers, orderBy=self._sortingColumnsForSetOperations)

    @property
    def api_activemembers(self):
        """See `IPerson`."""
        return self._members(direct=True, need_karma=True,
            need_ubuntu_coc=True, need_location=True, need_archive=True,
            need_preferred_email=True, need_validity=True)

    @property
    def active_member_count(self):
        """See `IPerson`."""
        return self.activemembers.count()

    @property
    def inactivemembers(self):
        """See `IPerson`."""
        return self.expiredmembers.union(
            self.deactivatedmembers,
            orderBy=self._sortingColumnsForSetOperations)

    @property
    def inactive_member_count(self):
        """See `IPerson`."""
        return self.inactivemembers.count()

    @property
    def pendingmembers(self):
        """See `IPerson`."""
        return self.proposedmembers.union(
            self.invited_members,
            orderBy=self._sortingColumnsForSetOperations)

    @property
    def team_memberships(self):
        """See `IPerson`."""
        Team = ClassAlias(Person, "Team")
        store = Store.of(self)
        # Join on team to sort by team names. Upper is used in the sort so
        # sorting works as is user expected, e.g. (A b C) not (A C b).
        return store.find(TeamMembership,
            And(TeamMembership.personID == self.id,
                TeamMembership.teamID == Team.id,
                TeamMembership.status.is_in([
                    TeamMembershipStatus.APPROVED,
                    TeamMembershipStatus.ADMIN,
                    ]))).order_by(
                        Upper(Team.displayname),
                        Upper(Team.name))

    def _getMappedParticipantsLocations(self, limit=None):
        """See `IPersonViewRestricted`."""
        return PersonLocation.select("""
            PersonLocation.person = TeamParticipation.person AND
            TeamParticipation.team = %s AND
            -- We only need to check for a latitude here because there's a DB
            -- constraint which ensures they are both set or unset.
            PersonLocation.latitude IS NOT NULL AND
            PersonLocation.visible IS TRUE AND
            Person.id = PersonLocation.person AND
            Person.teamowner IS NULL
            """ % sqlvalues(self.id),
            clauseTables=['TeamParticipation', 'Person'],
            prejoins=['person', ], limit=limit)

    def getMappedParticipants(self, limit=None):
        """See `IPersonViewRestricted`."""
        # Pre-cache this location against its person.  Since we'll always
        # iterate over all persons returned by this property (to build the map
        # of team members), it becomes more important to cache their locations
        # than to return a lazy SelectResults (or similar) object that only
        # fetches the rows when they're needed.
        locations = self._getMappedParticipantsLocations(limit=limit)
        for location in locations:
            get_property_cache(location.person).location = location
        participants = set(location.person for location in locations)
        # Cache the ValidPersonCache query for all mapped participants.
        if len(participants) > 0:
            sql = "id IN (%s)" % ",".join(sqlvalues(*participants))
            list(ValidPersonCache.select(sql))
        getUtility(IPersonSet).cacheBrandingForPeople(participants)
        return list(participants)

    @property
    def mapped_participants_count(self):
        """See `IPersonViewRestricted`."""
        return self._getMappedParticipantsLocations().count()

    def getMappedParticipantsBounds(self, limit=None):
        """See `IPersonViewRestricted`."""
        max_lat = -90.0
        min_lat = 90.0
        max_lng = -180.0
        min_lng = 180.0
        locations = self._getMappedParticipantsLocations(limit)
        if self.mapped_participants_count == 0:
            raise AssertionError(
                'This method cannot be called when '
                'mapped_participants_count == 0.')
        latitudes = sorted(location.latitude for location in locations)
        if latitudes[-1] > max_lat:
            max_lat = latitudes[-1]
        if latitudes[0] < min_lat:
            min_lat = latitudes[0]
        longitudes = sorted(location.longitude for location in locations)
        if longitudes[-1] > max_lng:
            max_lng = longitudes[-1]
        if longitudes[0] < min_lng:
            min_lng = longitudes[0]
        center_lat = (max_lat + min_lat) / 2.0
        center_lng = (max_lng + min_lng) / 2.0
        return dict(
            min_lat=min_lat, min_lng=min_lng, max_lat=max_lat,
            max_lng=max_lng, center_lat=center_lat, center_lng=center_lng)

    @property
    def unmapped_participants(self):
        """See `IPersonViewRestricted`."""
        return Person.select("""
            Person.id = TeamParticipation.person AND
            TeamParticipation.team = %s AND
            TeamParticipation.person NOT IN (
                SELECT PersonLocation.person
                FROM PersonLocation INNER JOIN TeamParticipation ON
                     PersonLocation.person = TeamParticipation.person
                WHERE TeamParticipation.team = %s AND
                      PersonLocation.latitude IS NOT NULL) AND
            Person.teamowner IS NULL
            """ % sqlvalues(self.id, self.id),
            clauseTables=['TeamParticipation'])

    @property
    def unmapped_participants_count(self):
        """See `IPersonViewRestricted`."""
        return self.unmapped_participants.count()

    @property
    def open_membership_invitations(self):
        """See `IPerson`."""
        return TeamMembership.select("""
            TeamMembership.person = %s AND status = %s
            AND Person.id = TeamMembership.team
            """ % sqlvalues(self.id, TeamMembershipStatus.INVITED),
            clauseTables=['Person'],
            orderBy=Person.sortingColumns)

    # XXX: salgado, 2009-04-16: This should be called just deactivate(),
    # because it not only deactivates this person's account but also the
    # person.
    def deactivateAccount(self, comment):
        """See `IPersonSpecialRestricted`."""
        if not self.is_valid_person:
            raise AssertionError(
                "You can only deactivate an account of a valid person.")

        for membership in self.team_memberships:
            self.leave(membership.team)

        # Deactivate CoC signatures, invalidate email addresses, unassign bug
        # tasks and specs and reassign pillars and teams.
        for coc in self.signedcocs:
            coc.active = False
        for email in self.validatedemails:
            email = IMasterObject(email)
            email.status = EmailAddressStatus.NEW
        params = BugTaskSearchParams(self, assignee=self)
        for bug_task in self.searchTasks(params):
            # If the bugtask has a conjoined master we don't try to
            # update it, since we will update it correctly when we
            # update its conjoined master (see bug 193983).
            if bug_task.conjoined_master is not None:
                continue

            # XXX flacoste 2007-11-26 bug=164635 The comparison using id in
            # the assert below works around a nasty intermittent failure.
            assert bug_task.assignee.id == self.id, (
               "Bugtask %s assignee isn't the one expected: %s != %s" % (
                    bug_task.id, bug_task.assignee.name, self.name))
            bug_task.transitionToAssignee(None)
        for spec in self.assigned_specs:
            spec.assignee = None
        registry_experts = getUtility(ILaunchpadCelebrities).registry_experts
        for team in Person.selectBy(teamowner=self):
            team.teamowner = registry_experts
        for pillar_name in self.getOwnedOrDrivenPillars():
            pillar = pillar_name.pillar
            # XXX flacoste 2007-11-26 bug=164635 The comparison using id below
            # works around a nasty intermittent failure.
            changed = False
            if pillar.owner.id == self.id:
                pillar.owner = registry_experts
                changed = True
            if pillar.driver is not None and pillar.driver.id == self.id:
                pillar.driver = registry_experts
                changed = True

            if not changed:
                # Since we removed the person from all teams, something is
                # seriously broken here.
                raise AssertionError(
                    "%s was expected to be owner or driver of %s" %
                    (self.name, pillar.name))

        # Nuke all subscriptions of this person.
        removals = [
            ('BranchSubscription', 'person'),
            ('BugSubscription', 'person'),
            ('QuestionSubscription', 'person'),
            ('SpecificationSubscription', 'person'),
            ('AnswerContact', 'person')]
        cur = cursor()
        for table, person_id_column in removals:
            cur.execute("DELETE FROM %s WHERE %s=%d"
                        % (table, person_id_column, self.id))

        # Update the account's status, preferred email and name.
        self.account_status = AccountStatus.DEACTIVATED
        self.account_status_comment = comment
        IMasterObject(self.preferredemail).status = EmailAddressStatus.NEW
        del get_property_cache(self).preferredemail
        base_new_name = self.name + '-deactivatedaccount'
        self.name = self._ensureNewName(base_new_name)

    def _ensureNewName(self, base_new_name):
        """Return a unique name."""
        new_name = base_new_name
        count = 1
        while Person.selectOneBy(name=new_name) is not None:
            new_name = base_new_name + str(count)
            count += 1
        return new_name

    @property
    def private(self):
        """See `IPerson`."""
        if not self.is_team:
            return False
        elif self.visibility == PersonVisibility.PUBLIC:
            return False
        else:
            return True

    @property
    def is_merge_pending(self):
        """See `IPublicPerson`."""
        return not getUtility(
            IPersonMergeJobSource).find(from_person=self).is_empty()

    def visibilityConsistencyWarning(self, new_value):
        """Warning used when changing the team's visibility.

        A private-membership team cannot be connected to other
        objects, since it may be possible to infer the membership.
        """
        if self._visibility_warning_cache != self._visibility_warning_marker:
            return self._visibility_warning_cache

        cur = cursor()
        references = list(postgresql.listReferences(cur, 'person', 'id'))
        # These tables will be skipped since they do not risk leaking
        # team membership information, except StructuralSubscription
        # which will be checked further down to provide a clearer warning.
        # Note all of the table names and columns must be all lowercase.
        skip = set([
            ('emailaddress', 'person'),
            ('gpgkey', 'owner'),
            ('ircid', 'person'),
            ('jabberid', 'person'),
            ('karma', 'person'),
            ('karmacache', 'person'),
            ('karmatotalcache', 'person'),
            ('logintoken', 'requester'),
            ('personlanguage', 'person'),
            ('personlocation', 'person'),
            ('personsettings', 'person'),
            ('persontransferjob', 'minor_person'),
            ('persontransferjob', 'major_person'),
            ('signedcodeofconduct', 'owner'),
            ('sshkey', 'person'),
            ('structuralsubscription', 'subscriber'),
            ('teammembership', 'team'),
            ('teamparticipation', 'person'),
            ('teamparticipation', 'team'),
            # Skip mailing lists because if the mailing list is purged, it's
            # not a problem.  Do this check separately below.
            ('mailinglist', 'team'),
            ])

        # The following relationships are allowable for Private teams and
        # thus should be skipped.
        if new_value == PersonVisibility.PRIVATE:
            skip.update([('bugsubscription', 'person'),
                         ('bugtask', 'assignee'),
                         ('branch', 'owner'),
                         ('branchsubscription', 'person'),
                         ('branchvisibilitypolicy', 'team'),
                         ('archive', 'owner'),
                         ('archivesubscriber', 'subscriber'),
                         ])

        warnings = set()
        for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
            if (src_tab, src_col) in skip:
                continue
            cur.execute('SELECT 1 FROM %s WHERE %s=%d LIMIT 1'
                        % (src_tab, src_col, self.id))
            if cur.rowcount > 0:
                if src_tab[0] in 'aeiou':
                    article = 'an'
                else:
                    article = 'a'
                warnings.add('%s %s' % (article, src_tab))

        # Private teams may have structural subscription, so the following
        # test is not applied to them.
        if new_value != PersonVisibility.PRIVATE:
            # Add warnings for subscriptions in StructuralSubscription table
            # describing which kind of object is being subscribed to.
            cur.execute("""
                SELECT
                    count(product) AS product_count,
                    count(productseries) AS productseries_count,
                    count(project) AS project_count,
                    count(milestone) AS milestone_count,
                    count(distribution) AS distribution_count,
                    count(distroseries) AS distroseries_count,
                    count(sourcepackagename) AS sourcepackagename_count
                FROM StructuralSubscription
                WHERE subscriber=%d LIMIT 1
                """ % self.id)

            row = cur.fetchone()
            for count, warning in zip(row, [
                    'a project subscriber',
                    'a project series subscriber',
                    'a project subscriber',
                    'a milestone subscriber',
                    'a distribution subscriber',
                    'a distroseries subscriber',
                    'a source package subscriber']):
                if count > 0:
                    warnings.add(warning)

        # Non-purged mailing list check for transitioning to or from PUBLIC.
        if PersonVisibility.PUBLIC in [self.visibility, new_value]:
            mailing_list = getUtility(IMailingListSet).get(self.name)
            if (mailing_list is not None and
                mailing_list.status != MailingListStatus.PURGED):
                warnings.add('a mailing list')

        # Compose warning string.
        warnings = sorted(warnings)

        if len(warnings) == 0:
            self._visibility_warning_cache = None
        else:
            if len(warnings) == 1:
                message = warnings[0]
            else:
                message = '%s and %s' % (
                    ', '.join(warnings[:-1]),
                    warnings[-1])
            self._visibility_warning_cache = (
                'This team cannot be converted to %s since it is '
                'referenced by %s.' % (new_value, message))
        return self._visibility_warning_cache

    @property
    def member_memberships(self):
        """See `IPerson`."""
        return self._getMembershipsByStatuses(
            [TeamMembershipStatus.ADMIN, TeamMembershipStatus.APPROVED])

    def getInactiveMemberships(self):
        """See `IPerson`."""
        return self._getMembershipsByStatuses(
            [TeamMembershipStatus.EXPIRED, TeamMembershipStatus.DEACTIVATED])

    def getInvitedMemberships(self):
        """See `IPerson`."""
        return self._getMembershipsByStatuses([TeamMembershipStatus.INVITED])

    def getProposedMemberships(self):
        """See `IPerson`."""
        return self._getMembershipsByStatuses([TeamMembershipStatus.PROPOSED])

    def _getMembershipsByStatuses(self, statuses):
        """All `ITeamMembership`s in any given status for this team's members.

        :param statuses: A list of `TeamMembershipStatus` items.

        If called on an person rather than a team, this will obviously return
        no memberships at all.
        """
        statuses = ",".join(quote(status) for status in statuses)
        # We don't want to escape 'statuses' so we can't easily use
        # sqlvalues() on the query below.
        query = """
            TeamMembership.status IN (%s)
            AND Person.id = TeamMembership.person
            AND TeamMembership.team = %d
            """ % (statuses, self.id)
        return TeamMembership.select(
            query, clauseTables=['Person'],
            prejoinClauseTables=['Person'],
            orderBy=Person.sortingColumns)

    def getLatestApprovedMembershipsForPerson(self, limit=5):
        """See `IPerson`."""
        result = self.team_memberships
        result = result.order_by(
            Desc(TeamMembership.datejoined),
            Desc(TeamMembership.id))
        return result[:limit]

    def getPathsToTeams(self):
        """See `Iperson`."""
        # Get all of the teams this person participates in.
        teams = list(self.teams_participated_in)

        # For cases where self is a team, we don't need self as a team
        # participated in.
        teams = [team for team in teams if team is not self]

        # Get all of the memberships for any of the teams this person is
        # a participant of. This must be ordered by date and id because
        # because the graph of the results will create needs to contain
        # the oldest path information to be consistent with results from
        # IPerson.findPathToTeam.
        store = Store.of(self)
        all_direct_memberships = store.find(TeamMembership,
            And(
                TeamMembership.personID.is_in(
                    [team.id for team in teams] + [self.id]),
                TeamMembership.teamID != self.id,
                TeamMembership.status.is_in([
                    TeamMembershipStatus.APPROVED,
                    TeamMembershipStatus.ADMIN,
                    ]))).order_by(
                        Desc(TeamMembership.datejoined),
                        Desc(TeamMembership.id))
        # Cast the results to list now, because they will be iterated over
        # several times.
        all_direct_memberships = list(all_direct_memberships)

        # Pull out the memberships directly used by this person.
        user_memberships = [
            membership for membership in
            all_direct_memberships
            if membership.person == self]

        all_direct_memberships = [
            (membership.team, membership.person) for membership in
            all_direct_memberships]

        # Create a graph from the edges provided by the other data sets.
        graph = dict(all_direct_memberships)

        # Build the teams paths from that graph.
        paths = {}
        for team in teams:
            path = [team]
            step = team
            while path[-1] != self:
                step = graph[step]
                path.append(step)
            paths[team] = path
        return (paths, user_memberships)

    @property
    def teams_participated_in(self):
        """See `IPerson`."""
        return Person.select("""
            Person.id = TeamParticipation.team
            AND TeamParticipation.person = %s
            AND Person.teamowner IS NOT NULL
            """ % sqlvalues(self.id),
            clauseTables=['TeamParticipation'],
            orderBy=Person.sortingColumns)

    @property
    def teams_indirectly_participated_in(self):
        """See `IPerson`."""
        Team = ClassAlias(Person, "Team")
        store = Store.of(self)
        origin = [
            Team,
            Join(TeamParticipation, Team.id == TeamParticipation.teamID),
            LeftJoin(TeamMembership,
                And(TeamMembership.person == self.id,
                    TeamMembership.teamID == TeamParticipation.teamID,
                    TeamMembership.status.is_in([
                        TeamMembershipStatus.APPROVED,
                        TeamMembershipStatus.ADMIN])))]
        find_objects = (Team)
        return store.using(*origin).find(find_objects,
            And(
                TeamParticipation.person == self.id,
                TeamParticipation.person != TeamParticipation.teamID,
                TeamMembership.id == None))

    @property
    def teams_with_icons(self):
        """See `IPerson`."""
        return Person.select("""
            Person.id = TeamParticipation.team
            AND TeamParticipation.person = %s
            AND Person.teamowner IS NOT NULL
            AND Person.icon IS NOT NULL
            AND TeamParticipation.team != %s
            """ % sqlvalues(self.id, self.id),
            clauseTables=['TeamParticipation'],
            orderBy=Person.sortingColumns)

    @property
    def defaultexpirationdate(self):
        """See `IPerson`."""
        days = self.defaultmembershipperiod
        if days:
            return datetime.now(pytz.timezone('UTC')) + timedelta(days)
        else:
            return None

    @property
    def defaultrenewedexpirationdate(self):
        """See `IPerson`."""
        days = self.defaultrenewalperiod
        if days:
            return datetime.now(pytz.timezone('UTC')) + timedelta(days)
        else:
            return None

    def reactivate(self, comment, password, preferred_email):
        """See `IPersonSpecialRestricted`."""
        account = IMasterObject(self.account)
        account.reactivate(comment, password, preferred_email)
        if '-deactivatedaccount' in self.name:
            # The name was changed by deactivateAccount(). Restore the
            # name, but we must ensure it does not conflict with a current
            # user.
            name_parts = self.name.split('-deactivatedaccount')
            base_new_name = name_parts[0]
            self.name = self._ensureNewName(base_new_name)

    def validateAndEnsurePreferredEmail(self, email):
        """See `IPerson`."""
        email = IMasterObject(email)
        assert not self.is_team, "This method must not be used for teams."
        if not IEmailAddress.providedBy(email):
            raise TypeError(
                "Any person's email address must provide the IEmailAddress "
                "interface. %s doesn't." % email)
        # XXX Steve Alexander 2005-07-05:
        # This is here because of an SQLobject comparison oddity.
        assert email.personID == self.id, 'Wrong person! %r, %r' % (
            email.personID, self.id)

        # We need the preferred email address. This method is called
        # recursively, however, and the email address may have just been
        # created. So we have to explicitly pull it from the master store
        # until we rewrite this 'icky mess.
        preferred_email = IMasterStore(EmailAddress).find(
            EmailAddress,
            EmailAddress.personID == self.id,
            EmailAddress.status == EmailAddressStatus.PREFERRED).one()

        # This email is already validated and is this person's preferred
        # email, so we have nothing to do.
        if preferred_email == email:
            return

        if preferred_email is None:
            # This branch will be executed only in the first time a person
            # uses Launchpad. Either when creating a new account or when
            # resetting the password of an automatically created one.
            self.setPreferredEmail(email)
        else:
            email.status = EmailAddressStatus.VALIDATED

    def setContactAddress(self, email):
        """See `IPerson`."""
        assert self.is_team, "This method must be used only for teams."

        if email is None:
            self._unsetPreferredEmail()
        else:
            self._setPreferredEmail(email)
        # A team can have up to two addresses, the preferred one and one used
        # by the team mailing list.
        if (self.mailing_list is not None
            and self.mailing_list.status != MailingListStatus.PURGED):
            mailing_list_email = getUtility(IEmailAddressSet).getByEmail(
                self.mailing_list.address)
            if mailing_list_email is not None:
                mailing_list_email = IMasterObject(mailing_list_email)
        else:
            mailing_list_email = None
        all_addresses = IMasterStore(self).find(
            EmailAddress, EmailAddress.personID == self.id)
        for address in all_addresses:
            # Delete all email addresses that are not the preferred email
            # address, or the team's email address. If this method was called
            # with None, and there is no mailing list, then this condidition
            # is (None, None), causing all email addresses to be deleted.
            if address not in (email, mailing_list_email):
                address.destroySelf()

    def _unsetPreferredEmail(self):
        """Change the preferred email address to VALIDATED."""
        email_address = IMasterStore(EmailAddress).find(
            EmailAddress, personID=self.id,
            status=EmailAddressStatus.PREFERRED).one()
        if email_address is not None:
            email_address.status = EmailAddressStatus.VALIDATED
            email_address.syncUpdate()
        del get_property_cache(self).preferredemail

    def setPreferredEmail(self, email):
        """See `IPerson`."""
        assert not self.is_team, "This method must not be used for teams."
        if email is None:
            self._unsetPreferredEmail()
            return
        self._setPreferredEmail(email)

    def _setPreferredEmail(self, email):
        """Set this person's preferred email to the given email address.

        If the person already has an email address, then its status is
        changed to VALIDATED and the given one is made its preferred one.

        The given email address must implement IEmailAddress and be owned by
        this person.
        """
        if not IEmailAddress.providedBy(email):
            raise TypeError(
                "Any person's email address must provide the IEmailAddress "
                "interface. %s doesn't." % email)
        assert email.personID == self.id

        existing_preferred_email = IMasterStore(EmailAddress).find(
            EmailAddress, personID=self.id,
            status=EmailAddressStatus.PREFERRED).one()

        if existing_preferred_email is not None:
            existing_preferred_email.status = EmailAddressStatus.VALIDATED

        email = removeSecurityProxy(email)
        IMasterObject(email).status = EmailAddressStatus.PREFERRED
        IMasterObject(email).syncUpdate()

        # Now we update our cache of the preferredemail.
        get_property_cache(self).preferredemail = email

    @cachedproperty
    def preferredemail(self):
        """See `IPerson`."""
        emails = self._getEmailsByStatus(EmailAddressStatus.PREFERRED)
        # There can be only one preferred email for a given person at a
        # given time, and this constraint must be ensured in the DB, but
        # it's not a problem if we ensure this constraint here as well.
        emails = shortlist(emails)
        length = len(emails)
        assert length <= 1
        if length:
            return emails[0]
        else:
            return None

    @property
    def safe_email_or_blank(self):
        """See `IPerson`."""
        if (self.preferredemail is not None
            and not self.hide_email_addresses):
            return self.preferredemail.email
        else:
            return ''

    @property
    def validatedemails(self):
        """See `IPerson`."""
        return self._getEmailsByStatus(EmailAddressStatus.VALIDATED)

    @property
    def unvalidatedemails(self):
        """See `IPerson`."""
        query = """
            requester = %s
            AND (tokentype=%s OR tokentype=%s)
            AND date_consumed IS NULL
            """ % sqlvalues(self.id, LoginTokenType.VALIDATEEMAIL,
                            LoginTokenType.VALIDATETEAMEMAIL)
        return sorted(set(token.email for token in LoginToken.select(query)))

    @property
    def guessedemails(self):
        """See `IPerson`."""
        return self._getEmailsByStatus(EmailAddressStatus.NEW)

    @property
    def pending_gpg_keys(self):
        """See `IPerson`."""
        logintokenset = getUtility(ILoginTokenSet)
        return sorted(set(token.fingerprint for token in
                      logintokenset.getPendingGPGKeys(requesterid=self.id)))

    @property
    def inactive_gpg_keys(self):
        """See `IPerson`."""
        gpgkeyset = getUtility(IGPGKeySet)
        return gpgkeyset.getGPGKeys(ownerid=self.id, active=False)

    @property
    def gpg_keys(self):
        """See `IPerson`."""
        gpgkeyset = getUtility(IGPGKeySet)
        return gpgkeyset.getGPGKeys(ownerid=self.id)

    def getLatestMaintainedPackages(self):
        """See `IPerson`."""
        return self._latestSeriesQuery()

    def getLatestSynchronisedPublishings(self):
        """See `IPerson`."""
        query = """
            SourcePackagePublishingHistory.id IN (
                SELECT DISTINCT ON (spph.distroseries,
                                    spr.sourcepackagename)
                    spph.id
                FROM
                    SourcePackagePublishingHistory as spph, archive,
                    SourcePackagePublishingHistory as ancestor_spph,
                    SourcePackageRelease as spr
                WHERE
                    spph.sourcepackagerelease = spr.id AND
                    spph.creator = %(creator)s AND
                    spph.ancestor = ancestor_spph.id AND
                    spph.archive = archive.id AND
                    ancestor_spph.archive != spph.archive AND
                    archive.purpose = %(archive_purpose)s
                ORDER BY spph.distroseries,
                    spr.sourcepackagename,
                    spph.datecreated DESC,
                    spph.id DESC
            )
            """ % dict(
                   creator=quote(self.id),
                   archive_purpose=quote(ArchivePurpose.PRIMARY),
                   )

        return SourcePackagePublishingHistory.select(
            query,
            orderBy=['-SourcePackagePublishingHistory.datecreated',
                     '-SourcePackagePublishingHistory.id'],
            prejoins=['sourcepackagerelease', 'archive'])

    def getLatestUploadedButNotMaintainedPackages(self):
        """See `IPerson`."""
        return self._latestSeriesQuery(uploader_only=True)

    def getLatestUploadedPPAPackages(self):
        """See `IPerson`."""
        return self._latestSeriesQuery(
            uploader_only=True, ppa_only=True)

    def _latestSeriesQuery(self, uploader_only=False, ppa_only=False):
        """Return the sourcepackagereleases (SPRs) related to this person.

        :param uploader_only: controls if we are interested in SPRs where
            the person in question is only the uploader (creator) and not the
            maintainer (debian-syncs) if the `ppa_only` parameter is also
            False, or, if the flag is False, it returns all SPR maintained
            by this person.

        :param ppa_only: controls if we are interested only in source
            package releases targeted to any PPAs or, if False, sources
            targeted to primary archives.

        Active 'ppa_only' flag is usually associated with active
        'uploader_only' because there shouldn't be any sense of maintainership
        for packages uploaded to PPAs by someone else than the user himself.
        """
        clauses = ['sourcepackagerelease.upload_archive = archive.id']

        if uploader_only:
            clauses.append(
                'sourcepackagerelease.creator = %s' % quote(self.id))

        if ppa_only:
            # Source maintainer is irrelevant for PPA uploads.
            pass
        elif uploader_only:
            clauses.append(
                'sourcepackagerelease.maintainer != %s' % quote(self.id))
        else:
            clauses.append(
                'sourcepackagerelease.maintainer = %s' % quote(self.id))

        if ppa_only:
            clauses.append(
                'archive.purpose = %s' % quote(ArchivePurpose.PPA))
        else:
            clauses.append(
                'archive.purpose != %s' % quote(ArchivePurpose.PPA))

        query_clauses = " AND ".join(clauses)
        query = """
            SourcePackageRelease.id IN (
                SELECT DISTINCT ON (upload_distroseries,
                                    sourcepackagerelease.sourcepackagename,
                                    upload_archive)
                    sourcepackagerelease.id
                FROM sourcepackagerelease, archive,
                    sourcepackagepublishinghistory as spph
                WHERE
                    spph.sourcepackagerelease = sourcepackagerelease.id AND
                    spph.archive = archive.id AND
                    %(more_query_clauses)s
                ORDER BY upload_distroseries,
                    sourcepackagerelease.sourcepackagename,
                    upload_archive, dateuploaded DESC
              )
              """ % dict(more_query_clauses=query_clauses)

        rset = SourcePackageRelease.select(
            query,
            orderBy=['-SourcePackageRelease.dateuploaded',
                     'SourcePackageRelease.id'],
            prejoins=['sourcepackagename', 'maintainer', 'upload_archive'])

        return rset

    def createRecipe(self, name, description, recipe_text, distroseries,
                     registrant, daily_build_archive=None, build_daily=False):
        """See `IPerson`."""
        from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
        recipe = SourcePackageRecipe.new(
            registrant, self, name, recipe_text, description, distroseries,
            daily_build_archive, build_daily)
        Store.of(recipe).flush()
        return recipe

    def getRecipe(self, name):
        from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
        return Store.of(self).find(
            SourcePackageRecipe, SourcePackageRecipe.owner == self,
            SourcePackageRecipe.name == name).one()

    def getMergeQueue(self, name):
        from lp.code.model.branchmergequeue import BranchMergeQueue
        return Store.of(self).find(
            BranchMergeQueue,
            BranchMergeQueue.owner == self,
            BranchMergeQueue.name == unicode(name)).one()

    def isUploader(self, distribution):
        """See `IPerson`."""
        permissions = getUtility(IArchivePermissionSet).componentsForUploader(
            distribution.main_archive, self)
        return permissions.count() > 0

    @cachedproperty
    def is_ubuntu_coc_signer(self):
        """See `IPerson`."""
        # Also assigned to by self._members.
        store = Store.of(self)
        query = And(SignedCodeOfConduct.ownerID == self.id,
            Person._is_ubuntu_coc_signer_condition())
        return not store.find(SignedCodeOfConduct, query).is_empty()

    @staticmethod
    def _is_ubuntu_coc_signer_condition():
        """Generate a Storm Expr for determing the coc signing status."""
        sigset = getUtility(ISignedCodeOfConductSet)
        lastdate = sigset.getLastAcceptedDate()
        return And(SignedCodeOfConduct.active == True,
            SignedCodeOfConduct.datecreated >= lastdate)

    @property
    def activesignatures(self):
        """See `IPerson`."""
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        return sCoC_util.searchByUser(self.id)

    @property
    def inactivesignatures(self):
        """See `IPerson`."""
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        return sCoC_util.searchByUser(self.id, active=False)

    @cachedproperty
    def archive(self):
        """See `IPerson`."""
        return getUtility(IArchiveSet).getPPAOwnedByPerson(self)

    def getArchiveSubscriptionURLs(self, requester):
        """See `IPerson`."""
        agent = getUtility(ILaunchpadCelebrities).software_center_agent
        # If the requester isn't asking about themselves, and they aren't the
        # software center agent, deny them
        if requester.id != agent.id:
            if self.id != requester.id:
                raise Unauthorized
        subscriptions = getUtility(
            IArchiveSubscriberSet).getBySubscriberWithActiveToken(
                subscriber=self)
        return [token.archive_url for (subscription, token) in subscriptions
                if token is not None]

    def getArchiveSubscriptionURL(self, requester, archive):
        """See `IPerson`."""
        agent = getUtility(ILaunchpadCelebrities).software_center_agent
        # If the requester isn't asking about themselves, and they aren't the
        # software center agent, deny them
        if requester.id != agent.id:
            if self.id != requester.id:
                raise Unauthorized
        token = archive.getAuthToken(self)
        if token is None:
            token = archive.newAuthToken(self)
        return token.archive_url

    @property
    def ppas(self):
        """See `IPerson`."""
        return Archive.selectBy(
            owner=self, purpose=ArchivePurpose.PPA, orderBy='name')

    def getPPAByName(self, name):
        """See `IPerson`."""
        return getUtility(IArchiveSet).getPPAOwnedByPerson(self, name)

    def createPPA(self, name=None, displayname=None, description=None,
                  private=False):
        """See `IPerson`."""
        errors = Archive.validatePPA(self, name, private)
        if errors:
            raise PPACreationError(errors)
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        return getUtility(IArchiveSet).new(
            owner=self, purpose=ArchivePurpose.PPA,
            distribution=ubuntu, name=name, displayname=displayname,
            description=description, private=private)

    def isBugContributor(self, user=None):
        """See `IPerson`."""
        search_params = BugTaskSearchParams(user=user, assignee=self)
        bugtask_count = self.searchTasks(search_params).count()
        return bugtask_count > 0

    def isBugContributorInTarget(self, user=None, target=None):
        """See `IPerson`."""
        assert (IBugTarget.providedBy(target) or
                IProjectGroup.providedBy(target)), (
            "%s isn't a valid bug target." % target)
        search_params = BugTaskSearchParams(user=user, assignee=self)
        bugtask_count = target.searchTasks(search_params).count()
        return bugtask_count > 0

    @property
    def structural_subscriptions(self):
        """See `IPerson`."""
        return IStore(self).find(
            StructuralSubscription,
            StructuralSubscription.subscriberID == self.id).order_by(
                Desc(StructuralSubscription.date_created))

    def autoSubscribeToMailingList(self, mailinglist, requester=None):
        """See `IPerson`."""
        if mailinglist is None or not mailinglist.is_usable:
            return False

        if mailinglist.getSubscription(self):
            # We are already subscribed to the list.
            return False

        if self.preferredemail is None:
            return False

        if requester is None:
            # Assume the current user requested this action themselves.
            requester = self

        policy = self.mailing_list_auto_subscribe_policy

        if policy == MailingListAutoSubscribePolicy.ALWAYS:
            mailinglist.subscribe(self)
            return True
        elif (requester is self and
              policy == MailingListAutoSubscribePolicy.ON_REGISTRATION):
            # Assume that we requested to be joined.
            mailinglist.subscribe(self)
            return True
        else:
            # We don't want to subscribe to the list.
            return False

    @property
    def hardware_submissions(self):
        """See `IPerson`."""
        from lp.hardwaredb.model.hwdb import HWSubmissionSet
        return HWSubmissionSet().search(owner=self)

    @property
    def recipes(self):
        """See `IHasRecipes`."""
        from lp.code.model.sourcepackagerecipe import SourcePackageRecipe
        store = Store.of(self)
        return store.find(
            SourcePackageRecipe,
            SourcePackageRecipe.owner == self)

    def canAccess(self, obj, attribute):
        """See `IPerson.`"""
        return canAccess(obj, attribute)

    def canWrite(self, obj, attribute):
        """See `IPerson.`"""
        return canWrite(obj, attribute)

    def checkRename(self):
        """See `IPerson.`"""
        reasons = []
        atom = 'person'
        has_ppa = getUtility(IArchiveSet).getPPAOwnedByPerson(
            self, has_packages=True,
            statuses=[ArchiveStatus.ACTIVE,
                      ArchiveStatus.DELETING]) is not None
        has_mailing_list = None
        if ITeam.providedBy(self):
            atom = 'team'
            mailing_list = getUtility(IMailingListSet).get(self.name)
            has_mailing_list = (
                mailing_list is not None and
                mailing_list.status != MailingListStatus.PURGED)
        if has_ppa:
            reasons.append('an active PPA with packages published')
        if has_mailing_list:
            reasons.append('a mailing list')
        if reasons:
            return _('This %s has %s and may not be renamed.' % (
                atom, ' and '.join(reasons)))
        else:
            return None

    def canCreatePPA(self):
        """See `IPerson.`"""
        return self.subscriptionpolicy in CLOSED_TEAM_POLICY


class PersonSet:
    """The set of persons."""
    implements(IPersonSet)

    def __init__(self):
        self.title = 'People registered with Launchpad'

    def isNameBlacklisted(self, name, user=None):
        """See `IPersonSet`."""
        if user is None:
            user_id = 0
        else:
            user_id = user.id
        cur = cursor()
        cur.execute(
            "SELECT is_blacklisted_name(%(name)s, %(user_id)s)" % sqlvalues(
            name=name.encode('UTF-8'), user_id=user_id))
        return bool(cur.fetchone()[0])

    def getTopContributors(self, limit=50):
        """See `IPersonSet`."""
        # The odd ordering here is to ensure we hit the PostgreSQL
        # indexes. It will not make any real difference outside of tests.
        query = """
            id IN (
                SELECT person FROM KarmaTotalCache
                ORDER BY karma_total DESC, person DESC
                LIMIT %s
                )
            """ % limit
        top_people = shortlist(Person.select(query))
        return sorted(
            top_people,
            key=lambda obj: (obj.karma, obj.displayname, obj.id),
            reverse=True)

    def getOrCreateByOpenIDIdentifier(
        self, openid_identifier, email_address, full_name,
        creation_rationale, comment):
        """See `IPersonSet`."""
        assert email_address is not None and full_name is not None, (
                "Both email address and full name are required to "
                "create an account.")
        db_updated = False

        assert isinstance(openid_identifier, unicode)

        # Load the EmailAddress, Account and OpenIdIdentifier records
        # from the master (if they exist). We use the master to avoid
        # possible replication lag issues but this might actually be
        # unnecessary.
        with MasterDatabasePolicy():
            store = IMasterStore(EmailAddress)
            join = store.using(
                EmailAddress,
                LeftJoin(Account, EmailAddress.accountID == Account.id))
            email, account = (
                join.find(
                    (EmailAddress, Account),
                    EmailAddress.email.lower() ==
                        ensure_unicode(email_address).lower()).one()
                or (None, None))
            identifier = store.find(
                OpenIdIdentifier, identifier=openid_identifier).one()

            if email is None and identifier is None:
                # Neither the Email Address not the OpenId Identifier
                # exist in the database. Create the email address,
                # account, and associated info. OpenIdIdentifier is
                # created later.
                account_set = getUtility(IAccountSet)
                account, email = account_set.createAccountAndEmail(
                    email_address, creation_rationale, full_name,
                    password=None)
                db_updated = True

            elif email is None:
                # The Email Address does not exist in the database,
                # but the OpenId Identifier does. Create the Email
                # Address and link it to the account.
                assert account is None, 'Retrieved an account but not email?'
                account = identifier.account
                emailaddress_set = getUtility(IEmailAddressSet)
                email = emailaddress_set.new(
                    email_address, account=account)
                db_updated = True

            elif account is None:
                # Email address exists, but there is no Account linked
                # to it. Create the Account and link it to the
                # EmailAddress.
                account_set = getUtility(IAccountSet)
                account = account_set.new(
                    AccountCreationRationale.OWNER_CREATED_LAUNCHPAD,
                    full_name)
                email.account = account
                db_updated = True

            if identifier is None:
                # This is the first time we have seen that
                # OpenIdIdentifier. Link it.
                identifier = OpenIdIdentifier()
                identifier.account = account
                identifier.identifier = openid_identifier
                store.add(identifier)
                db_updated = True

            elif identifier.account != account:
                # The ISD OpenId server may have linked this OpenId
                # identifier to a new email address, or the user may
                # have transfered their email address to a different
                # Launchpad Account. If that happened, repair the
                # link - we trust the ISD OpenId server.
                identifier.account = account
                db_updated = True

            # We now have an account, email address, and openid identifier.

            if account.status == AccountStatus.SUSPENDED:
                raise AccountSuspendedError(
                    "The account matching the identifier is suspended.")

            elif account.status in [AccountStatus.DEACTIVATED,
                                    AccountStatus.NOACCOUNT]:
                password = ''  # Needed just to please reactivate() below.
                removeSecurityProxy(account).reactivate(
                    comment, password, removeSecurityProxy(email))
                db_updated = True
            else:
                # Account is active, so nothing to do.
                pass

            if IPerson(account, None) is None:
                removeSecurityProxy(account).createPerson(
                    creation_rationale, comment=comment)
                db_updated = True

            person = IPerson(account)
            if email.personID != person.id:
                removeSecurityProxy(email).person = person
                db_updated = True

            return person, db_updated

    def newTeam(self, teamowner, name, displayname, teamdescription=None,
                subscriptionpolicy=TeamSubscriptionPolicy.MODERATED,
                defaultmembershipperiod=None, defaultrenewalperiod=None):
        """See `IPersonSet`."""
        assert teamowner
        if self.getByName(name, ignore_merged=False) is not None:
            raise NameAlreadyTaken(
                "The name '%s' is already taken." % name)
        team = Person(teamowner=teamowner, name=name, displayname=displayname,
                teamdescription=teamdescription,
                defaultmembershipperiod=defaultmembershipperiod,
                defaultrenewalperiod=defaultrenewalperiod,
                subscriptionpolicy=subscriptionpolicy)
        notify(ObjectCreatedEvent(team))
        # Here we add the owner as a team admin manually because we know what
        # we're doing (so we don't need to do any sanity checks) and we don't
        # want any email notifications to be sent.
        TeamMembershipSet().new(
            teamowner, team, TeamMembershipStatus.ADMIN, teamowner)
        return team

    def createPersonAndEmail(
            self, email, rationale, comment=None, name=None,
            displayname=None, password=None, passwordEncrypted=False,
            hide_email_addresses=False, registrant=None):
        """See `IPersonSet`."""

        # This check is also done in EmailAddressSet.new() and also
        # generate_nick(). We repeat it here as some call sites want
        # InvalidEmailAddress rather than NicknameGenerationError that
        # generate_nick() will raise.
        if not valid_email(email):
            raise InvalidEmailAddress(
                "%s is not a valid email address." % email)

        if name is None:
            name = generate_nick(email)

        if not displayname:
            displayname = name.capitalize()

        # Convert the PersonCreationRationale to an AccountCreationRationale
        account_rationale = getattr(AccountCreationRationale, rationale.name)

        account = getUtility(IAccountSet).new(
                account_rationale, displayname, password=password,
                password_is_encrypted=passwordEncrypted)

        person = self._newPerson(
            name, displayname, hide_email_addresses, rationale=rationale,
            comment=comment, registrant=registrant, account=account)

        email = getUtility(IEmailAddressSet).new(
                email, person, account=account)

        assert email.accountID is not None, (
            'Failed to link EmailAddress to Account')
        return person, email

    def createPersonWithoutEmail(
        self, name, rationale, comment=None, displayname=None,
        registrant=None):
        """Create and return a new Person without using an email address.

        See `IPersonSet`.
        """
        return self._newPerson(
            name, displayname, hide_email_addresses=True, rationale=rationale,
            comment=comment, registrant=registrant)

    def _newPerson(self, name, displayname, hide_email_addresses,
                   rationale, comment=None, registrant=None, account=None):
        """Create and return a new Person with the given attributes."""
        if not valid_name(name):
            raise InvalidName(
                "%s is not a valid name for a person." % name)
        else:
            # The name should be okay, move on...
            pass
        if self.getByName(name, ignore_merged=False) is not None:
            raise NameAlreadyTaken(
                "The name '%s' is already taken." % name)

        if not displayname:
            displayname = name.capitalize()

        if account is None:
            account_id = None
        else:
            account_id = account.id
        person = Person(
            name=name, displayname=displayname, accountID=account_id,
            creation_rationale=rationale, creation_comment=comment,
            hide_email_addresses=hide_email_addresses, registrant=registrant)
        return person

    def ensurePerson(self, email, displayname, rationale, comment=None,
                     registrant=None):
        """See `IPersonSet`."""
        # Start by checking if there is an `EmailAddress` for the given
        # text address.  There are many cases where an email address can be
        # created without an associated `Person`. For instance, we created
        # an account linked to the address through an external system such
        # SSO or ShipIt.
        email_address = getUtility(IEmailAddressSet).getByEmail(email)

        # There is no `EmailAddress` for this text address, so we need to
        # create both the `Person` and `EmailAddress` here and we are done.
        if email_address is None:
            person, email_address = self.createPersonAndEmail(
                email, rationale, comment=comment, displayname=displayname,
                registrant=registrant, hide_email_addresses=True)
            return person

        # There is an `EmailAddress` for this text address, but no
        # associated `Person`.
        if email_address.person is None:
            assert email_address.accountID is not None, (
                '%s is not associated to a person or account'
                % email_address.email)
            account = IMasterStore(Account).get(
                Account, email_address.accountID)
            account_person = self.getByAccount(account)
            if account_person is None:
                # There is no associated `Person` to the email `Account`.
                # This is probably because the account was created externally
                # to Launchpad. Create just the `Person`, associate it with
                # the `EmailAddress` and return it.
                name = generate_nick(email)
                account_person = self._newPerson(
                    name, displayname, hide_email_addresses=True,
                    rationale=rationale, comment=comment,
                    registrant=registrant, account=email_address.account)
            # There is (now) a `Person` linked to the `Account`, link the
            # `EmailAddress` to this `Person` and return it.
            master_email = IMasterStore(EmailAddress).get(
                EmailAddress, email_address.id)
            master_email.personID = account_person.id
            # Populate the previously empty 'preferredemail' cached
            # property, so the Person record is up-to-date.
            if master_email.status == EmailAddressStatus.PREFERRED:
                cache = get_property_cache(account_person)
                cache.preferredemail = master_email
            return account_person

        # Easy, return the `Person` associated with the existing
        # `EmailAddress`.
        return IMasterStore(Person).get(Person, email_address.personID)

    def getByName(self, name, ignore_merged=True):
        """See `IPersonSet`."""
        query = (Person.q.name == name)
        if ignore_merged:
            query = AND(query, Person.q.mergedID == None)
        return Person.selectOne(query)

    def getByAccount(self, account):
        """See `IPersonSet`."""
        return Person.selectOne(Person.q.accountID == account.id)

    def updateStatistics(self, ztm):
        """See `IPersonSet`."""
        stats = getUtility(ILaunchpadStatisticSet)
        people_count = Person.select(
            AND(Person.q.teamownerID == None,
                Person.q.mergedID == None)).count()
        stats.update('people_count', people_count)
        ztm.commit()
        teams_count = Person.select(
            AND(Person.q.teamownerID != None,
                Person.q.mergedID == None)).count()
        stats.update('teams_count', teams_count)
        ztm.commit()

    def peopleCount(self):
        """See `IPersonSet`."""
        return getUtility(ILaunchpadStatisticSet).value('people_count')

    def teamsCount(self):
        """See `IPersonSet`."""
        return getUtility(ILaunchpadStatisticSet).value('teams_count')

    def _teamPrivacyQuery(self):
        """Generate the query needed for privacy filtering.

        If the visibility is not PUBLIC ensure the logged in user is a member
        of the team.
        """
        logged_in_user = getUtility(ILaunchBag).user
        if logged_in_user is not None:
            private_query = SQL("""
                TeamParticipation.person = ?
                AND Person.teamowner IS NOT NULL
                AND Person.visibility != ?
                """, (logged_in_user.id, PersonVisibility.PUBLIC.value))
        else:
            private_query = None

        base_query = SQL("Person.visibility = ?",
                         (PersonVisibility.PUBLIC.value, ),
                         tables=['Person'])

        if private_query is None:
            query = base_query
        else:
            query = Or(base_query, private_query)

        return query

    def _teamEmailQuery(self, text):
        """Product the query for team email addresses."""
        privacy_query = self._teamPrivacyQuery()
        # XXX: BradCrittenden 2009-06-08 bug=244768:  Use Not(Bar.foo == None)
        # instead of Bar.foo != None.
        team_email_query = And(
            privacy_query,
            TeamParticipation.team == Person.id,
            Not(Person.teamowner == None),
            Person.merged == None,
            EmailAddress.person == Person.id,
            EmailAddress.email.lower().startswith(ensure_unicode(text)))
        return team_email_query

    def _teamNameQuery(self, text):
        """Produce the query for team names."""
        privacy_query = self._teamPrivacyQuery()
        # XXX: BradCrittenden 2009-06-08 bug=244768:  Use Not(Bar.foo == None)
        # instead of Bar.foo != None.
        team_name_query = And(
            privacy_query,
            TeamParticipation.team == Person.id,
            Not(Person.teamowner == None),
            Person.merged == None,
            SQL("Person.fti @@ ftq(?)", (text, )))
        return team_name_query

    def find(self, text=""):
        """See `IPersonSet`."""
        if not text:
            # Return an empty result set.
            return EmptyResultSet()

        orderBy = Person._sortingColumnsForSetOperations
        text = ensure_unicode(text).lower()
        # Teams may not have email addresses, so we need to either use a LEFT
        # OUTER JOIN or do a UNION between four queries. Using a UNION makes
        # it a lot faster than with a LEFT OUTER JOIN.
        person_email_query = And(
            Person.teamowner == None,
            Person.merged == None,
            EmailAddress.person == Person.id,
            Person.account == Account.id,
            Not(Account.status.is_in(INACTIVE_ACCOUNT_STATUSES)),
            EmailAddress.email.lower().startswith(text))

        store = IStore(Person)

        # The call to order_by() is necessary to avoid having the default
        # ordering applied.  Since no value is passed the effect is to remove
        # the generation of an 'ORDER BY' clause on the intermediate results.
        # Otherwise the default ordering is taken from the ordering
        # declaration on the class.  The final result set will have the
        # appropriate ordering set.
        results = store.find(
            Person, person_email_query).order_by()

        person_name_query = And(
            Person.teamowner == None,
            Person.merged == None,
            Person.account == Account.id,
            Not(Account.status.is_in(INACTIVE_ACCOUNT_STATUSES)),
            SQL("Person.fti @@ ftq(?)", (text, ))
            )

        results = results.union(store.find(
            Person, person_name_query)).order_by()
        team_email_query = self._teamEmailQuery(text)
        results = results.union(
            store.find(Person, team_email_query)).order_by()
        team_name_query = self._teamNameQuery(text)
        results = results.union(
            store.find(Person, team_name_query)).order_by()

        return results.order_by(orderBy)

    def findPerson(
            self, text="", exclude_inactive_accounts=True,
            must_have_email=False, created_after=None, created_before=None):
        """See `IPersonSet`."""
        orderBy = Person._sortingColumnsForSetOperations
        text = ensure_unicode(text).lower()
        store = IStore(Person)
        base_query = And(
            Person.teamowner == None,
            Person.merged == None)

        clause_tables = []

        if exclude_inactive_accounts:
            clause_tables.append('Account')
            base_query = And(
                base_query,
                Person.account == Account.id,
                Not(Account.status.is_in(INACTIVE_ACCOUNT_STATUSES)))
        email_clause_tables = clause_tables + ['EmailAddress']
        if must_have_email:
            clause_tables = email_clause_tables
            base_query = And(
                base_query,
                EmailAddress.person == Person.id)
        if created_after is not None:
            base_query = And(
                base_query,
                Person.datecreated > created_after)
        if created_before is not None:
            base_query = And(
                base_query,
                Person.datecreated < created_before)

        # Short circuit for returning all users in order
        if not text:
            results = store.find(Person, base_query)
            return results.order_by(Person._storm_sortingColumns)

        # We use a UNION here because this makes things *a lot* faster
        # than if we did a single SELECT with the two following clauses
        # ORed.
        email_query = And(
            base_query,
            EmailAddress.person == Person.id,
            EmailAddress.email.lower().startswith(ensure_unicode(text)))

        name_query = And(
            base_query,
            SQL("Person.fti @@ ftq(?)", (text, )))
        email_results = store.find(Person, email_query).order_by()
        name_results = store.find(Person, name_query).order_by()
        combined_results = email_results.union(name_results)
        return combined_results.order_by(orderBy)

    def findTeam(self, text=""):
        """See `IPersonSet`."""
        orderBy = Person._sortingColumnsForSetOperations
        text = ensure_unicode(text).lower()
        # Teams may not have email addresses, so we need to either use a LEFT
        # OUTER JOIN or do a UNION between two queries. Using a UNION makes
        # it a lot faster than with a LEFT OUTER JOIN.
        email_query = self._teamEmailQuery(text)
        store = IStore(Person)
        email_results = store.find(Person, email_query).order_by()
        name_query = self._teamNameQuery(text)
        name_results = store.find(Person, name_query).order_by()
        combined_results = email_results.union(name_results)
        return combined_results.order_by(orderBy)

    def get(self, personid):
        """See `IPersonSet`."""
        try:
            return Person.get(personid)
        except SQLObjectNotFound:
            return None

    def getByEmail(self, email):
        """See `IPersonSet`."""
        address = self.getByEmails([email]).one()
        if address:
            return address[1]

    def getByEmails(self, emails, include_hidden=True):
        """See `IPersonSet`."""
        if not emails:
            return EmptyResultSet()
        addresses = [
            ensure_unicode(address.lower().strip())
            for address in emails]
        extra_query = True
        if not include_hidden:
            extra_query = Person.hide_email_addresses == False
        return IStore(Person).using(
            Person,
            Join(EmailAddress, EmailAddress.personID == Person.id)
        ).find(
            (EmailAddress, Person),
            EmailAddress.email.lower().is_in(addresses), extra_query)

    def latest_teams(self, limit=5):
        """See `IPersonSet`."""
        return Person.select("Person.teamowner IS NOT NULL",
            orderBy=['-datecreated'], limit=limit)

    def _merge_person_decoration(self, to_person, from_person, skip,
        decorator_table, person_pointer_column, additional_person_columns):
        """Merge a table that "decorates" Person.

        Because "person decoration" is becoming more frequent, we create a
        helper function that can be used for tables that decorate person.

        :to_person:       the IPerson that is "real"
        :from_person:     the IPerson that is being merged away
        :skip:            a list of table/column pairs that have been
                          handled
        :decorator_table: the name of the table that decorated Person
        :person_pointer_column:
                          the column on decorator_table that UNIQUE'ly
                          references Person.id
        :additional_person_columns:
                          additional columns in the decorator_table that
                          also reference Person.id but are not UNIQUE

        A Person decorator is a table that uniquely references Person,
        so that the information in the table "extends" the Person table.
        Because the reference to Person is unique, there can only be one
        row in the decorator table for any given Person. This function
        checks if there is an existing decorator for the to_person, and
        if so, it just leaves any from_person decorator in place as
        "noise". Otherwise, it updates any from_person decorator to
        point to the "to_person". There can also be other columns in the
        decorator which point to Person, these are assumed to be
        non-unique and will be updated to point to the to_person
        regardless.
        """
        store = Store.of(to_person)
        # First, update the main UNIQUE pointer row which links the
        # decorator table to Person. We do not update rows if there are
        # already rows in the table that refer to the to_person
        store.execute(
         """UPDATE %(decorator)s
            SET %(person_pointer)s=%(to_id)d
            WHERE %(person_pointer)s=%(from_id)d
              AND ( SELECT count(*) FROM %(decorator)s
                    WHERE %(person_pointer)s=%(to_id)d ) = 0
            """ % {
                'decorator': decorator_table,
                'person_pointer': person_pointer_column,
                'from_id': from_person.id,
                'to_id': to_person.id})

        # Now, update any additional columns in the table which point to
        # Person. Since these are assumed to be NOT UNIQUE, we don't
        # have to worry about multiple rows pointing at the to_person.
        for additional_column in additional_person_columns:
            store.execute(
             """UPDATE %(decorator)s
                SET %(column)s=%(to_id)d
                WHERE %(column)s=%(from_id)d
                """ % {
                    'decorator': decorator_table,
                    'from_id': from_person.id,
                    'to_id': to_person.id,
                    'column': additional_column})
        skip.append(
            (decorator_table.lower(), person_pointer_column.lower()))

    def _mergeBranches(self, from_person, to_person):
        # This shouldn't use removeSecurityProxy.
        branches = getUtility(IBranchCollection).ownedBy(from_person)
        for branch in branches.getBranches():
            removeSecurityProxy(branch).setOwner(to_person, to_person)

    def _mergeBranchMergeQueues(self, cur, from_id, to_id):
        cur.execute('''
            UPDATE BranchMergeQueue SET owner = %(to_id)s WHERE owner =
            %(from_id)s''', dict(to_id=to_id, from_id=from_id))

    def _mergeSourcePackageRecipes(self, from_person, to_person):
        # This shouldn't use removeSecurityProxy.
        recipes = from_person.recipes
        existing_names = [r.name for r in to_person.recipes]
        for recipe in recipes:
            new_name = recipe.name
            count = 1
            while new_name in existing_names:
                new_name = '%s-%s' % (recipe.name, count)
                count += 1
            naked_recipe = removeSecurityProxy(recipe)
            naked_recipe.owner = to_person
            naked_recipe.name = new_name

    def _mergeMailingListSubscriptions(self, cur, from_id, to_id):
        # Update MailingListSubscription. Note that since all the from_id
        # email addresses are set to NEW, all the subscriptions must be
        # removed because the user must confirm them.
        cur.execute('''
            DELETE FROM MailingListSubscription WHERE person=%(from_id)d
            ''' % vars())

    def _mergeBranchSubscription(self, cur, from_id, to_id):
        # Update only the BranchSubscription that will not conflict.
        cur.execute('''
            UPDATE BranchSubscription
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND branch NOT IN
                (
                SELECT branch
                FROM BranchSubscription
                WHERE person = %(to_id)d
                )
            ''' % vars())
        # and delete those left over.
        cur.execute('''
            DELETE FROM BranchSubscription WHERE person=%(from_id)d
            ''' % vars())

    def _mergeBugAffectsPerson(self, cur, from_id, to_id):
        # Update only the BugAffectsPerson that will not conflict
        cur.execute('''
            UPDATE BugAffectsPerson
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND bug NOT IN
                (
                SELECT bug
                FROM BugAffectsPerson
                WHERE person = %(to_id)d
                )
            ''' % vars())
        # and delete those left over.
        cur.execute('''
            DELETE FROM BugAffectsPerson WHERE person=%(from_id)d
            ''' % vars())

    def _mergeAnswerContact(self, cur, from_id, to_id):
        # Update only the AnswerContacts that will not conflict.
        cur.execute('''
            UPDATE AnswerContact
            SET person=%(to_id)d
            WHERE person=%(from_id)d
                AND distribution IS NULL
                AND product NOT IN (
                    SELECT product
                    FROM AnswerContact
                    WHERE person = %(to_id)d
                    )
            ''' % vars())
        cur.execute('''
            UPDATE AnswerContact
            SET person=%(to_id)d
            WHERE person=%(from_id)d
                AND distribution IS NOT NULL
                AND (distribution, sourcepackagename) NOT IN (
                    SELECT distribution,sourcepackagename
                    FROM AnswerContact
                    WHERE person = %(to_id)d
                    )
            ''' % vars())
        # and delete those left over.
        cur.execute('''
            DELETE FROM AnswerContact WHERE person=%(from_id)d
            ''' % vars())

    def _mergeQuestionSubscription(self, cur, from_id, to_id):
        # Update only the QuestionSubscriptions that will not conflict.
        cur.execute('''
            UPDATE QuestionSubscription
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND question NOT IN
                (
                SELECT question
                FROM QuestionSubscription
                WHERE person = %(to_id)d
                )
            ''' % vars())
        # and delete those left over.
        cur.execute('''
            DELETE FROM QuestionSubscription WHERE person=%(from_id)d
            ''' % vars())

    def _mergeBugNotificationRecipient(self, cur, from_id, to_id):
        # Update BugNotificationRecipient entries that will not conflict.
        cur.execute('''
            UPDATE BugNotificationRecipient
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND bug_notification NOT IN (
                SELECT bug_notification FROM BugNotificationRecipient
                WHERE person=%(to_id)d
                )
            ''' % vars())
        # and delete those left over.
        cur.execute('''
            DELETE FROM BugNotificationRecipient
            WHERE person=%(from_id)d
            ''' % vars())

    def _mergeStructuralSubscriptions(self, cur, from_id, to_id):
        # Update StructuralSubscription entries that will not conflict.
        # We separate this out from the parent query primarily to help
        # keep within our line length constraints, though it might make
        # things more readable otherwise as well.
        exists_query = '''
            SELECT StructuralSubscription.id
            FROM StructuralSubscription
            WHERE StructuralSubscription.subscriber=%(to_id)d AND (
                StructuralSubscription.product=SSub.product
                OR
                StructuralSubscription.project=SSub.project
                OR
                StructuralSubscription.distroseries=SSub.distroseries
                OR
                StructuralSubscription.milestone=SSub.milestone
                OR
                StructuralSubscription.productseries=SSub.productseries
                OR
                (StructuralSubscription.distribution=SSub.distribution
                 AND StructuralSubscription.sourcepackagename IS NULL
                 AND SSub.sourcepackagename IS NULL)
                OR
                (StructuralSubscription.sourcepackagename=
                    SSub.sourcepackagename
                 AND StructuralSubscription.sourcepackagename=
                    SSub.sourcepackagename)
                )
            '''
        cur.execute(('''
            UPDATE StructuralSubscription
            SET subscriber=%(to_id)d
            WHERE subscriber=%(from_id)d AND id NOT IN (
                SELECT SSub.id
                FROM StructuralSubscription AS SSub
                WHERE
                    SSub.subscriber=%(from_id)d
                    AND EXISTS (''' + exists_query + ''')
            )
            ''') % vars())
        # Delete the rest.  We have to explicitly delete the bug subscription
        # filters first because there is not a cascade delete set up in the
        # db.
        cur.execute('''
            DELETE FROM BugSubscriptionFilter
            WHERE structuralsubscription IN (
                SELECT id
                FROM StructuralSubscription
                WHERE subscriber=%(from_id)d)
            ''' % vars())
        cur.execute('''
            DELETE FROM StructuralSubscription WHERE subscriber=%(from_id)d
            ''' % vars())

    def _mergeSpecificationFeedback(self, cur, from_id, to_id):
        # Update the SpecificationFeedback entries that will not conflict
        # and trash the rest.

        # First we handle the reviewer.
        cur.execute('''
            UPDATE SpecificationFeedback
            SET reviewer=%(to_id)d
            WHERE reviewer=%(from_id)d AND specification NOT IN
                (
                SELECT specification
                FROM SpecificationFeedback
                WHERE reviewer = %(to_id)d
                )
            ''' % vars())
        cur.execute('''
            DELETE FROM SpecificationFeedback WHERE reviewer=%(from_id)d
            ''' % vars())

        # And now we handle the requester.
        cur.execute('''
            UPDATE SpecificationFeedback
            SET requester=%(to_id)d
            WHERE requester=%(from_id)d AND specification NOT IN
                (
                SELECT specification
                FROM SpecificationFeedback
                WHERE requester = %(to_id)d
                )
            ''' % vars())
        cur.execute('''
            DELETE FROM SpecificationFeedback WHERE requester=%(from_id)d
            ''' % vars())

    def _mergeSpecificationSubscription(self, cur, from_id, to_id):
        # Update the SpecificationSubscription entries that will not conflict
        # and trash the rest
        cur.execute('''
            UPDATE SpecificationSubscription
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND specification NOT IN
                (
                SELECT specification
                FROM SpecificationSubscription
                WHERE person = %(to_id)d
                )
            ''' % vars())
        cur.execute('''
            DELETE FROM SpecificationSubscription WHERE person=%(from_id)d
            ''' % vars())

    def _mergeSprintAttendance(self, cur, from_id, to_id):
        # Update only the SprintAttendances that will not conflict
        cur.execute('''
            UPDATE SprintAttendance
            SET attendee=%(to_id)d
            WHERE attendee=%(from_id)d AND sprint NOT IN
                (
                SELECT sprint
                FROM SprintAttendance
                WHERE attendee = %(to_id)d
                )
            ''' % vars())
        # and delete those left over
        cur.execute('''
            DELETE FROM SprintAttendance WHERE attendee=%(from_id)d
            ''' % vars())

    def _mergePOExportRequest(self, cur, from_id, to_id):
        # Update only the POExportRequests that will not conflict
        # and trash the rest
        cur.execute('''
            UPDATE POExportRequest
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND id NOT IN (
                SELECT a.id FROM POExportRequest AS a, POExportRequest AS b
                WHERE a.person = %(from_id)d AND b.person = %(to_id)d
                AND a.potemplate = b.potemplate
                AND a.pofile = b.pofile
                )
            ''' % vars())
        cur.execute('''
            DELETE FROM POExportRequest WHERE person=%(from_id)d
            ''' % vars())

    def _mergeTranslationMessage(self, cur, from_id, to_id):
        # Update the TranslationMessage. They should not conflict since each
        # of them are independent
        cur.execute('''
            UPDATE TranslationMessage
            SET submitter=%(to_id)d
            WHERE submitter=%(from_id)d
            ''' % vars())
        cur.execute('''
            UPDATE TranslationMessage
            SET reviewer=%(to_id)d
            WHERE reviewer=%(from_id)d
            ''' % vars())

    def _mergeTranslationImportQueueEntry(self, cur, from_id, to_id):
        # Update only the TranslationImportQueueEntry that will not conflict
        # and trash the rest
        cur.execute('''
            UPDATE TranslationImportQueueEntry
            SET importer=%(to_id)d
            WHERE importer=%(from_id)d AND id NOT IN (
                SELECT a.id
                FROM TranslationImportQueueEntry AS a,
                     TranslationImportQueueEntry AS b
                WHERE a.importer = %(from_id)d AND b.importer = %(to_id)d
                AND a.distroseries = b.distroseries
                AND a.sourcepackagename = b.sourcepackagename
                AND a.productseries = b.productseries
                AND a.path = b.path
                )
            ''' % vars())
        cur.execute('''
            DELETE FROM TranslationImportQueueEntry WHERE importer=%(from_id)d
            ''' % vars())

    def _mergeCodeReviewVote(self, cur, from_id, to_id):
        # Update only the CodeReviewVote that will not conflict,
        # and leave conflicts as noise
        cur.execute('''
            UPDATE CodeReviewVote
            SET reviewer=%(to_id)d
            WHERE reviewer=%(from_id)d AND id NOT IN (
                SELECT a.id FROM CodeReviewVote AS a, CodeReviewVote AS b
                WHERE a.reviewer = %(from_id)d AND b.reviewer = %(to_id)d
                AND a.branch_merge_proposal = b.branch_merge_proposal
                )
            ''' % vars())

    def _mergeTeamMembership(self, cur, from_id, to_id):
        # Transfer active team memberships
        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN
        cur.execute(
            'SELECT team, status FROM TeamMembership WHERE person = %s '
            'AND status IN (%s,%s)'
            % sqlvalues(from_id, approved, admin))
        for team_id, status in cur.fetchall():
            cur.execute('SELECT status FROM TeamMembership WHERE person = %s '
                        'AND team = %s'
                        % sqlvalues(to_id, team_id))
            result = cur.fetchone()
            if result is not None:
                current_status = result[0]
                # Now we can safely delete from_person's membership record,
                # because we know to_person has a membership entry for this
                # team, so may only need to change its status.
                cur.execute(
                    'DELETE FROM TeamMembership WHERE person = %s '
                    'AND team = %s' % sqlvalues(from_id, team_id))

                if current_status == admin.value:
                    # to_person is already an administrator of this team, no
                    # need to do anything else.
                    continue
                # to_person is either an approved or an inactive member,
                # while from_person is either admin or approved. That means we
                # can safely set from_person's membership status on
                # to_person's membership.
                assert status in (approved.value, admin.value)
                cur.execute(
                    'UPDATE TeamMembership SET status = %s WHERE person = %s '
                    'AND team = %s' % sqlvalues(status, to_id, team_id))
            else:
                # to_person is not a member of this team. just change
                # from_person with to_person in the membership record.
                cur.execute(
                    'UPDATE TeamMembership SET person = %s WHERE person = %s '
                    'AND team = %s'
                    % sqlvalues(to_id, from_id, team_id))

        cur.execute('SELECT team FROM TeamParticipation WHERE person = %s '
                    'AND person != team' % sqlvalues(from_id))
        for team_id in cur.fetchall():
            cur.execute(
                'SELECT team FROM TeamParticipation WHERE person = %s '
                'AND team = %s' % sqlvalues(to_id, team_id))
            if not cur.fetchone():
                cur.execute(
                    'UPDATE TeamParticipation SET person = %s WHERE '
                    'person = %s AND team = %s'
                    % sqlvalues(to_id, from_id, team_id))
            else:
                cur.execute(
                    'DELETE FROM TeamParticipation WHERE person = %s AND '
                    'team = %s' % sqlvalues(from_id, team_id))

    def _mergeKarmaCache(self, cur, from_id, to_id, from_karma):
        # Merge the karma total cache so the user does not think the karma
        # was lost.
        params = dict(from_id=from_id, to_id=to_id)
        if from_karma > 0:
            cur.execute('''
                SELECT karma_total FROM KarmaTotalCache
                WHERE person = %(to_id)d
                ''' % params)
            result = cur.fetchone()
            if result is not None:
                # Add the karma to the remaining user.
                params['karma_total'] = from_karma + result[0]
                cur.execute('''
                    UPDATE KarmaTotalCache SET karma_total = %(karma_total)d
                    WHERE person = %(to_id)d
                    ''' % params)
            else:
                # Make the existing karma belong to the remaining user.
                cur.execute('''
                    UPDATE KarmaTotalCache SET person = %(to_id)d
                    WHERE person = %(from_id)d
                    ''' % params)
        # Delete the old caches; the daily job will build them later.
        cur.execute('''
            DELETE FROM KarmaTotalCache WHERE person = %(from_id)d
            ''' % params)
        cur.execute('''
            DELETE FROM KarmaCache WHERE person = %(from_id)d
            ''' % params)

    def _mergeDateCreated(self, cur, from_id, to_id):
        cur.execute('''
            UPDATE Person
            SET datecreated = (
                SELECT MIN(datecreated) FROM Person
                WHERE id in (%(to_id)d, %(from_id)d) LIMIT 1)
            WHERE id = %(to_id)d
            ''' % vars())

    def _purgeUnmergableTeamArtifacts(self, from_team, to_team, reviewer):
        """Purge team artifacts that cannot be merged, but can be removed."""
        # A team cannot have more than one mailing list.
        mailing_list = getUtility(IMailingListSet).get(from_team.name)
        if mailing_list is not None:
            if mailing_list.status in PURGE_STATES:
                from_team.mailing_list.purge()
            elif mailing_list.status != MailingListStatus.PURGED:
                raise AssertionError(
                    "Teams with active mailing lists cannot be merged.")
        # Team email addresses are not transferable.
        from_team.setContactAddress(None)
        # Memberships in the team are not transferable because there
        # is a high probablity there will be a CyclicTeamMembershipError.
        comment = (
            'Deactivating all members as this team is being merged into %s.'
            % to_team.name)
        membershipset = getUtility(ITeamMembershipSet)
        membershipset.deactivateActiveMemberships(
            from_team, comment, reviewer)
        # Memberships in other teams are not transferable because there
        # is a high probablity there will be a CyclicTeamMembershipError.
        all_super_teams = set(from_team.teams_participated_in)
        indirect_super_teams = set(
            from_team.teams_indirectly_participated_in)
        super_teams = all_super_teams - indirect_super_teams
        naked_from_team = removeSecurityProxy(from_team)
        for team in super_teams:
            naked_from_team.retractTeamMembership(team, reviewer)
        IStore(from_team).flush()

    def mergeAsync(self, from_person, to_person, reviewer=None, delete=False):
        """See `IPersonSet`."""
        return getUtility(IPersonMergeJobSource).create(
            from_person=from_person, to_person=to_person, reviewer=reviewer,
            delete=delete)

    def delete(self, from_person, reviewer):
        """See `IPersonSet`."""
        # Deletes are implemented by merging into registry experts. Force
        # the target to prevent any accidental misuse by calling code.
        to_person = getUtility(ILaunchpadCelebrities).registry_experts
        return self._merge(from_person, to_person, reviewer, True)

    def merge(self, from_person, to_person, reviewer=None):
        """See `IPersonSet`."""
        return self._merge(from_person, to_person, reviewer)

    def _merge(self, from_person, to_person, reviewer, delete=False):
        """Helper for merge and delete methods."""
        # since we are doing direct SQL manipulation, make sure all
        # changes have been flushed to the database
        store = Store.of(from_person)
        store.flush()
        if (from_person.is_team and not to_person.is_team
            or not from_person.is_team and to_person.is_team):
            raise AssertionError("Users cannot be merged with teams.")
        if from_person.is_team and reviewer is None:
            raise AssertionError("Team merged require a reviewer.")
        if getUtility(IArchiveSet).getPPAOwnedByPerson(
            from_person, statuses=[ArchiveStatus.ACTIVE,
                                   ArchiveStatus.DELETING]) is not None:
            raise AssertionError(
                'from_person has a ppa in ACTIVE or DELETING status')
        if from_person.is_team:
            self._purgeUnmergableTeamArtifacts(
                from_person, to_person, reviewer)
        if getUtility(IEmailAddressSet).getByPerson(from_person).count() > 0:
            raise AssertionError('from_person still has email addresses.')

        # Get a database cursor.
        cur = cursor()

        # These table.columns will be skipped by the 'catch all'
        # update performed later
        skip = [
            ('teammembership', 'person'),
            ('teammembership', 'team'),
            ('teamparticipation', 'person'),
            ('teamparticipation', 'team'),
            ('personlanguage', 'person'),
            ('person', 'merged'),
            ('personsettings', 'person'),
            ('emailaddress', 'person'),
            # Polls are not carried over when merging teams.
            ('poll', 'team'),
            # We can safely ignore the mailinglist table as there's a sanity
            # check above which prevents teams with associated mailing lists
            # from being merged.
            ('mailinglist', 'team'),
            # I don't think we need to worry about the votecast and vote
            # tables, because a real human should never have two profiles
            # in Launchpad that are active members of a given team and voted
            # in a given poll. -- GuilhermeSalgado 2005-07-07
            # We also can't afford to change poll results after they are
            # closed -- StuartBishop 20060602
            ('votecast', 'person'),
            ('vote', 'person'),
            ('translationrelicensingagreement', 'person'),
            # These are ON DELETE CASCADE and maintained by triggers.
            ('bugsummary', 'viewed_by'),
            ('bugsummaryjournal', 'viewed_by'),
            ]

        references = list(postgresql.listReferences(cur, 'person', 'id'))

        # Sanity check. If we have an indirect reference, it must
        # be ON DELETE CASCADE. We only have one case of this at the moment,
        # but this code ensures we catch any new ones added incorrectly.
        for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
            # If the ref_tab and ref_col is not Person.id, then we have
            # an indirect reference. Ensure the update action is 'CASCADE'
            if ref_tab != 'person' and ref_col != 'id':
                if updact != 'c':
                    raise RuntimeError(
                        '%s.%s reference to %s.%s must be ON UPDATE CASCADE'
                        % (src_tab, src_col, ref_tab, ref_col))

        # These rows are in a UNIQUE index, and we can only move them
        # to the new Person if there is not already an entry. eg. if
        # the destination and source persons are both subscribed to a bug,
        # we cannot change the source persons subscription. We just leave them
        # as noise for the time being.

        to_id = to_person.id
        from_id = from_person.id

        # Update PersonLocation, which is a Person-decorator table.
        self._merge_person_decoration(
            to_person, from_person, skip, 'PersonLocation', 'person',
            ['last_modified_by', ])

        # Update GPGKey. It won't conflict, but our sanity checks don't
        # know that.
        cur.execute(
            'UPDATE GPGKey SET owner=%(to_id)d WHERE owner=%(from_id)d'
            % vars())
        skip.append(('gpgkey', 'owner'))

        # Update the Branches that will not conflict, and fudge the names of
        # ones that *do* conflict.
        self._mergeBranches(from_person, to_person)
        skip.append(('branch', 'owner'))

        self._mergeBranchMergeQueues(cur, from_id, to_id)
        skip.append(('branchmergequeue', 'owner'))

        self._mergeSourcePackageRecipes(from_person, to_person)
        skip.append(('sourcepackagerecipe', 'owner'))

        self._mergeMailingListSubscriptions(cur, from_id, to_id)
        skip.append(('mailinglistsubscription', 'person'))

        self._mergeBranchSubscription(cur, from_id, to_id)
        skip.append(('branchsubscription', 'person'))

        self._mergeBugAffectsPerson(cur, from_id, to_id)
        skip.append(('bugaffectsperson', 'person'))

        self._mergeAnswerContact(cur, from_id, to_id)
        skip.append(('answercontact', 'person'))

        self._mergeQuestionSubscription(cur, from_id, to_id)
        skip.append(('questionsubscription', 'person'))

        self._mergeBugNotificationRecipient(cur, from_id, to_id)
        skip.append(('bugnotificationrecipient', 'person'))

        # We ignore BugSubscriptionFilterMutes.
        skip.append(('bugsubscriptionfiltermute', 'person'))

        # We ignore BugMutes.
        skip.append(('bugmute', 'person'))

        self._mergeStructuralSubscriptions(cur, from_id, to_id)
        skip.append(('structuralsubscription', 'subscriber'))

        self._mergeSpecificationFeedback(cur, from_id, to_id)
        skip.append(('specificationfeedback', 'reviewer'))
        skip.append(('specificationfeedback', 'requester'))

        self._mergeSpecificationSubscription(cur, from_id, to_id)
        skip.append(('specificationsubscription', 'person'))

        self._mergeSprintAttendance(cur, from_id, to_id)
        skip.append(('sprintattendance', 'attendee'))

        self._mergePOExportRequest(cur, from_id, to_id)
        skip.append(('poexportrequest', 'person'))

        self._mergeTranslationMessage(cur, from_id, to_id)
        skip.append(('translationmessage', 'submitter'))
        skip.append(('translationmessage', 'reviewer'))

        # Handle the POFileTranslator cache by doing nothing. As it is
        # maintained by triggers, the data migration has already been done
        # for us when we updated the source tables.
        skip.append(('pofiletranslator', 'person'))

        self._mergeTranslationImportQueueEntry(cur, from_id, to_id)
        skip.append(('translationimportqueueentry', 'importer'))

        # XXX cprov 2007-02-22 bug=87098:
        # Since we only allow one PPA for each user,
        # we can't reassign the old user archive to the new user.
        # It need to be done manually, probably by reasinning all publications
        # to the old PPA to the new one, performing a careful_publishing on it
        # and removing the old one from disk.
        skip.append(('archive', 'owner'))

        self._mergeCodeReviewVote(cur, from_id, to_id)
        skip.append(('codereviewvote', 'reviewer'))

        self._mergeKarmaCache(cur, from_id, to_id, from_person.karma)
        skip.append(('karmacache', 'person'))
        skip.append(('karmatotalcache', 'person'))

        self._mergeDateCreated(cur, from_id, to_id)

        # Sanity check. If we have a reference that participates in a
        # UNIQUE index, it must have already been handled by this point.
        # We can tell this by looking at the skip list.
        for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
            uniques = postgresql.listUniques(cur, src_tab, src_col)
            if len(uniques) > 0 and (src_tab, src_col) not in skip:
                raise NotImplementedError(
                        '%s.%s reference to %s.%s is in a UNIQUE index '
                        'but has not been handled' % (
                            src_tab, src_col, ref_tab, ref_col))

        # Handle all simple cases
        for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
            if (src_tab, src_col) in skip:
                continue
            cur.execute('UPDATE %s SET %s=%d WHERE %s=%d' % (
                src_tab, src_col, to_person.id, src_col, from_person.id))

        self._mergeTeamMembership(cur, from_id, to_id)

        # Flag the person as merged
        cur.execute('''
            UPDATE Person SET merged=%(to_id)d WHERE id=%(from_id)d
            ''' % vars())

        # Append a -merged suffix to the person's name.
        name = base = "%s-merged" % from_person.name.encode('ascii')
        cur.execute("SELECT id FROM Person WHERE name = %s" % sqlvalues(name))
        i = 1
        while cur.fetchone():
            name = "%s%d" % (base, i)
            cur.execute("SELECT id FROM Person WHERE name = %s"
                        % sqlvalues(name))
            i += 1
        cur.execute("UPDATE Person SET name = %s WHERE id = %s"
                    % sqlvalues(name, from_person))

        # Since we've updated the database behind Storm's back,
        # flush its caches.
        store.invalidate()

        # Move OpenId Identifiers from the merged account to the new
        # account.
        if from_person.account is not None and to_person.account is not None:
            store.execute("""
                UPDATE OpenIdIdentifier SET account=%s WHERE account=%s
                """ % sqlvalues(to_person.accountID, from_person.accountID))

        if delete:
            # We don't notify anyone about deletes.
            return

        # Inform the user of the merge changes.
        if to_person.isTeam():
            mail_text = get_email_template(
                'team-merged.txt', app='registry')
            subject = 'Launchpad teams merged'
        else:
            mail_text = get_email_template(
                'person-merged.txt', app='registry')
            subject = 'Launchpad accounts merged'
        mail_text = mail_text % {
            'dupename': from_person.name,
            'person': to_person.name,
            }
        getUtility(IPersonNotificationSet).addNotification(
            to_person, subject, mail_text)

    def getValidPersons(self, persons):
        """See `IPersonSet.`"""
        person_ids = [person.id for person in persons]
        if len(person_ids) == 0:
            return []

        # This has the side effect of sucking in the ValidPersonCache
        # items into the cache, allowing Person.is_valid_person calls to
        # not hit the DB.
        valid_person_ids = set(
                person_id.id for person_id in ValidPersonCache.select(
                    "id IN %s" % sqlvalues(person_ids)))
        return [
            person for person in persons if person.id in valid_person_ids]

    def getPeopleWithBranches(self, product=None):
        """See `IPersonSet`."""
        branch_clause = 'SELECT owner FROM Branch'
        if product is not None:
            branch_clause += ' WHERE product = %s' % quote(product)
        return Person.select('''
            Person.id in (%s)
            ''' % branch_clause)

    def updatePersonalStandings(self):
        """See `IPersonSet`."""
        cur = cursor()
        cur.execute("""
        UPDATE Person
        SET personal_standing = %s
        WHERE personal_standing = %s
        AND id IN (
            SELECT posted_by
            FROM MessageApproval
            WHERE status = %s
            GROUP BY posted_by
            HAVING COUNT(DISTINCT mailing_list) >= %s
            )
        """ % sqlvalues(PersonalStanding.GOOD,
                        PersonalStanding.UNKNOWN,
                        PostedMessageStatus.APPROVED,
                        config.standingupdater.approvals_needed))

    def cacheBrandingForPeople(self, people):
        """See `IPersonSet`."""
        aliases = []
        aliases.extend(person.iconID for person in people
                       if person.iconID is not None)
        aliases.extend(person.logoID for person in people
                       if person.logoID is not None)
        aliases.extend(person.mugshotID for person in people
                       if person.mugshotID is not None)
        if not aliases:
            return
        # Listify, since this is a pure cache.
        list(LibraryFileAlias.select("LibraryFileAlias.id IN %s"
             % sqlvalues(aliases), prejoins=["content"]))

    def getPrecachedPersonsFromIDs(
        self, person_ids, need_karma=False, need_ubuntu_coc=False,
        need_location=False, need_archive=False,
        need_preferred_email=False, need_validity=False, need_icon=False):
        """See `IPersonSet`."""
        origin = [Person]
        conditions = [
            Person.id.is_in(person_ids)]
        return self._getPrecachedPersons(
            origin, conditions,
            need_karma=need_karma, need_ubuntu_coc=need_ubuntu_coc,
            need_location=need_location, need_archive=need_archive,
            need_preferred_email=need_preferred_email,
            need_validity=need_validity, need_icon=need_icon)

    def _getPrecachedPersons(
        self, origin, conditions, store=None,
        need_karma=False, need_ubuntu_coc=False,
        need_location=False, need_archive=False, need_preferred_email=False,
        need_validity=False, need_icon=False):
        """Lookup all members of the team with optional precaching.

        :param store: Provide ability to specify the store.
        :param origin: List of storm tables and joins. This list will be
            appended to. The Person table is required.
        :param conditions: Storm conditions for tables in origin.
        :param need_karma: The karma attribute will be cached.
        :param need_ubuntu_coc: The is_ubuntu_coc_signer attribute will be
            cached.
        :param need_location: The location attribute will be cached.
        :param need_archive: The archive attribute will be cached.
        :param need_preferred_email: The preferred email attribute will be
            cached.
        :param need_validity: The is_valid attribute will be cached.
        :param need_icon: Cache the persons' icons so that their URLs can
            be generated without further reference to the database.
        """
        if store is None:
            store = IStore(Person)
        columns = [Person]
        decorators = []
        if need_karma:
            # New people have no karmatotalcache rows.
            origin.append(
                LeftJoin(KarmaTotalCache,
                    KarmaTotalCache.person == Person.id))
            columns.append(KarmaTotalCache)
        if need_ubuntu_coc:
            columns.append(Alias(Exists(Select(SignedCodeOfConduct,
                And(Person._is_ubuntu_coc_signer_condition(),
                    SignedCodeOfConduct.ownerID == Person.id))),
                name='is_ubuntu_coc_signer'))
        if need_location:
            # New people have no location rows
            origin.append(
                LeftJoin(PersonLocation,
                    PersonLocation.person == Person.id))
            columns.append(PersonLocation)
        if need_archive:
            # Not everyone has PPAs.
            # It would be nice to cleanly expose the soyuz rules for this to
            # avoid duplicating the relationships.
            archive_conditions = Or(
                Archive.id == None,
                And(
                    Archive.owner == Person.id,
                    Archive.id == Select(
                        tables=Archive,
                        columns=Min(Archive.id),
                        where=And(
                            Archive.purpose == ArchivePurpose.PPA,
                            Archive.owner == Person.id))))
            origin.append(
                LeftJoin(Archive, archive_conditions))
            columns.append(Archive)

        # Checking validity requires having a preferred email.
        if need_preferred_email and not need_validity:
            # Teams don't have email, so a left join
            origin.append(
                LeftJoin(EmailAddress, EmailAddress.person == Person.id))
            columns.append(EmailAddress)
            conditions = And(conditions,
                Or(EmailAddress.status == None,
                   EmailAddress.status == EmailAddressStatus.PREFERRED))
        if need_validity:
            valid_stuff = Person._validity_queries()
            origin.extend(valid_stuff["joins"])
            columns.extend(valid_stuff["tables"])
            decorators.extend(valid_stuff["decorators"])
        if need_icon:
            IconAlias = ClassAlias(LibraryFileAlias, "LibraryFileAlias")
            origin.append(LeftJoin(IconAlias, Person.icon == IconAlias.id))
            columns.append(IconAlias)
        if len(columns) == 1:
            column = columns[0]
            # Return a simple ResultSet
            return store.using(*origin).find(column, conditions)
        # Adapt the result into a cached Person.
        columns = tuple(columns)
        raw_result = store.using(*origin).find(columns, conditions)

        def prepopulate_person(row):
            result = row[0]
            cache = get_property_cache(result)
            index = 1
            #-- karma caching
            if need_karma:
                karma = row[index]
                index += 1
                if karma is None:
                    karma_total = 0
                else:
                    karma_total = karma.karma_total
                cache.karma = karma_total
            #-- ubuntu code of conduct signer status caching.
            if need_ubuntu_coc:
                signed = row[index]
                index += 1
                cache.is_ubuntu_coc_signer = signed
            #-- location caching
            if need_location:
                location = row[index]
                index += 1
                cache.location = location
            #-- archive caching
            if need_archive:
                archive = row[index]
                index += 1
                cache.archive = archive
            #-- preferred email caching
            if need_preferred_email and not need_validity:
                email = row[index]
                index += 1
                cache.preferredemail = email
            for decorator in decorators:
                column = row[index]
                index += 1
                decorator(result, column)
            return result
        return DecoratedResultSet(raw_result,
            result_decorator=prepopulate_person)


# Provide a storm alias from Person to Owner. This is useful in queries on
# objects that have more than just an owner associated with them.
Owner = ClassAlias(Person, 'Owner')


class PersonLanguage(SQLBase):
    _table = 'PersonLanguage'

    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)
    language = ForeignKey(foreignKey='Language', dbName='language',
                          notNull=True)


class SSHKey(SQLBase):
    implements(ISSHKey)
    _defaultOrder = ["person", "keytype", "keytext"]

    _table = 'SSHKey'

    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)
    keytype = EnumCol(dbName='keytype', notNull=True, enum=SSHKeyType)
    keytext = StringCol(dbName='keytext', notNull=True)
    comment = StringCol(dbName='comment', notNull=True)


class SSHKeySet:
    implements(ISSHKeySet)

    def new(self, person, sshkey):
        try:
            kind, keytext, comment = sshkey.split(' ', 2)
        except (ValueError, AttributeError):
            raise SSHKeyAdditionError

        if not (kind and keytext and comment):
            raise SSHKeyAdditionError

        process = subprocess.Popen(
            '/usr/bin/ssh-vulnkey -', shell=True, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = process.communicate(sshkey.encode('utf-8'))
        if 'compromised' in out.lower():
            raise SSHKeyCompromisedError

        if kind == 'ssh-rsa':
            keytype = SSHKeyType.RSA
        elif kind == 'ssh-dss':
            keytype = SSHKeyType.DSA
        else:
            raise SSHKeyAdditionError

        return SSHKey(person=person, keytype=keytype, keytext=keytext,
                      comment=comment)

    def getByID(self, id, default=None):
        try:
            return SSHKey.get(id)
        except SQLObjectNotFound:
            return default

    def getByPeople(self, people):
        """See `ISSHKeySet`"""
        return SSHKey.select("""
            SSHKey.person IN %s
            """ % sqlvalues([person.id for person in people]))


class WikiName(SQLBase, HasOwnerMixin):
    implements(IWikiName)

    _table = 'WikiName'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    wiki = StringCol(dbName='wiki', notNull=True)
    wikiname = StringCol(dbName='wikiname', notNull=True)

    @property
    def url(self):
        return self.wiki + self.wikiname


class WikiNameSet:
    implements(IWikiNameSet)

    def getByWikiAndName(self, wiki, wikiname):
        """See `IWikiNameSet`."""
        return WikiName.selectOneBy(wiki=wiki, wikiname=wikiname)

    def get(self, id):
        """See `IWikiNameSet`."""
        try:
            return WikiName.get(id)
        except SQLObjectNotFound:
            return None

    def new(self, person, wiki, wikiname):
        """See `IWikiNameSet`."""
        return WikiName(person=person, wiki=wiki, wikiname=wikiname)


class JabberID(SQLBase, HasOwnerMixin):
    implements(IJabberID)

    _table = 'JabberID'
    _defaultOrder = ['jabberid']

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    jabberid = StringCol(dbName='jabberid', notNull=True)


class JabberIDSet:
    implements(IJabberIDSet)

    def new(self, person, jabberid):
        """See `IJabberIDSet`"""
        return JabberID(person=person, jabberid=jabberid)

    def getByJabberID(self, jabberid):
        """See `IJabberIDSet`"""
        return JabberID.selectOneBy(jabberid=jabberid)

    def getByPerson(self, person):
        """See `IJabberIDSet`"""
        return JabberID.selectBy(person=person)


class IrcID(SQLBase, HasOwnerMixin):
    """See `IIrcID`"""
    implements(IIrcID)

    _table = 'IrcID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    network = StringCol(dbName='network', notNull=True)
    nickname = StringCol(dbName='nickname', notNull=True)


class IrcIDSet:
    """See `IIrcIDSet`"""
    implements(IIrcIDSet)

    def get(self, id):
        """See `IIrcIDSet`"""
        try:
            return IrcID.get(id)
        except SQLObjectNotFound:
            return None

    def new(self, person, network, nickname):
        """See `IIrcIDSet`"""
        return IrcID(person=person, network=network, nickname=nickname)


class NicknameGenerationError(Exception):
    """I get raised when something went wrong generating a nickname."""


def _is_nick_registered(nick):
    """Answer the question: is this nick registered?"""
    return PersonSet().getByName(nick) is not None


def generate_nick(email_addr, is_registered=_is_nick_registered):
    """Generate a LaunchPad nick from the email address provided.

    See lp.app.validators.name for the definition of a
    valid nick.

    It is technically possible for this function to raise a
    NicknameGenerationError, but this will only occur if an operator
    has majorly screwed up the name blacklist.
    """
    email_addr = email_addr.strip().lower()

    if not valid_email(email_addr):
        raise NicknameGenerationError("%s is not a valid email address"
                                      % email_addr)

    user = re.match("^(\S+)@(?:\S+)$", email_addr).groups()[0]
    user = user.replace(".", "-").replace("_", "-")

    person_set = PersonSet()

    def _valid_nick(nick):
        if not valid_name(nick):
            return False
        elif is_registered(nick):
            return False
        elif person_set.isNameBlacklisted(nick):
            return False
        else:
            return True

    generated_nick = sanitize_name(user)
    if _valid_nick(generated_nick):
        return generated_nick

    # We seed the random number generator so we get consistent results,
    # making the algorithm repeatable and thus testable.
    random_state = random.getstate()
    random.seed(sum(ord(letter) for letter in generated_nick))
    try:
        attempts = 0
        prefix = ''
        suffix = ''
        mutated_nick = [letter for letter in generated_nick]
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        while attempts < 1000:
            attempts += 1

            # Prefer a nickname with a suffix
            suffix += random.choice(chars)
            if _valid_nick(generated_nick + '-' + suffix):
                return generated_nick + '-' + suffix

            # Next a prefix
            prefix += random.choice(chars)
            if _valid_nick(prefix + '-' + generated_nick):
                return prefix + '-' + generated_nick

            # Or a mutated character
            index = random.randint(0, len(mutated_nick) - 1)
            mutated_nick[index] = random.choice(chars)
            if _valid_nick(''.join(mutated_nick)):
                return ''.join(mutated_nick)

            # Or a prefix + generated + suffix
            if _valid_nick(prefix + '-' + generated_nick + '-' + suffix):
                return prefix + '-' + generated_nick + '-' + suffix

            # Or a prefix + mutated + suffix
            if _valid_nick(
                    prefix + '-' + ''.join(mutated_nick) + '-' + suffix):
                return prefix + '-' + ''.join(mutated_nick) + '-' + suffix

        raise NicknameGenerationError(
            "No nickname could be generated. "
            "This should be impossible to trigger unless some twonk has "
            "registered a match everything regexp in the black list.")

    finally:
        random.setstate(random_state)


@adapter(IAccount)
@implementer(IPerson)
def person_from_account(account):
    """Adapt an `IAccount` into an `IPerson`.

    If there is a current browser request, we cache the looked up Person in
    the request's annotations so that we don't have to hit the DB once again
    when further adaptation is needed.  We know this cache may cross
    transaction boundaries, but this should not be a problem as the Person ->
    Account link can't be changed.

    This cache is necessary because our security adapters may need to adapt
    the Account representing the logged in user into an IPerson multiple
    times.
    """
    request = get_current_browser_request()
    person = None
    # First we try to get the person from the cache, but only if there is a
    # browser request.
    if request is not None:
        cache = request.annotations.setdefault(
            'launchpad.person_to_account_cache', weakref.WeakKeyDictionary())
        person = cache.get(account)

    # If it's not in the cache, then we get it from the database, and in that
    # case, if there is a browser request, we also store that person in the
    # cache.
    if person is None:
        person = IStore(Person).find(Person, account=account).one()
        if request is not None:
            cache[account] = person

    if person is None:
        raise ComponentLookupError()
    return person


@ProxyFactory
def get_recipients(person):
    """Return a set of people who receive email for this Person (person/team).

    If <person> has a preferred email, the set will contain only that
    person.  If <person> doesn't have a preferred email but is a team,
    the set will contain the preferred email address of each member of
    <person>, including indirect members, that has an active account and an
    preferred (active) address.

    Finally, if <person> doesn't have a preferred email and is not a team,
    the set will be empty.
    """
    if person.preferredemail:
        return [person]
    elif person.is_team:
        # Get transitive members of a team that does not itself have a
        # preferred email.
        return _get_recipients_for_team(person)
    else:
        return []


def _get_recipients_for_team(team):
    """Given a team without a preferred email, return recipients.

    Helper for get_recipients, divided out simply to make get_recipients
    easier to understand in broad brush."""
    store = IStore(Person)
    source = store.using(TeamMembership,
                         Join(Person,
                              TeamMembership.personID == Person.id),
                         LeftJoin(EmailAddress,
                                  And(
                                      EmailAddress.person == Person.id,
                                      EmailAddress.status ==
                                        EmailAddressStatus.PREFERRED)),
                         LeftJoin(Account,
                             Person.accountID == Account.id))
    pending_team_ids = [team.id]
    recipient_ids = set()
    seen = set()
    while pending_team_ids:
        # Find Persons that have a preferred email address and an active
        # account, or are a team, or both.
        intermediate_transitive_results = source.find(
            (TeamMembership.personID, EmailAddress.personID),
            In(TeamMembership.status,
               [TeamMembershipStatus.ADMIN.value,
                TeamMembershipStatus.APPROVED.value]),
            In(TeamMembership.teamID, pending_team_ids),
            Or(
                And(EmailAddress.personID != None,
                    Account.status == AccountStatus.ACTIVE),
                Person.teamownerID != None)).config(distinct=True)
        next_ids = []
        for (person_id,
             preferred_email_marker) in intermediate_transitive_results:
            if preferred_email_marker is None:
                # This is a team without a preferred email address.
                if person_id not in seen:
                    next_ids.append(person_id)
                    seen.add(person_id)
            else:
                recipient_ids.add(person_id)
        pending_team_ids = next_ids
    return getUtility(IPersonSet).getPrecachedPersonsFromIDs(
        recipient_ids,
        need_validity=True,
        need_preferred_email=True)
