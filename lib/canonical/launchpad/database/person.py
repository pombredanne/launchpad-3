# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
# vars() causes W0612
# pylint: disable-msg=E0611,W0212,W0612,C0322

"""Implementation classes for a Person."""

__metaclass__ = type
__all__ = [
    'generate_nick',
    'IrcID',
    'IrcIDSet',
    'JabberID',
    'JabberIDSet',
    'Owner',
    'Person',
    'PersonLanguage',
    'PersonSet',
    'SSHKey',
    'SSHKeySet',
    'ValidPersonCache',
    'WikiName',
    'WikiNameSet']

from datetime import datetime, timedelta
from operator import attrgetter
import pytz
import random
import re

from zope.lifecycleevent import ObjectCreatedEvent
from zope.interface import alsoProvides, implementer, implements
from zope.component import adapter, getUtility
from zope.component.interfaces import ComponentLookupError
from zope.event import notify
from zope.security.proxy import ProxyFactory, removeSecurityProxy
from sqlobject import (
    BoolCol, ForeignKey, IntCol, SQLMultipleJoin, SQLObjectNotFound,
    SQLRelatedJoin, StringCol)
from sqlobject.sqlbuilder import AND, OR, SQLConstant
from storm.store import EmptyResultSet, Store
from storm.expr import And, Join
from storm.info import ClassAlias

from canonical.config import config
from canonical.database import postgresql
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor, quote, quote_like, sqlvalues, SQLBase)

from canonical.cachedproperty import cachedproperty

from canonical.lazr.utils import safe_hasattr

from canonical.launchpad.database.account import Account
from lp.answers.model.answercontact import AnswerContact
from canonical.launchpad.database.bugtarget import HasBugsBase
from canonical.launchpad.database.karma import KarmaCategory
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.oauth import (
    OAuthAccessToken, OAuthRequestToken)
from canonical.launchpad.database.personlocation import PersonLocation
from canonical.launchpad.database.structuralsubscription import (
    StructuralSubscription)
from canonical.launchpad.database.translationrelicensingagreement import (
    TranslationRelicensingAgreement)
from canonical.launchpad.event.karma import KarmaAssignedEvent
from canonical.launchpad.event.team import JoinTeamEvent, TeamInvitationEvent
from canonical.launchpad.helpers import (
    get_contact_email_addresses, get_email_template, shortlist)

from canonical.launchpad.interfaces import IMasterObject, IMasterStore
from canonical.launchpad.interfaces.account import (
    AccountCreationRationale, AccountStatus, IAccount, IAccountSet,
    INACTIVE_ACCOUNT_STATUSES)
from canonical.launchpad.interfaces.archive import ArchivePurpose
from canonical.launchpad.interfaces.archivepermission import (
    IArchivePermissionSet)
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus, IBranchMergeProposalGetter)
from canonical.launchpad.interfaces.bugtask import (
    BugTaskSearchParams, IBugTaskSet)
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.codeofconduct import (
    ISignedCodeOfConductSet)
from canonical.launchpad.interfaces.distribution import IDistribution
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus, IEmailAddress, IEmailAddressSet, InvalidEmailAddress)
from canonical.launchpad.interfaces.gpg import IGPGKeySet
from canonical.launchpad.interfaces.hwdb import IHWSubmissionSet
from canonical.launchpad.interfaces.irc import IIrcID, IIrcIDSet
from canonical.launchpad.interfaces.jabber import IJabberID, IJabberIDSet
from canonical.launchpad.interfaces.launchpad import (
    IHasIcon, IHasLogo, IHasMugshot, ILaunchpadCelebrities)
from canonical.launchpad.interfaces.launchpadstatistic import (
    ILaunchpadStatisticSet)
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.interfaces.mailinglist import (
    IMailingListSet, MailingListStatus, PostedMessageStatus)
from canonical.launchpad.interfaces.mailinglistsubscription import (
    MailingListAutoSubscribePolicy)
from canonical.launchpad.interfaces.person import (
    IPerson, IPersonSet, ITeam, ImmutableVisibilityError, InvalidName,
    JoinNotAllowed, NameAlreadyTaken, PersonCreationRationale,
    PersonVisibility, PersonalStanding, TeamMembershipRenewalPolicy,
    TeamSubscriptionPolicy)
from canonical.launchpad.interfaces.personnotification import (
    IPersonNotificationSet)
from canonical.launchpad.interfaces.pillar import IPillarNameSet
from canonical.launchpad.interfaces.product import IProduct
from canonical.launchpad.interfaces.project import IProject
from canonical.launchpad.interfaces.revision import IRevisionSet
from canonical.launchpad.interfaces.salesforce import (
    ISalesforceVoucherProxy, VOUCHER_STATUSES)
from canonical.launchpad.interfaces.specification import (
    SpecificationDefinitionStatus, SpecificationFilter,
    SpecificationImplementationStatus, SpecificationSort)
from canonical.launchpad.interfaces import IStore
from canonical.launchpad.interfaces.ssh import ISSHKey, ISSHKeySet, SSHKeyType
from canonical.launchpad.interfaces.teammembership import (
    TeamMembershipStatus)
from canonical.launchpad.interfaces.translationgroup import (
    ITranslationGroupSet)
from canonical.launchpad.interfaces.translator import ITranslatorSet
from canonical.launchpad.interfaces.wikiname import IWikiName, IWikiNameSet
from canonical.launchpad.webapp.interfaces import (
    ILaunchBag, IStoreSelector, AUTH_STORE, MASTER_FLAVOR)

from canonical.launchpad.database.archive import Archive
from canonical.launchpad.database.codeofconduct import SignedCodeOfConduct
from canonical.launchpad.database.bugtask import BugTask
from canonical.launchpad.database.emailaddress import (
    EmailAddress, HasOwnerMixin)
from canonical.launchpad.database.karma import KarmaCache, KarmaTotalCache
from canonical.launchpad.database.logintoken import LoginToken
from canonical.launchpad.database.pillar import PillarName
from canonical.launchpad.database.pofiletranslator import POFileTranslator
from canonical.launchpad.database.karma import KarmaAction, Karma
from canonical.launchpad.database.mentoringoffer import MentoringOffer
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.database.teammembership import (
    TeamMembership, TeamMembershipSet, TeamParticipation)
from lp.answers.model.question import QuestionPersonSearch

from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.validators.name import sanitize_name, valid_name
from canonical.launchpad.validators.person import validate_public_person

from lp.answers.interfaces.questioncollection import (
    QUESTION_STATUS_DEFAULT_SEARCH)

class ValidPersonCache(SQLBase):
    """Flags if a Person is active and usable in Launchpad.

    This is readonly, as this is a view in the database.
    """
    # Look Ma, no columns! (apart from id)


def validate_person_visibility(person, attr, value):
    """Validate changes in visibility.

    * Prevent teams with inconsistent connections from being made private
    * Prevent private teams with mailing lists from going public
    """
    mailing_list = getUtility(IMailingListSet).get(person.name)

    if (value == PersonVisibility.PUBLIC and
        person.visibility == PersonVisibility.PRIVATE_MEMBERSHIP and
        mailing_list is not None and
        mailing_list.status != MailingListStatus.PURGED):
        raise ImmutableVisibilityError(
            'This team cannot be made public since it has a mailing list')

    if value != PersonVisibility.PUBLIC:
        warning = person.visibility_consistency_warning
        if warning is not None:
            raise ImmutableVisibilityError(warning)

    return value


class Person(
    SQLBase, HasBugsBase, HasSpecificationsMixin, HasTranslationImportsMixin):
    """A Person."""

    implements(IPerson, IHasIcon, IHasLogo, IHasMugshot)

    sortingColumns = SQLConstant(
        "person_sort_key(Person.displayname, Person.name)")
    # When doing any sort of set operations (union, intersect, except_) with
    # SQLObject we can't use sortingColumns because the table name Person is
    # not available in that context, so we use this one.
    _sortingColumnsForSetOperations = SQLConstant(
        "person_sort_key(displayname, name)")
    _defaultOrder = sortingColumns

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
        return '<Person at 0x%x %s (%s)>' % (
            id(self), self.name, self.displayname)

    def _sync_displayname(self, attr, value):
        """Update any related Account.displayname.

        We can't do this in a DB trigger as soon the Account table will
        in a separate database to the Person table.
        """
        if self.accountID is not None:
            auth_store = getUtility(IStoreSelector).get(
                AUTH_STORE, MASTER_FLAVOR)
            account = auth_store.get(Account, self.accountID)
            if account.displayname != value:
                account.displayname = value
        return value

    displayname = StringCol(dbName='displayname', notNull=True,
                            storm_validator=_sync_displayname)

    teamdescription = StringCol(dbName='teamdescription', default=None)
    homepage_content = StringCol(default=None)
    icon = ForeignKey(
        dbName='icon', foreignKey='LibraryFileAlias', default=None)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    mugshot = ForeignKey(
        dbName='mugshot', foreignKey='LibraryFileAlias', default=None)

    # XXX StuartBishop 2008-05-13 bug=237280: The password,
    # account_status and account_status_comment properties should go. Note
    # that they override the current strict controls on Account, allowing
    # access via Person to use the less strict controls on that interface.
    # Part of the process of removing these methods from Person will be
    # loosening the permissions on Account or fixing the callsites.
    def _get_password(self):
        # We have to remove the security proxy because the password is
        # needed before we are authenticated. I'm not overly worried because
        # this method is scheduled for demolition -- StuartBishop 20080514
        from canonical.launchpad.database.account import AccountPassword
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

    city = StringCol(default=None)
    phone = StringCol(default=None)
    country = ForeignKey(dbName='country', foreignKey='Country', default=None)
    province = StringCol(default=None)
    postcode = StringCol(default=None)
    addressline1 = StringCol(default=None)
    addressline2 = StringCol(default=None)
    organization = StringCol(default=None)

    teamowner = ForeignKey(dbName='teamowner', foreignKey='Person',
                           default=None,
                           storm_validator=validate_public_person)

    sshkeys = SQLMultipleJoin('SSHKey', joinColumn='person')

    renewal_policy = EnumCol(
        enum=TeamMembershipRenewalPolicy,
        default=TeamMembershipRenewalPolicy.NONE)
    subscriptionpolicy = EnumCol(
        dbName='subscriptionpolicy',
        enum=TeamSubscriptionPolicy,
        default=TeamSubscriptionPolicy.MODERATED)
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

    ownedBounties = SQLMultipleJoin('Bounty', joinColumn='owner',
        orderBy='id')
    reviewerBounties = SQLMultipleJoin('Bounty', joinColumn='reviewer',
        orderBy='id')
    # XXX: matsubara 2006-03-06 bug=33935:
    # Is this really needed? There's no attribute 'claimant' in the Bounty
    # database class or interface, but the column exists in the database.
    claimedBounties = SQLMultipleJoin('Bounty', joinColumn='claimant',
        orderBy='id')
    subscribedBounties = SQLRelatedJoin('Bounty', joinColumn='person',
        otherColumn='bounty', intermediateTable='BountySubscription',
        orderBy='id')
    signedcocs = SQLMultipleJoin('SignedCodeOfConduct', joinColumn='owner')
    ircnicknames = SQLMultipleJoin('IrcID', joinColumn='person')
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

    @cachedproperty('_languages_cache')
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
        return self._languages_cache

    def setLanguagesCache(self, languages):
        """Set this person's cached languages.

        Order them by name if necessary.
        """
        self._languages_cache = sorted(
            languages, key=attrgetter('englishname'))

    def deleteLanguagesCache(self):
        """Delete this person's cached languages, if it exists."""
        if safe_hasattr(self, '_languages_cache'):
            del self._languages_cache

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
        assert not self.is_team, "Can't convert a team to a team."
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
        return OAuthAccessToken.select("""
            person = %s
            AND (date_expires IS NULL OR date_expires > %s)
            """ % sqlvalues(self, UTC_NOW))

    @property
    def oauth_request_tokens(self):
        """See `IPerson`."""
        return OAuthRequestToken.select("""
            person = %s
            AND (date_expires IS NULL OR date_expires > %s)
            """ % sqlvalues(self, UTC_NOW))

    @cachedproperty('_location')
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
            self._location = PersonLocation(person=self, visible=visible)
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
            self._location = PersonLocation(
                person=self, time_zone=time_zone, latitude=latitude,
                longitude=longitude, last_modified_by=user)

        # Make a note that we need to tell this person that their
        # information was updated by the user. We can only do this if we
        # have a validated email address for this person.
        if user != self and self.preferredemail is not None:
            mail_text = get_email_template('person-location-modified.txt')
            mail_text = mail_text % {
                'actor': user.name,
                'actor_browsername': user.browsername,
                'person': self.name}
            subject = '%s updated your location and time zone' % (
                user.browsername)
            getUtility(IPersonNotificationSet).addNotification(
                self, subject, mail_text)

    def get_translations_relicensing_agreement(self):
        """Return whether translator agrees to relicense their translations.

        If she has made no explicit decision yet, return None.
        """
        relicensing_agreement = TranslationRelicensingAgreement.selectOneBy(
            person=self)
        if relicensing_agreement is None:
            return None
        else:
            return relicensing_agreement.allow_relicensing

    def set_translations_relicensing_agreement(self, value):
        """Set a translations relicensing decision by translator.

        If she has already made a decision, overrides it with the new one.
        """
        relicensing_agreement = TranslationRelicensingAgreement.selectOneBy(
            person=self)
        if relicensing_agreement is None:
            relicensing_agreement = TranslationRelicensingAgreement(
                person=self,
                allow_relicensing=value)
        else:
            relicensing_agreement.allow_relicensing = value

    translations_relicensing_agreement = property(
        get_translations_relicensing_agreement,
        set_translations_relicensing_agreement,
        doc="See `IPerson`.")

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

    # mentorship
    @property
    def mentoring_offers(self):
        """See `IPerson`"""
        return MentoringOffer.select("""MentoringOffer.id IN
        (SELECT MentoringOffer.id
            FROM MentoringOffer
            LEFT OUTER JOIN BugTask ON
                MentoringOffer.bug = BugTask.bug
            LEFT OUTER JOIN Bug ON
                BugTask.bug = Bug.id
            LEFT OUTER JOIN Specification ON
                MentoringOffer.specification = Specification.id
            WHERE
                MentoringOffer.owner = %s
                """ % sqlvalues(self.id) + """ AND (
                BugTask.id IS NULL OR NOT
                (Bug.private IS TRUE OR
                  (""" + BugTask.completeness_clause +"""))) AND (
                Specification.id IS NULL OR NOT
                (""" + Specification.completeness_clause +")))",
            )

    @property
    def team_mentorships(self):
        """See `IPerson`"""
        return MentoringOffer.select("""MentoringOffer.id IN
        (SELECT MentoringOffer.id
            FROM MentoringOffer
            JOIN TeamParticipation ON
                MentoringOffer.team = TeamParticipation.person
            LEFT OUTER JOIN BugTask ON
                MentoringOffer.bug = BugTask.bug
            LEFT OUTER JOIN Bug ON
                BugTask.bug = Bug.id
            LEFT OUTER JOIN Specification ON
                MentoringOffer.specification = Specification.id
            WHERE
                TeamParticipation.team = %s
                """ % sqlvalues(self.id) + """ AND (
                BugTask.id IS NULL OR NOT
                (Bug.private IS TRUE OR
                  (""" + BugTask.completeness_clause +"""))) AND (
                Specification.id IS NULL OR NOT
                (""" + Specification.completeness_clause +")))",
            )

    @property
    def unique_displayname(self):
        """See `IPerson`."""
        return "%s (%s)" % (self.displayname, self.name)

    @property
    def browsername(self):
        """See `IPersonPublic`."""
        return self.displayname

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
        completeness =  Specification.completeness_clause

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

    def searchQuestions(self, search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, participation=None,
                        needs_attention=None):
        """See `IPerson`."""
        return QuestionPersonSearch(
                person=self,
                search_text=search_text,
                status=status, language=language, sort=sort,
                participation=participation,
                needs_attention=needs_attention
                ).getResults()

    def getQuestionLanguages(self):
        """See `IQuestionTarget`."""
        return set(Language.select(
            """Language.id = language AND Question.id IN (
            SELECT id FROM Question
                      WHERE owner = %(personID)s OR answerer = %(personID)s OR
                           assignee = %(personID)s
            UNION SELECT question FROM QuestionSubscription
                  WHERE person = %(personID)s
            UNION SELECT question
                  FROM QuestionMessage JOIN Message ON (message = Message.id)
                  WHERE owner = %(personID)s
            )""" % sqlvalues(personID=self.id),
            clauseTables=['Question'], distinct=True))

    @property
    def translatable_languages(self):
        """See `IPerson`."""
        return Language.select("""
            Language.id = PersonLanguage.language AND
            PersonLanguage.person = %s AND
            Language.code <> 'en' AND
            Language.visible""" % quote(self),
            clauseTables=['PersonLanguage'], orderBy='englishname')

    def getDirectAnswerQuestionTargets(self):
        """See `IPerson`."""
        answer_contacts = AnswerContact.select(
            'person = %s' % sqlvalues(self))
        return self._getQuestionTargetsFromAnswerContacts(answer_contacts)

    def getTeamAnswerQuestionTargets(self):
        """See `IPerson`."""
        answer_contacts = AnswerContact.select(
            '''AnswerContact.person = TeamParticipation.team
            AND TeamParticipation.person = %(personID)s
            AND AnswerContact.person != %(personID)s''' % sqlvalues(
                personID=self.id),
            clauseTables=['TeamParticipation'], distinct=True)
        return self._getQuestionTargetsFromAnswerContacts(answer_contacts)

    def _getQuestionTargetsFromAnswerContacts(self, answer_contacts):
        """Return a list of active IQuestionTargets.

        :param answer_contacts: an iterable of `AnswerContact`s.
        :return: a list of active `IQuestionTarget`s.
        :raise AssertionError: if the IQuestionTarget is not a `Product`,
            `Distribution`, or `SourcePackage`.
        """
        targets = set()
        for answer_contact in answer_contacts:
            if answer_contact.product is not None:
                target = answer_contact.product
                pillar = target
            elif answer_contact.sourcepackagename is not None:
                assert answer_contact.distribution is not None, (
                    "Missing distribution.")
                distribution = answer_contact.distribution
                target = distribution.getSourcePackage(
                    answer_contact.sourcepackagename)
                pillar = distribution
            elif answer_contact.distribution is not None:
                target = answer_contact.distribution
                pillar = target
            else:
                raise AssertionError('Unknown IQuestionTarget.')

            if pillar.active:
                # Deactivated pillars are not valid IQuestionTargets.
                targets.add(target)

        return list(targets)

    # XXX: Tom Berger 2008-04-14 bug=191799:
    # The implementation of these functions
    # is no longer appropriate, since it now relies on subscriptions,
    # rather than package bug supervisors.
    def getBugSubscriberPackages(self):
        """See `IPerson`."""
        packages = [sub.target for sub in self.structural_subscriptions
                    if (sub.distribution is not None and
                        sub.sourcepackagename is not None)]
        packages.sort(key=lambda x: x.name)
        return packages

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
        return self.teamowner is not None

    def isTeam(self):
        """Deprecated. Use is_team instead."""
        return self.teamowner is not None

    def getMergeProposals(self, status=None, visible_by_user=None):
        """See `IPerson`."""
        if not status:
            status = (
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW,
                BranchMergeProposalStatus.WORK_IN_PROGRESS)

        return getUtility(IBranchMergeProposalGetter).getProposalsForContext(
            self, status, visible_by_user=None)

    @property
    def mailing_list(self):
        """See `IPerson`."""
        return getUtility(IMailingListSet).get(self.name)

    def _customizeSearchParams(self, search_params):
        """No-op, to satisfy a requirement of HasBugsBase."""
        pass

    def searchTasks(self, search_params, *args, **kwargs):
        """See `IHasBugs`."""
        if len(kwargs) > 0:
            # if keyword arguments are supplied, use the deault
            # implementation in HasBugsBase.
            return HasBugsBase.searchTasks(self, search_params, **kwargs)
        else:
            # Otherwise pass all positional arguments to the
            # implementation in BugTaskSet.
            return getUtility(IBugTaskSet).search(search_params, *args)

    def getProjectsAndCategoriesContributedTo(self, limit=5):
        """See `IPerson`."""
        contributions = []
        results = self._getProjectsWithTheMostKarma(limit=limit)
        for pillar_name, karma in results:
            pillar = getUtility(IPillarNameSet).getByName(pillar_name)
            contributions.append(
                {'project': pillar,
                 'categories': self._getContributedCategories(pillar)})
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
        query = """
            SELECT name
            FROM product, teamparticipation
            WHERE teamparticipation.person = %(person)s
                AND (driver = teamparticipation.team
                     OR owner = teamparticipation.team)

            UNION

            SELECT name
            FROM project, teamparticipation
            WHERE teamparticipation.person = %(person)s
                AND (driver = teamparticipation.team
                     OR owner = teamparticipation.team)

            UNION

            SELECT name
            FROM distribution, teamparticipation
            WHERE teamparticipation.person = %(person)s
                AND (driver = teamparticipation.team
                     OR owner = teamparticipation.team)
            """ % sqlvalues(person=self)
        cur = cursor()
        cur.execute(query)
        names = [sqlvalues(str(name)) for [name] in cur.fetchall()]
        if not names:
            return PillarName.select("1=2")
        quoted_names = ','.join([name for [name] in names])
        return PillarName.select(
            "PillarName.name IN (%s) AND PillarName.active IS TRUE" %
            quoted_names, prejoins=['distribution', 'project', 'product'],
            orderBy=['PillarName.distribution', 'PillarName.project',
                     'PillarName.product'])

    def getOwnedProjects(self, match_name=None):
        """See `IPerson`."""
        # Import here to work around a circular import problem.
        from canonical.launchpad.database import Product

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

    def getCommercialSubscriptionVouchers(self):
        """See `IPerson`."""
        voucher_proxy = getUtility(ISalesforceVoucherProxy)
        commercial_vouchers = voucher_proxy.getAllVouchers(self)
        unredeemed_commercial_vouchers = []
        redeemed_commercial_vouchers = []
        for voucher in commercial_vouchers:
            assert voucher.status in VOUCHER_STATUSES, (
                "Voucher %s has unrecognized status %s" %
                (voucher.voucher_id, voucher.status))
            if voucher.status == 'Redeemed':
                redeemed_commercial_vouchers.append(voucher)
            else:
                unredeemed_commercial_vouchers.append(voucher)
        return (unredeemed_commercial_vouchers,
                redeemed_commercial_vouchers)

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

    @property
    def karma(self):
        """See `IPerson`."""
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

    @property
    def is_valid_person(self):
        """See `IPerson`."""
        if self.is_team:
            return False
        try:
            ValidPersonCache.get(self.id)
            return True
        except SQLObjectNotFound:
            return False

    def assignKarma(self, action_name, product=None, distribution=None,
                    sourcepackagename=None):
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

        karma = Karma(
            person=self, action=action, product=product,
            distribution=distribution, sourcepackagename=sourcepackagename)
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
        if isinstance(team, str):
            team = PersonSet().getByName(team)

        if self._inTeam_cache is None: # Initialize cache
            self._inTeam_cache = {}
        else:
            try:
                return self._inTeam_cache[team.id] # Return from cache
            except KeyError:
                pass # Or fall through

        tp = TeamParticipation.selectOneBy(team=team, person=self)
        if tp is not None or self.id == team.teamownerID:
            in_team = True
        elif team.is_team and not team.teamowner.inTeam(team):
            # The owner is not a member but must retain his rights over
            # this team. This person may be a member of the owner, and in this
            # case it'll also have rights over this team.
            in_team = self.inTeam(team.teamowner)
        else:
            in_team = False

        self._inTeam_cache[team.id] = in_team
        return in_team

    def hasParticipationEntryFor(self, team):
        """See `IPerson`."""
        return bool(TeamParticipation.selectOneBy(person=self, team=team))

    def leave(self, team):
        """See `IPerson`."""
        assert not ITeam.providedBy(self)

        self._inTeam_cache = {} # Flush the cache used by the inTeam method

        active = [TeamMembershipStatus.ADMIN, TeamMembershipStatus.APPROVED]
        tm = TeamMembership.selectOneBy(person=self, team=team)
        if tm is None or tm.status not in active:
            # Ok, we're done. You are not an active member and still
            # not being.
            return

        tm.setStatus(TeamMembershipStatus.DEACTIVATED, self)

    def join(self, team, requester=None, may_subscribe_to_list=True):
        """See `IPerson`."""
        if self in team.activemembers:
            return

        if requester is None:
            assert not self.is_team, (
                "You need to specify a reviewer when a team joins another.")
            requester = self

        expired = TeamMembershipStatus.EXPIRED
        proposed = TeamMembershipStatus.PROPOSED
        approved = TeamMembershipStatus.APPROVED
        declined = TeamMembershipStatus.DECLINED
        deactivated = TeamMembershipStatus.DEACTIVATED

        if team.subscriptionpolicy == TeamSubscriptionPolicy.RESTRICTED:
            raise JoinNotAllowed("This is a restricted team")
        elif team.subscriptionpolicy == TeamSubscriptionPolicy.MODERATED:
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
        for person in self.getDirectAdministrators():
            to_addrs.update(get_contact_email_addresses(person))
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
        if person.is_team:
            assert not self.hasParticipationEntryFor(person), (
                "Team '%s' is a member of '%s'. As a consequence, '%s' can't "
                "be added as a member of '%s'"
                % (self.name, person.name, person.name, self.name))
            # By default, teams can only be invited as members, meaning that
            # one of the team's admins will have to accept the invitation
            # before the team is made a member. If force_team_add is True,
            # though, then we'll add a team as if it was a person.
            if not force_team_add:
                status = TeamMembershipStatus.INVITED
                event = TeamInvitationEvent

        expires = self.defaultexpirationdate
        tm = TeamMembership.selectOneBy(person=person, team=self)
        if tm is None:
            tm = TeamMembershipSet().new(
                person, self, status, reviewer, dateexpires=expires,
                comment=comment)
            # Accessing the id attribute ensures that the team
            # creation has been flushed to the database.
            tm_id = tm.id
            notify(event(person, self))
        else:
            # We can't use tm.setExpirationDate() here because the reviewer
            # here will be the member themselves when they join an OPEN team.
            tm.dateexpires = expires
            tm.setStatus(status, reviewer, comment)

        if not person.is_team and may_subscribe_to_list:
            person.autoSubscribeToMailingList(self.mailing_list,
                                              requester=reviewer)

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

    def deactivateAllMembers(self, comment, reviewer):
        """Deactivate all members of this team."""
        assert self.is_team, "This method is only available for teams."
        assert reviewer.inTeam(getUtility(ILaunchpadCelebrities).admin), (
            "Only Launchpad admins can deactivate all members of a team")
        for membership in self.member_memberships:
            membership.setStatus(
                TeamMembershipStatus.DEACTIVATED, reviewer, comment)

    def setMembershipData(self, person, status, reviewer, expires=None,
                          comment=None):
        """See `IPerson`."""
        tm = TeamMembership.selectOneBy(person=person, team=self)
        assert tm is not None
        tm.setExpirationDate(expires, reviewer)
        tm.setStatus(status, reviewer, comment=comment)

    def getAdministratedTeams(self):
        """See `IPerson`."""
        owner_of_teams = Person.select('''
            Person.teamowner = TeamParticipation.team
            AND TeamParticipation.person = %s
            ''' % sqlvalues(self),
            clauseTables=['TeamParticipation'])
        admin_of_teams = Person.select('''
            Person.id = TeamMembership.team
            AND TeamMembership.status = %(admin)s
            AND TeamMembership.person = TeamParticipation.team
            AND TeamParticipation.person = %(person)s
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

    @property
    def wiki_names(self):
        """See `IPerson`."""
        result =  Store.of(self).find(WikiName, WikiName.person == self.id)
        return result.order_by(WikiName.wiki, WikiName.wikiname)

    @property
    def title(self):
        """See `IPerson`."""
        return self.browsername

    @property
    def allmembers(self):
        """See `IPerson`."""
        query = """
            Person.id = TeamParticipation.person AND
            TeamParticipation.team = %s AND
            TeamParticipation.person != %s
            """ % sqlvalues(self.id, self.id)
        return Person.select(query, clauseTables=['TeamParticipation'])

    def _getMembersWithPreferredEmails(self, include_teams=False):
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

    def getMembersWithPreferredEmails(self, include_teams=False):
        """See `IPerson`."""
        result = self._getMembersWithPreferredEmails(
            include_teams=include_teams)
        person_list = []
        for person, email in result:
            person._preferredemail_cached = email
            person_list.append(person)
        return person_list

    def getMembersWithPreferredEmailsCount(self, include_teams=False):
        """See `IPerson`."""
        result = self._getMembersWithPreferredEmails(
            include_teams=include_teams)
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

    # XXX: kiko 2005-10-07:
    # myactivememberships should be renamed to team_memberships and be
    # described as the set of memberships for the object's teams.
    @property
    def myactivememberships(self):
        """See `IPerson`."""
        return TeamMembership.select("""
            TeamMembership.person = %s AND status in %s AND
            Person.id = TeamMembership.team
            """ % sqlvalues(self.id, [TeamMembershipStatus.APPROVED,
                                      TeamMembershipStatus.ADMIN]),
            clauseTables=['Person'],
            orderBy=Person.sortingColumns)

    @property
    def mapped_participants(self):
        """See `IPersonViewRestricted`."""
        locations = PersonLocation.select("""
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
            prejoins=['person',])
        # Pre-cache this location against its person.  Since we'll always
        # iterate over all persons returned by this property (to build the map
        # of team members), it becomes more important to cache their locations
        # than to return a lazy SelectResults (or similar) object that only
        # fetches the rows when they're needed.
        for location in locations:
            location.person._location = location
        participants = set(location.person for location in locations)
        # Cache the ValidPersonCache query for all mapped participants.
        if len(participants) > 0:
            sql = "id IN (%s)" % ",".join(sqlvalues(*participants))
            list(ValidPersonCache.select(sql))
        return list(participants)

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
    def open_membership_invitations(self):
        """See `IPerson`."""
        return TeamMembership.select("""
            TeamMembership.person = %s AND status = %s
            AND Person.id = TeamMembership.team
            """ % sqlvalues(self.id, TeamMembershipStatus.INVITED),
            clauseTables=['Person'],
            orderBy=Person.sortingColumns)

    def activateAccount(self, comment, password, preferred_email):
        """See `IPersonSpecialRestricted`.

        :raise AssertionError: if the Person is a Team.
        """
        # XXX sinzui 2008-07-14 bug=248518:
        # This method would assert the password is not None, but
        # setPreferredEmail() passes the Person's current password.
        if self.is_team:
            raise AssertionError(
                "Teams cannot be activated with this method.")
        account = IMasterStore(Account).get(Account, self.accountID)
        account.status = AccountStatus.ACTIVE
        account.status_comment = comment
        account.password = password
        if preferred_email is not None:
            self.validateAndEnsurePreferredEmail(
                IMasterObject(preferred_email))
        # sync so validpersoncache updates.
        account.sync()

    def deactivateAccount(self, comment):
        """See `IPersonSpecialRestricted`."""
        assert self.is_valid_person, (
            "You can only deactivate an account of a valid person.")

        for membership in self.myactivememberships:
            self.leave(membership.team)

        # Deactivate CoC signatures, invalidate email addresses, unassign bug
        # tasks and specs and reassign pillars and teams.
        for coc in self.signedcocs:
            coc.active = False
        for email in self.validatedemails:
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
            if pillar.owner.id == self.id:
                pillar.owner = registry_experts
            elif pillar.driver.id == self.id:
                pillar.driver = registry_experts
            else:
                # Since we removed the person from all teams, something is
                # seriously broken here.
                raise AssertionError(
                    "%s was expected to be owner or driver of %s" %
                    (self.name, pillar.name))

        # Nuke all subscriptions of this person.
        removals = [
            ('BountySubscription', 'person'),
            ('BranchSubscription', 'person'),
            ('BugSubscription', 'person'),
            ('QuestionSubscription', 'person'),
            ('POSubscription', 'person'),
            ('SpecificationSubscription', 'person'),
            ('PackageBugSupervisor', 'bug_supervisor'),
            ('AnswerContact', 'person')]
        cur = cursor()
        for table, person_id_column in removals:
            cur.execute("DELETE FROM %s WHERE %s=%d"
                        % (table, person_id_column, self.id))

        # Update the account's status, preferred email and name.
        self.account_status = AccountStatus.DEACTIVATED
        self.account_status_comment = comment
        IMasterObject(self.preferredemail).status = EmailAddressStatus.NEW
        self._preferredemail_cached = None
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
    def visibility_consistency_warning(self):
        """Warning used when changing the team's visibility.

        A private-membership team cannot be connected to other
        objects, since it may be possible to infer the membership.
        """
        cur = cursor()
        references = list(postgresql.listReferences(cur, 'person', 'id'))
        # These tables will be skipped since they do not risk leaking
        # team membership information, except StructuralSubscription
        # which will be checked further down to provide a clearer warning.
        skip = [
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
            ('signedcodeofconduct', 'owner'),
            ('sshkey', 'person'),
            ('structuralsubscription', 'subscriber'),
            # Private-membership teams can have members, but they
            # cannot be members of other teams.
            ('teammembership', 'team'),
            # A private-membership team must be able to participate in itself.
            ('teamparticipation', 'person'),
            ('teamparticipation', 'team'),
            # Skip mailing lists because if the mailing list is purged, it's
            # not a problem.  Do this check separately below.
            ('mailinglist', 'team')
            ]
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

        # Non-purged mailing list check.
        mailing_list = getUtility(IMailingListSet).get(self.name)
        if (mailing_list is not None and
            mailing_list.status != MailingListStatus.PURGED):
            warnings.add('a mailing list')

        # Compose warning string.
        warnings = sorted(warnings)
        if len(warnings) == 0:
            return None
        else:
            if len(warnings) == 1:
                message = warnings[0]
            else:
                message = '%s and %s' % (
                    ', '.join(warnings[:-1]),
                    warnings[-1])
            return ('This team cannot be made private since it is referenced'
                    ' by %s.' % message)

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
        result = self.myactivememberships
        result = result.orderBy(['-date_joined', '-id'])
        return result[:limit]

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
        return Person.select("""
              -- we are looking for teams, so we want "people" that are on the
              -- teamparticipation.team side of teamparticipation
            Person.id = TeamParticipation.team AND
              -- where this person participates in the team
            TeamParticipation.person = %s AND
              -- but not the teamparticipation for "this person in himself"
              -- which exists for every person
            TeamParticipation.team != %s AND
              -- nor do we want teams in which the person is a direct
              -- participant, so we exclude the teams in which there is
              -- a teammembership for this person
            TeamParticipation.team NOT IN
              (SELECT TeamMembership.team FROM TeamMembership WHERE
                      TeamMembership.person = %s AND
                      TeamMembership.status IN (%s, %s))
            """ % sqlvalues(self.id, self.id, self.id,
                            TeamMembershipStatus.APPROVED,
                            TeamMembershipStatus.ADMIN),
            clauseTables=['TeamParticipation'],
            orderBy=Person.sortingColumns)

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

    @property
    def translation_history(self):
        """See `IPerson`."""
        return POFileTranslator.select(
            'POFileTranslator.person = %s' % sqlvalues(self),
            orderBy='-date_last_touched')

    @property
    def translation_groups(self):
        """See `IPerson`."""
        return getUtility(ITranslationGroupSet).getByPerson(self)

    @property
    def translators(self):
        """See `IPerson`."""
        return getUtility(ITranslatorSet).getByTranslator(self)

    def validateAndEnsurePreferredEmail(self, email):
        """See `IPerson`."""
        email = IMasterObject(email)
        assert not self.is_team, "This method must not be used for teams."
        if not IEmailAddress.providedBy(email):
            raise TypeError, (
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
            # Automated processes need access to set the account().
            removeSecurityProxy(email).accountID = self.accountID
            getUtility(IHWSubmissionSet).setOwnership(email)
        # Now that we have validated the email, see if this can be
        # matched to an existing RevisionAuthor.
        getUtility(IRevisionSet).checkNewVerifiedEmail(email)

    def setContactAddress(self, email):
        """See `IPerson`."""
        assert self.is_team, "This method must be used only for teams."

        if email is None:
            self._unsetPreferredEmail()
        else:
            self._setPreferredEmail(email)

    def _unsetPreferredEmail(self):
        """Change the preferred email address to VALIDATED."""
        email_address = IMasterStore(EmailAddress).find(
            EmailAddress, personID=self.id,
            status=EmailAddressStatus.PREFERRED).one()
        if email_address is not None:
            email_address.status = EmailAddressStatus.VALIDATED
            email_address.syncUpdate()
        self._preferredemail_cached = None

    def setPreferredEmail(self, email):
        """See `IPerson`."""
        assert not self.is_team, "This method must not be used for teams."
        if email is None:
            self._unsetPreferredEmail()
            return
        if (self.preferredemail is None
            and self.account_status != AccountStatus.ACTIVE):
            # XXX sinzui 2008-07-14 bug=248518:
            # This is a hack to preserve this function's behaviour before
            # Account was split from Person. This can be removed when
            # all the callsites ensure that the account is ACTIVE first.
            self.activateAccount(
                "Activated when the preferred email was set.",
                password=self.password,
                preferred_email=email)
        # Anonymous users may claim their profile; remove the proxy
        # to set the account.
        removeSecurityProxy(email).accountID = self.accountID
        self._setPreferredEmail(email)

    def _setPreferredEmail(self, email):
        """Set this person's preferred email to the given email address.

        If the person already has an email address, then its status is
        changed to VALIDATED and the given one is made its preferred one.

        The given email address must implement IEmailAddress and be owned by
        this person.
        """
        if not IEmailAddress.providedBy(email):
            raise TypeError, (
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

        getUtility(IHWSubmissionSet).setOwnership(email)

        # Now we update our cache of the preferredemail.
        self._preferredemail_cached = email

    @cachedproperty('_preferredemail_cached')
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
    def pendinggpgkeys(self):
        """See `IPerson`."""
        logintokenset = getUtility(ILoginTokenSet)
        return sorted(set(token.fingerprint for token in
                      logintokenset.getPendingGPGKeys(requesterid=self.id)))

    @property
    def inactivegpgkeys(self):
        """See `IPerson`."""
        gpgkeyset = getUtility(IGPGKeySet)
        return gpgkeyset.getGPGKeys(ownerid=self.id, active=False)

    @property
    def gpgkeys(self):
        """See `IPerson`."""
        gpgkeyset = getUtility(IGPGKeySet)
        return gpgkeyset.getGPGKeys(ownerid=self.id)

    def getLatestMaintainedPackages(self):
        """See `IPerson`."""
        return self._latestSeriesQuery()

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
            package releases targeted to any PPAs or, if False, sources targeted
            to primary archives.

        Active 'ppa_only' flag is usually associated with active 'uploader_only'
        because there shouldn't be any sense of maintainership for packages
        uploaded to PPAs by someone else than the user himself.
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
                SELECT DISTINCT ON (upload_distroseries, sourcepackagename,
                                    upload_archive)
                    sourcepackagerelease.id
                FROM sourcepackagerelease, archive,
                    securesourcepackagepublishinghistory sspph
                WHERE
                    sspph.sourcepackagerelease = sourcepackagerelease.id AND
                    sspph.archive = archive.id AND
                    %(more_query_clauses)s
                ORDER BY upload_distroseries, sourcepackagename,
                    upload_archive, dateuploaded DESC
              )
              """ % dict(more_query_clauses=query_clauses)

        rset = SourcePackageRelease.select(
            query,
            orderBy=['-SourcePackageRelease.dateuploaded',
                     'SourcePackageRelease.id'],
            prejoins=['sourcepackagename', 'maintainer', 'upload_archive'])

        return rset

    def isUploader(self, distribution):
        """See `IPerson`."""
        permissions = getUtility(IArchivePermissionSet).componentsForUploader(
            distribution.main_archive, self)
        return permissions.count() > 0

    @cachedproperty
    def is_ubuntero(self):
        """See `IPerson`."""
        sigset = getUtility(ISignedCodeOfConductSet)
        lastdate = sigset.getLastAcceptedDate()

        query = AND(SignedCodeOfConduct.q.active==True,
                    SignedCodeOfConduct.q.ownerID==self.id,
                    SignedCodeOfConduct.q.datecreated>=lastdate)

        return bool(SignedCodeOfConduct.select(query).count())

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

    @property
    def archive(self):
        """See `IPerson`."""
        return self.getPPAByName('ppa')

    @property
    def ppas(self):
        """See `IPerson`."""
        return Archive.selectBy(
            owner=self, purpose=ArchivePurpose.PPA, orderBy='name')

    def getPPAByName(self, name):
        """See `IPerson`."""
        return Archive.selectOneBy(
            owner=self, purpose=ArchivePurpose.PPA, name=name)

    def isBugContributor(self, user=None):
        """See `IPerson`."""
        search_params = BugTaskSearchParams(user=user, assignee=self)
        bugtask_count = self.searchTasks(search_params).count()
        return bugtask_count > 0

    def isBugContributorInTarget(self, user=None, target=None):
        """See `IPerson`."""
        assert (IBugTarget.providedBy(target) or
                IProject.providedBy(target)), (
            "%s isn't a valid bug target." % target)
        search_params = BugTaskSearchParams(user=user, assignee=self)
        bugtask_count = target.searchTasks(search_params).count()
        return bugtask_count > 0

    @property
    def structural_subscriptions(self):
        """See `IPerson`."""
        return StructuralSubscription.selectBy(
            subscriber=self, orderBy=['-date_created'])

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
        from canonical.launchpad.database.hwdb import HWSubmissionSet
        return HWSubmissionSet().search(owner=self)


class PersonSet:
    """The set of persons."""
    implements(IPersonSet)

    def __init__(self):
        self.title = 'People registered with Launchpad'

    def isNameBlacklisted(self, name):
        """See `IPersonSet`."""
        cur = cursor()
        cur.execute("SELECT is_blacklisted_name(%(name)s)" % sqlvalues(
            name=name.encode('UTF-8')))
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
                account_rationale, displayname, openid_mnemonic=name,
                password=password, password_is_encrypted=passwordEncrypted)

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
        person = self.getByEmail(email)
        if person:
            return person
        person, dummy = self.createPersonAndEmail(
            email, rationale, comment=comment, displayname=displayname,
            registrant=registrant)
        return person

    def getByName(self, name, ignore_merged=True):
        """See `IPersonSet`."""
        query = (Person.q.name == name)
        if ignore_merged:
            query = AND(query, Person.q.mergedID==None)
        return Person.selectOne(query)

    def getByAccount(self, account):
        """See `IPersonSet`."""
        return Person.selectOne(Person.q.accountID == account.id)

    def updateStatistics(self, ztm):
        """See `IPersonSet`."""
        stats = getUtility(ILaunchpadStatisticSet)
        people_count = Person.select(
            AND(Person.q.teamownerID==None, Person.q.mergedID==None)).count()
        stats.update('people_count', people_count)
        ztm.commit()
        teams_count = Person.select(
            AND(Person.q.teamownerID!=None, Person.q.mergedID==None)).count()
        stats.update('teams_count', teams_count)
        ztm.commit()

    def peopleCount(self):
        """See `IPersonSet`."""
        return getUtility(ILaunchpadStatisticSet).value('people_count')

    def teamsCount(self):
        """See `IPersonSet`."""
        return getUtility(ILaunchpadStatisticSet).value('teams_count')

    def find(self, text, orderBy=None):
        """See `IPersonSet`."""
        if not text:
            # Return an empty result set.
            return EmptyResultSet()
        if orderBy is None:
            orderBy = Person._sortingColumnsForSetOperations
        text = text.lower()

        # Teams may not have email addresses, so we need to either use a LEFT
        # OUTER JOIN or do a UNION between four queries. Using a UNION makes
        # it a lot faster than with a LEFT OUTER JOIN.
        args = (quote_like(text),) + sqlvalues(INACTIVE_ACCOUNT_STATUSES)
        person_email_query = """
            Person.teamowner IS NULL
            AND Person.merged IS NULL
            AND EmailAddress.person = Person.id
            AND lower(EmailAddress.email) LIKE %s || '%%%%'
            AND Person.account = Account.id
            AND Account.status NOT IN %s
            """ % args
        results = Person.select(
            person_email_query, clauseTables=['EmailAddress', 'Account'])

        person_name_query = """
            Person.teamowner IS NULL
            AND Person.merged is NULL
            AND Person.fti @@ ftq(%s)
            AND Person.account = Account.id
            AND Account.status NOT IN %s
            """ % sqlvalues(text, INACTIVE_ACCOUNT_STATUSES)
        results = results.union(Person.select(
            person_name_query, clauseTables=['Account']))

        team_email_query = """
            Person.teamowner IS NOT NULL
            AND Person.merged IS NULL
            AND EmailAddress.person = Person.id
            AND lower(EmailAddress.email) LIKE %s || '%%%%'
            """ % (quote_like(text),)
        results = results.union(Person.select(
            team_email_query, clauseTables=['EmailAddress']))

        team_name_query = """
            Person.teamowner IS NOT NULL
            AND Person.merged IS NULL
            AND Person.fti @@ ftq(%s)
            """ % (quote(text),)
        results = results.union(
                Person.select(team_name_query), orderBy=orderBy)
        return results

    def findPerson(
            self, text="", orderBy=None, exclude_inactive_accounts=True,
            must_have_email=False):
        """See `IPersonSet`."""
        if orderBy is None:
            orderBy = Person._sortingColumnsForSetOperations
        text = text.lower()

        base_query = [
                'Person.teamowner IS NULL',
                'Person.merged IS NULL',
                ]
        clause_tables = []

        if exclude_inactive_accounts:
            clause_tables.append('Account')
            base_query.append('Person.account = Account.id')
            base_query.append(
                'Account.status NOT IN (%s)'
                % ','.join(sqlvalues(*INACTIVE_ACCOUNT_STATUSES)))

        email_clause_tables = clause_tables + ['EmailAddress']
        if must_have_email:
            clause_tables = email_clause_tables
            base_query.append('EmailAddress.person = Person.id')

        # Short circuit for returning all users in order
        if not text:
            return Person.select(
                    ' AND '.join(base_query), clauseTables=clause_tables)

        # We use a UNION here because this makes things *a lot* faster
        # than if we did a single SELECT with the two following clauses
        # ORed.
        email_query = base_query + [
                'EmailAddress.person = Person.id',
                "lower(EmailAddress.email) LIKE %s || '%%'" % quote_like(text)
                ]
        name_query = base_query + ["Person.fti @@ ftq(%s)" % quote(text)]

        results = Person.select(
                ' AND '.join(email_query), clauseTables=email_clause_tables)
        results = results.union(
                Person.select(
                    ' AND '.join(name_query), clauseTables=clause_tables))

        return results.orderBy(orderBy)

    def findTeam(self, text="", orderBy=None):
        """See `IPersonSet`."""
        if orderBy is None:
            orderBy = Person._sortingColumnsForSetOperations
        text = text.lower()
        # Teams may not have email addresses, so we need to either use a LEFT
        # OUTER JOIN or do a UNION between two queries. Using a UNION makes
        # it a lot faster than with a LEFT OUTER JOIN.
        email_query = """
            Person.teamowner IS NOT NULL AND
            EmailAddress.person = Person.id AND
            lower(EmailAddress.email) LIKE %s || '%%'
            """ % quote_like(text)
        results = Person.select(email_query, clauseTables=['EmailAddress'])
        name_query = """
             Person.teamowner IS NOT NULL AND
             Person.fti @@ ftq(%s)
            """ % quote(text)
        return results.union(Person.select(name_query), orderBy=orderBy)

    def get(self, personid):
        """See `IPersonSet`."""
        try:
            return Person.get(personid)
        except SQLObjectNotFound:
            return None

    def getByEmail(self, email):
        """See `IPersonSet`."""
        # We lookup the EmailAddress in the auth store so we can
        # lookup a Person by EmailAddress in the same transaction
        # that the Person or EmailAddress was created. This is not
        # optimal for production as it requires two database lookups,
        # but is required by much of the test suite.
        email_address = IStore(EmailAddress).find(
            EmailAddress, email=email).one()
        if email_address is None:
            return None
        else:
            return IStore(Person).get(Person, email_address.personID)

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

    def merge(self, from_person, to_person):
        """See `IPersonSet`."""
        # Sanity checks
        if not IPerson.providedBy(from_person):
            raise TypeError('from_person is not a person.')
        if not IPerson.providedBy(to_person):
            raise TypeError('to_person is not a person.')
        # If the team has a mailing list, the mailing list better be in the
        # purged state, otherwise the team can't be merged.
        mailing_list = getUtility(IMailingListSet).get(from_person.name)
        assert (mailing_list is None or
                mailing_list.status == MailingListStatus.PURGED), (
            "Can't merge teams which have mailing lists into other teams.")

        if getUtility(IEmailAddressSet).getByPerson(from_person).count() > 0:
            raise AssertionError('from_person still has email addresses.')

        if from_person.is_team and from_person.allmembers.count() > 0:
            raise AssertionError(
                "Only teams without active members can be merged")

        # since we are doing direct SQL manipulation, make sure all
        # changes have been flushed to the database
        store = Store.of(from_person)

        # Get a database cursor.
        cur = cursor()

        references = list(postgresql.listReferences(cur, 'person', 'id'))

        # These table.columns will be skipped by the 'catch all'
        # update performed later
        skip = [
            ('teammembership', 'person'),
            ('teammembership', 'team'),
            ('teamparticipation', 'person'),
            ('teamparticipation', 'team'),
            ('personlanguage', 'person'),
            ('person', 'merged'),
            ('emailaddress', 'person'),
            ('karmacache', 'person'),
            ('karmatotalcache', 'person'),
            # Polls are not carried over when merging teams.
            ('poll', 'team'),
            # We can safely ignore the mailinglist table as there's a sanity
            # check above which prevents teams with associated mailing lists
            # from being merged.
            ('mailinglist', 'team'),
            # I don't think we need to worry about the votecast and vote
            # tables, because a real human should never have two accounts
            # in Launchpad that are active members of a given team and voted
            # in a given poll. -- GuilhermeSalgado 2005-07-07
            # We also can't afford to change poll results after they are
            # closed -- StuartBishop 20060602
            ('votecast', 'person'),
            ('vote', 'person'),
            ('translationrelicensingagreement', 'person'),
            ]

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
                        % (src_tab, src_col, ref_tab, ref_col)
                        )

        # These rows are in a UNIQUE index, and we can only move them
        # to the new Person if there is not already an entry. eg. if
        # the destination and source persons are both subscribed to a bounty,
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
        skip.append(('gpgkey','owner'))

        # Update the Branches that will not conflict, and fudge the names of
        # ones that *do* conflict.
        cur.execute('''
            SELECT product, name FROM Branch WHERE owner = %(to_id)d
            ''' % vars())
        possible_conflicts = set(tuple(r) for r in cur.fetchall())
        cur.execute('''
            SELECT id, product, name FROM Branch WHERE owner = %(from_id)d
            ORDER BY id
            ''' % vars())
        for id, product, name in list(cur.fetchall()):
            new_name = name
            suffix = 1
            while (product, new_name) in possible_conflicts:
                new_name = '%s-%d' % (name, suffix)
                suffix += 1
            possible_conflicts.add((product, new_name))
            new_name = new_name.encode('US-ASCII')
            name = name.encode('US-ASCII')
            cur.execute('''
                UPDATE Branch SET owner = %(to_id)s, name = %(new_name)s
                WHERE owner = %(from_id)s AND name = %(name)s
                    AND (%(product)s IS NULL OR product = %(product)s)
                ''', dict(to_id=to_id, from_id=from_id,
                          name=name, new_name=new_name, product=product))
        skip.append(('branch','owner'))

        # Update MailingListSubscription. Note that no remaining records
        # will have email_address set, as we assert earlier that the
        # from_person has no email addresses.
        # Update records that don't conflict.
        cur.execute('''
            UPDATE MailingListSubscription
            SET person=%(to_id)d
            WHERE person=%(from_id)d
                AND mailing_list NOT IN (
                    SELECT mailing_list
                    FROM MailingListSubscription
                    WHERE person=%(to_id)d
                    )
            ''' % vars())
        # Then trash the remainders.
        cur.execute('''
            DELETE FROM MailingListSubscription WHERE person=%(from_id)d
            ''' % vars())
        skip.append(('mailinglistsubscription', 'person'))

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
        skip.append(('branchsubscription', 'person'))

        # Update only the BountySubscriptions that will not conflict.
        cur.execute('''
            UPDATE BountySubscription
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND bounty NOT IN
                (
                SELECT bounty
                FROM BountySubscription
                WHERE person = %(to_id)d
                )
            ''' % vars())
        # and delete those left over.
        cur.execute('''
            DELETE FROM BountySubscription WHERE person=%(from_id)d
            ''' % vars())
        skip.append(('bountysubscription', 'person'))

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
        skip.append(('bugaffectsperson', 'person'))

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
        skip.append(('answercontact', 'person'))

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
        skip.append(('questionsubscription', 'person'))

        # Update only the MentoringOffers that will not conflict.
        cur.execute('''
            UPDATE MentoringOffer
            SET owner=%(to_id)d
            WHERE owner=%(from_id)d
                AND bug NOT IN (
                    SELECT bug
                    FROM MentoringOffer
                    WHERE owner = %(to_id)d)
                AND specification NOT IN (
                    SELECT specification
                    FROM MentoringOffer
                    WHERE owner = %(to_id)d)
            ''' % vars())
        cur.execute('''
            UPDATE MentoringOffer
            SET team=%(to_id)d
            WHERE team=%(from_id)d
                AND bug NOT IN (
                    SELECT bug
                    FROM MentoringOffer
                    WHERE team = %(to_id)d)
                AND specification NOT IN (
                    SELECT specification
                    FROM MentoringOffer
                    WHERE team = %(to_id)d)
            ''' % vars())
        # and delete those left over.
        cur.execute('''
            DELETE FROM MentoringOffer
            WHERE owner=%(from_id)d OR team=%(from_id)d
            ''' % vars())
        skip.append(('mentoringoffer', 'owner'))
        skip.append(('mentoringoffer', 'team'))

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
        skip.append(('bugnotificationrecipient', 'person'))

        # Update PackageBugSupervisor entries.
        cur.execute('''
            UPDATE PackageBugSupervisor SET bug_supervisor=%(to_id)d
            WHERE bug_supervisor=%(from_id)d
            ''' % vars())
        skip.append(('packagebugsupervisor', 'bug_supervisor'))

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
        skip.append(('specificationfeedback', 'reviewer'))

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
        skip.append(('specificationfeedback', 'requester'))

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
        skip.append(('specificationsubscription', 'person'))

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
        skip.append(('sprintattendance', 'attendee'))

        # Update only the POSubscriptions that will not conflict
        cur.execute('''
            UPDATE POSubscription
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND id NOT IN (
                SELECT a.id
                    FROM POSubscription AS a, POSubscription AS b
                    WHERE a.person = %(from_id)d AND b.person = %(to_id)d
                    AND a.language = b.language
                    AND a.potemplate = b.potemplate
                    )
            ''' % vars())
        skip.append(('posubscription', 'person'))

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
        skip.append(('poexportrequest', 'person'))

        # Update the TranslationMessage. They should not conflict since each
        # of them are independent
        cur.execute('''
            UPDATE TranslationMessage
            SET submitter=%(to_id)d
            WHERE submitter=%(from_id)d
            ''' % vars())
        skip.append(('translationmessage', 'submitter'))
        cur.execute('''
            UPDATE TranslationMessage
            SET reviewer=%(to_id)d
            WHERE reviewer=%(from_id)d
            ''' % vars())
        skip.append(('translationmessage', 'reviewer'))

        # Handle the POFileTranslator cache by doing nothing. As it is
        # maintained by triggers, the data migration has already been done
        # for us when we updated the source tables.
        skip.append(('pofiletranslator', 'person'))

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
        skip.append(('translationimportqueueentry', 'importer'))

        # XXX cprov 2007-02-22 bug=87098:
        # Since we only allow one PPA for each user,
        # we can't reassign the old user archive to the new user.
        # It need to be done manually, probably by reasinning all publications
        # to the old PPA to the new one, performing a careful_publishing on it
        # and removing the old one from disk.
        skip.append(('archive', 'owner'))

        # Update only the CodeReviewVote that will not conflict
        cur.execute('''
            UPDATE CodeReviewVote
            SET reviewer=%(to_id)d
            WHERE reviewer=%(from_id)d AND id NOT IN (
                SELECT a.id FROM CodeReviewVote AS a, CodeReviewVote AS b
                WHERE a.reviewer = %(from_id)d AND b.reviewer = %(to_id)d
                AND a.branch_merge_proposal = b.branch_merge_proposal
                )
            ''' % vars())
        # And leave conflicts as noise
        skip.append(('codereviewvote', 'reviewer'))

        # Update only the WebServiceBan that will not conflict
        cur.execute('''
            UPDATE WebServiceBan
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND id NOT IN (
                SELECT a.id FROM WebServiceBan AS a, WebServiceBan AS b
                WHERE a.person = %(from_id)d AND b.person = %(to_id)d
                AND ( (a.ip IS NULL AND b.ip IS NULL) OR (a.ip = b.ip) )
                )
            ''' % vars())
        # And delete the rest
        cur.execute('''
            DELETE FROM WebServiceBan WHERE person=%(from_id)d
            ''' % vars())
        skip.append(('webserviceban', 'person'))

        # Sanity check. If we have a reference that participates in a
        # UNIQUE index, it must have already been handled by this point.
        # We can tell this by looking at the skip list.
        for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
            uniques = postgresql.listUniques(cur, src_tab, src_col)
            if len(uniques) > 0 and (src_tab, src_col) not in skip:
                raise NotImplementedError(
                        '%s.%s reference to %s.%s is in a UNIQUE index '
                        'but has not been handled' % (
                            src_tab, src_col, ref_tab, ref_col
                            )
                        )

        # Handle all simple cases
        for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
            if (src_tab, src_col) in skip:
                continue
            cur.execute('UPDATE %s SET %s=%d WHERE %s=%d' % (
                src_tab, src_col, to_person.id, src_col, from_person.id
                ))

        # Transfer active team memberships
        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN
        cur.execute(
            'SELECT team, status FROM TeamMembership WHERE person = %s '
            'AND status IN (%s,%s)'
            % sqlvalues(from_person, approved, admin))
        for team_id, status in cur.fetchall():
            cur.execute('SELECT status FROM TeamMembership WHERE person = %s '
                        'AND team = %s'
                        % sqlvalues(to_person, team_id))
            result = cur.fetchone()
            if result:
                current_status = result[0]
                # Now we can safely delete from_person's membership record,
                # because we know to_person has a membership entry for this
                # team, so may only need to change its status.
                cur.execute(
                    'DELETE FROM TeamMembership WHERE person = %s '
                    'AND team = %s' % sqlvalues(from_person, team_id))

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
                    'AND team = %s' % sqlvalues(status, to_person, team_id))
            else:
                # to_person is not a member of this team. just change
                # from_person with to_person in the membership record.
                cur.execute(
                    'UPDATE TeamMembership SET person = %s WHERE person = %s '
                    'AND team = %s'
                    % sqlvalues(to_person, from_person, team_id))

        cur.execute('SELECT team FROM TeamParticipation WHERE person = %s '
                    'AND person != team' % sqlvalues(from_person))
        for team_id in cur.fetchall():
            cur.execute(
                'SELECT team FROM TeamParticipation WHERE person = %s '
                'AND team = %s' % sqlvalues(to_person, team_id))
            if not cur.fetchone():
                cur.execute(
                    'UPDATE TeamParticipation SET person = %s WHERE '
                    'person = %s AND team = %s'
                    % sqlvalues(to_person, from_person, team_id))
            else:
                cur.execute(
                    'DELETE FROM TeamParticipation WHERE person = %s AND '
                    'team = %s' % sqlvalues(from_person, team_id))

        # Flag the person as merged
        cur.execute('''
            UPDATE Person SET merged=%(to_id)d WHERE id=%(from_id)d
            ''' % vars())

        # Append a -merged suffix to the account's name.
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

    def getSubscribersForTargets(self, targets, recipients=None, level=None):
        """See `IPersonSet`. """
        if len(targets) == 0:
            return set()
        target_criteria = []
        for target in targets:
            # target_args is a mapping from query arguments
            # to query values.
            target_args = target._target_args
            target_criteria_clauses = []
            for key, value in target_args.items():
                if value is not None:
                    target_criteria_clauses.append(
                        '%s = %s' % (key, quote(value)))
                else:
                    target_criteria_clauses.append(
                        '%s IS NULL' % key)
            if level is not None:
                target_criteria_clauses.append('bug_notification_level >= %s'
                    % quote(level.value))

            target_criteria.append(
                '(%s)' % ' AND '.join(target_criteria_clauses))

        # Build a UNION query, since using OR slows down the query a lot.
        subscriptions = StructuralSubscription.select(target_criteria[0])
        for target_criterion in target_criteria[1:]:
            subscriptions = subscriptions.union(
                StructuralSubscription.select(target_criterion))

        # Listify the result, since we want to loop over it multiple times.
        subscriptions = list(subscriptions)

        # We can't use prejoins in UNION queries, so populate the cache
        # by getting all the subscribers.
        subscriber_ids = [
            subscription.subscriberID for subscription in subscriptions]
        if len(subscriber_ids) > 0:
            list(Person.select("id IN %s" % sqlvalues(subscriber_ids)))

        subscribers = set()
        for subscription in subscriptions:
            subscribers.add(subscription.subscriber)
            if recipients is not None:
                recipients.addStructuralSubscriber(
                    subscription.subscriber, subscription.target)
        return subscribers

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
        from canonical.launchpad.database import LibraryFileAlias
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

    def new(self, person, keytype, keytext, comment):
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

    See canonical.launchpad.validators.name for the definition of a
    valid nick.

    It is technically possible for this function to raise a
    NicknameGenerationError, but this will only occur if an operator
    has majorly screwed up the name blacklist.
    """
    email_addr = email_addr.strip().lower()

    if not valid_email(email_addr):
        raise NicknameGenerationError("%s is not a valid email address"
                                      % email_addr)

    user, domain = re.match("^(\S+)@(\S+)$", email_addr).groups()
    user = user.replace(".", "-").replace("_", "-")
    domain_parts = domain.split(".")

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

    for domain_part in domain_parts:
        generated_nick = sanitize_name(generated_nick + "-" + domain_part)
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
            index = random.randint(0, len(mutated_nick)-1)
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
            "registered a match everything regexp in the black list."
            )

    finally:
        random.setstate(random_state)


@adapter(IAccount)
@implementer(IPerson)
def person_from_account(account):
    """Adapt an IAccount into an IPerson."""
    # The IAccount interface does not publish the account.person reference.
    naked_account = removeSecurityProxy(account)
    person = ProxyFactory(IStore(Person).find(
        Person, accountID=naked_account.id).one())
    if person is None:
        raise ComponentLookupError
    return person
