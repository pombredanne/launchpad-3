# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# _valid_nick() in generate_nick causes E1101
# vars() causes W0612
# pylint: disable-msg=E0611,W0212,E1101,W0612

"""Implementation classes for a Person."""

__metaclass__ = type
__all__ = [
    'IrcID',
    'IrcIDSet',
    'JabberID',
    'JabberIDSet',
    'Person',
    'PersonSet',
    'SSHKey',
    'SSHKeySet',
    'WikiName',
    'WikiNameSet']

from datetime import datetime, timedelta
import pytz
import sha

from zope.interface import implements, alsoProvides
from zope.component import getUtility
from zope.event import notify
from zope.security.proxy import removeSecurityProxy

from sqlobject import (
    BoolCol, ForeignKey, IntCol, SQLMultipleJoin, SQLObjectNotFound,
    SQLRelatedJoin, StringCol)
from sqlobject.sqlbuilder import AND, OR, SQLConstant

from canonical.config import config
from canonical.database import postgresql
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor, flush_database_caches, flush_database_updates, quote, quote_like,
    sqlvalues, SQLBase)

from canonical.foaf import nickname
from canonical.cachedproperty import cachedproperty

from canonical.launchpad.database.answercontact import AnswerContact
from canonical.launchpad.database.karma import KarmaCategory
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.oauth import OAuthAccessToken
from canonical.launchpad.database.personlocation import PersonLocation
from canonical.launchpad.database.structuralsubscription import (
    StructuralSubscription)
from canonical.launchpad.database.translationrelicensingagreement import (
    TranslationRelicensingAgreement)
from canonical.launchpad.event.karma import KarmaAssignedEvent
from canonical.launchpad.event.team import JoinTeamEvent, TeamInvitationEvent
from canonical.launchpad.helpers import contactEmailAddresses, shortlist

from canonical.launchpad.interfaces import (
    AccountStatus, ArchivePurpose, BugTaskImportance, BugTaskSearchParams,
    BugTaskStatus, EmailAddressStatus, IArchivePermissionSet, IBugTarget,
    IBugTaskSet, IDistribution, IDistributionSet, IEmailAddress,
    IEmailAddressSet, IGPGKeySet, IHWSubmissionSet, IHasIcon, IHasLogo,
    IHasMugshot, IIrcID, IIrcIDSet, IJabberID, IJabberIDSet, ILaunchBag,
    ILaunchpadCelebrities, ILaunchpadStatisticSet, ILoginTokenSet,
    IMailingListSet, INACTIVE_ACCOUNT_STATUSES, InvalidEmailAddress,
    InvalidName, IPasswordEncryptor, IPerson, IPersonSet, IPillarNameSet,
    IProduct, IRevisionSet, ISSHKey, ISSHKeySet, ISignedCodeOfConductSet,
    ISourcePackageNameSet, ITeam, ITranslationGroupSet, IWikiName,
    IWikiNameSet, JoinNotAllowed, LoginTokenType,
    MailingListAutoSubscribePolicy, NameAlreadyTaken, PackagePublishingStatus,
    PersonCreationRationale, PersonVisibility, PersonalStanding,
    PostedMessageStatus, QUESTION_STATUS_DEFAULT_SEARCH, SSHKeyType,
    ShipItConstants, ShippingRequestStatus, SpecificationDefinitionStatus,
    SpecificationFilter, SpecificationImplementationStatus, SpecificationSort,
    TeamMembershipRenewalPolicy, TeamMembershipStatus, TeamSubscriptionPolicy,
    UBUNTU_WIKI_URL, UNRESOLVED_BUGTASK_STATUSES)

from canonical.launchpad.database.archive import Archive
from canonical.launchpad.database.codeofconduct import SignedCodeOfConduct
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.bugtask import (
    BugTask, get_bug_privacy_filter, search_value_to_where_condition)
from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.database.karma import KarmaCache, KarmaTotalCache
from canonical.launchpad.database.logintoken import LoginToken
from canonical.launchpad.database.pillar import PillarName
from canonical.launchpad.database.pofile import POFileTranslator
from canonical.launchpad.database.karma import KarmaAction, Karma
from canonical.launchpad.database.mentoringoffer import MentoringOffer
from canonical.launchpad.database.shipit import (
    MIN_KARMA_ENTRIES_TO_BE_TRUSTED_ON_SHIPIT, ShippingRequest)
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.specificationfeedback import (
    SpecificationFeedback)
from canonical.launchpad.database.specificationsubscription import (
    SpecificationSubscription)
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.database.teammembership import (
    TeamMembership, TeamMembershipSet, TeamParticipation)
from canonical.launchpad.database.question import QuestionPersonSearch

from canonical.launchpad.searchbuilder import any
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.validators.person import (
    public_person_validator, visibility_validator)


class ValidPersonOrTeamCache(SQLBase):
    """Flags if a Person or Team is active and usable in Launchpad.

    This is readonly, as the underlying table is maintained using
    database triggers.
    """
    # Look Ma, no columns! (apart from id)


class Person(SQLBase, HasSpecificationsMixin, HasTranslationImportsMixin):
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

    name = StringCol(dbName='name', alternateID=True, notNull=True)

    def _set_name(self, value):
        """Check that rename is allowed."""
        # Renaming a team is prohibited for any team that has a mailing list.
        # This is because renaming a mailing list is not trivial in Mailman
        # 2.1 (see Mailman FAQ item 4.70).  We prohibit such renames in the
        # team edit details view, but just to be safe, we also assert that
        # such an attempt is not being made here.  To do this, we must
        # override the SQLObject method for setting the 'name' database
        # column.  Watch out for when SQLObject is creating this row, because
        # in that case self.name isn't yet available.
        assert (self._SO_creating or
                not self.is_team or
                getUtility(IMailingListSet).get(self.name) is None), (
            'Cannot rename teams with mailing lists')
        # Everything's okay, so let SQLObject do the normal thing.
        self._SO_set_name(value)

    password = StringCol(dbName='password', default=None)
    displayname = StringCol(dbName='displayname', notNull=True)
    teamdescription = StringCol(dbName='teamdescription', default=None)
    homepage_content = StringCol(default=None)
    icon = ForeignKey(
        dbName='icon', foreignKey='LibraryFileAlias', default=None)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    mugshot = ForeignKey(
        dbName='mugshot', foreignKey='LibraryFileAlias', default=None)
    openid_identifier = StringCol(
            dbName='openid_identifier', alternateID=True, notNull=True,
            default=DEFAULT)

    account_status = EnumCol(
        enum=AccountStatus, default=AccountStatus.NOACCOUNT)
    account_status_comment = StringCol(default=None)

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
                           validator=public_person_validator)

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
        validator=public_person_validator)
    hide_email_addresses = BoolCol(notNull=True, default=False)
    verbose_bugnotifications = BoolCol(notNull=True, default=True)

    # SQLRelatedJoin gives us also an addLanguage and removeLanguage for free
    languages = SQLRelatedJoin('Language', joinColumn='person',
                            otherColumn='language',
                            intermediateTable='PersonLanguage',
                            orderBy='englishname')

    subscribed_branches = SQLRelatedJoin(
        'Branch', joinColumn='person', otherColumn='branch',
        intermediateTable='BranchSubscription', prejoins=['product'])
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
    authored_branches = SQLMultipleJoin(
        'Branch', joinColumn='author', prejoins=['product'])
    signedcocs = SQLMultipleJoin('SignedCodeOfConduct', joinColumn='owner')
    ircnicknames = SQLMultipleJoin('IrcID', joinColumn='person')
    jabberids = SQLMultipleJoin('JabberID', joinColumn='person')

    entitlements = SQLMultipleJoin('Entitlement', joinColumn='person')
    visibility = EnumCol(
        enum=PersonVisibility,
        default=PersonVisibility.PUBLIC,
        validator=visibility_validator)

    personal_standing = EnumCol(
        enum=PersonalStanding, default=PersonalStanding.UNKNOWN,
        notNull=True)

    personal_standing_reason = StringCol(default=None)

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
        self.password = None
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

    @cachedproperty
    def _location(self):
        return PersonLocation.selectOneBy(person=self)

    def set_time_zone(self, timezone):
        location = self._location
        if location is None:
            location = PersonLocation(
                person=self,
                latitude=None,
                longitude=None,
                time_zone=timezone,
                last_modified_by=self)
        location.time_zone = timezone
        self._location = location

    def get_time_zone(self):
        location = self._location
        if location is None:
            return None
        return location.time_zone
    timezone = property(get_time_zone, set_time_zone)


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
    def approver_specs(self):
        return shortlist(Specification.selectBy(
            approver=self, orderBy=['-datecreated']))

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
    def created_specs(self):
        return shortlist(Specification.selectBy(
            owner=self, orderBy=['-datecreated']))

    @property
    def drafted_specs(self):
        return shortlist(Specification.selectBy(
            drafter=self, orderBy=['-datecreated']))

    @property
    def feedback_specs(self):
        return shortlist(Specification.select(
            AND(Specification.q.id == SpecificationFeedback.q.specificationID,
                SpecificationFeedback.q.reviewerID == self.id),
            clauseTables=['SpecificationFeedback'],
            orderBy=['-datecreated']))

    @property
    def subscribed_specs(self):
        specification_id = SpecificationSubscription.q.specificationID
        return shortlist(Specification.select(
            AND (Specification.q.id == specification_id,
                 SpecificationSubscription.q.personID == self.id),
            clauseTables=['SpecificationSubscription'],
            orderBy=['-datecreated']))

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
        """Return a name suitable for display on a web page.

        Originally, this was calculated but now we just use displayname.
        You should continue to use this method, however, as we may want to
        change again, such as returning '$displayname ($name)'.
        """
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
        """Return a list of valid IQuestionTargets.

        Provided AnswerContact query results, a distinct list of Products,
        Distributions, and SourcePackages is returned.
        """
        targets = []
        for answer_contact in answer_contacts:
            if answer_contact.product is not None:
                target = answer_contact.product
            elif answer_contact.sourcepackagename is not None:
                assert answer_contact.distribution is not None, (
                    "Missing distribution.")
                distribution = answer_contact.distribution
                target = distribution.getSourcePackage(
                    answer_contact.sourcepackagename)
            elif answer_contact.distribution is not None:
                target = answer_contact.distribution
            else:
                raise AssertionError('Unknown IQuestionTarget.')

            if not target in targets:
                targets.append(target)

        return targets

    @property
    def branches(self):
        """See `IPerson`."""
        ret = self.authored_branches.union(self.registered_branches)
        ret = ret.union(self.subscribed_branches)
        return ret.orderBy('-id')

    @property
    def registered_branches(self):
        """See `IPerson`."""
        query = """Branch.owner = %d AND
                   (Branch.author != %d OR Branch.author is NULL)"""
        return Branch.select(query % (self.id, self.id),
                             prejoins=["product"])


    # XXX: TomBerger 2008-02-14, 2008-04-14 bug=191799:
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

    def getBugSubscriberOpenBugCounts(self, user):
        """See `IPerson`."""
        open_bugs_cond = (
            'BugTask.status %s' % search_value_to_where_condition(
                any(*UNRESOLVED_BUGTASK_STATUSES)))

        sum_template = "SUM(CASE WHEN %s THEN 1 ELSE 0 END) AS %s"
        sums = [
            sum_template % (open_bugs_cond, 'open_bugs'),
            sum_template % (
                'BugTask.importance %s' % search_value_to_where_condition(
                    BugTaskImportance.CRITICAL), 'open_critical_bugs'),
            sum_template % (
                'BugTask.assignee IS NULL', 'open_unassigned_bugs'),
            sum_template % (
                'BugTask.status %s' % search_value_to_where_condition(
                    BugTaskStatus.INPROGRESS), 'open_inprogress_bugs')]

        conditions = [
            'Bug.id = BugTask.bug',
            open_bugs_cond,
            'StructuralSubscription.subscriber = %s' % sqlvalues(self),
            'BugTask.sourcepackagename = '
                'StructuralSubscription.sourcepackagename',
            'BugTask.distribution = StructuralSubscription.distribution',
            'Bug.duplicateof is NULL']
        privacy_filter = get_bug_privacy_filter(user)
        if privacy_filter:
            conditions.append(privacy_filter)

        query = """SELECT BugTask.distribution,
                          BugTask.sourcepackagename,
                          %(sums)s
                   FROM BugTask, Bug, StructuralSubscription
                   WHERE %(conditions)s
                   GROUP BY BugTask.distribution, BugTask.sourcepackagename"""
        cur = cursor()
        cur.execute(query % dict(
            sums=', '.join(sums), conditions=' AND '.join(conditions)))
        distribution_set = getUtility(IDistributionSet)
        sourcepackagename_set = getUtility(ISourcePackageNameSet)
        packages_with_bugs = set()
        L = []
        for (distro_id, spn_id, open_bugs,
             open_critical_bugs, open_unassigned_bugs,
             open_inprogress_bugs) in shortlist(cur.fetchall()):
            distribution = distribution_set.get(distro_id)
            sourcepackagename = sourcepackagename_set.get(spn_id)
            source_package = distribution.getSourcePackage(sourcepackagename)
            # XXX: Bjorn Tillenius 2006-12-15:
            # Add a tuple instead of the distribution package
            # directly, since DistributionSourcePackage doesn't define a
            # __hash__ method.
            packages_with_bugs.add((distribution, sourcepackagename))
            package_counts = dict(
                package=source_package,
                open=open_bugs,
                open_critical=open_critical_bugs,
                open_unassigned=open_unassigned_bugs,
                open_inprogress=open_inprogress_bugs)
            L.append(package_counts)

        # Only packages with open bugs were included in the query. Let's
        # add the rest of the packages as well.
        all_packages = set(
            (distro_package.distribution, distro_package.sourcepackagename)
            for distro_package in self.getBugSubscriberPackages())
        for distribution, sourcepackagename in all_packages.difference(
                packages_with_bugs):
            package_counts = dict(
                package=distribution.getSourcePackage(sourcepackagename),
                open=0, open_critical=0, open_unassigned=0,
                open_inprogress=0)
            L.append(package_counts)

        return L

    def getBranch(self, product_name, branch_name):
        """See `IPerson`."""
        # import here to work around a circular import problem
        from canonical.launchpad.database import Product

        if product_name is None or product_name == '+junk':
            return Branch.selectOne(
                'owner=%d AND product is NULL AND name=%s'
                % (self.id, quote(branch_name)))
        else:
            product = Product.selectOneBy(name=product_name)
            if product is None:
                return None
            return Branch.selectOneBy(owner=self, product=product,
                                      name=branch_name)

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

    @property
    def mailing_list(self):
        """See `IPerson`."""
        return getUtility(IMailingListSet).get(self.name)

    @cachedproperty
    def is_trusted_on_shipit(self):
        """See `IPerson`."""
        min_entries = MIN_KARMA_ENTRIES_TO_BE_TRUSTED_ON_SHIPIT
        return Karma.selectBy(person=self).count() >= min_entries

    def shippedShipItRequestsOfCurrentSeries(self):
        """See `IPerson`."""
        query = '''
            ShippingRequest.recipient = %s
            AND ShippingRequest.id = RequestedCDs.request
            AND RequestedCDs.distroseries = %s
            AND ShippingRequest.shipment IS NOT NULL
            ''' % sqlvalues(self.id, ShipItConstants.current_distroseries)
        return ShippingRequest.select(
            query, clauseTables=['RequestedCDs'], distinct=True,
            orderBy='-daterequested')

    def lastShippedRequest(self):
        """See `IPerson`."""
        query = ("recipient = %s AND status = %s"
                 % sqlvalues(self.id, ShippingRequestStatus.SHIPPED))
        return ShippingRequest.selectFirst(query, orderBy=['-daterequested'])

    def pastShipItRequests(self):
        """See `IPerson`."""
        query = """
            recipient = %(id)s AND (
                status IN (%(denied)s, %(cancelled)s, %(shipped)s))
            """ % sqlvalues(id=self.id, denied=ShippingRequestStatus.DENIED,
                            cancelled=ShippingRequestStatus.CANCELLED,
                            shipped=ShippingRequestStatus.SHIPPED)
        return ShippingRequest.select(query, orderBy=['id'])

    def currentShipItRequest(self):
        """See `IPerson`."""
        query = """
            recipient = %(id)s
            AND status NOT IN (%(denied)s, %(cancelled)s, %(shipped)s)
            """ % sqlvalues(id=self.id, denied=ShippingRequestStatus.DENIED,
                            cancelled=ShippingRequestStatus.CANCELLED,
                            shipped=ShippingRequestStatus.SHIPPED)
        results = shortlist(
            ShippingRequest.select(query, orderBy=['id'], limit=2))
        count = len(results)
        assert (self == getUtility(ILaunchpadCelebrities).shipit_admin or
                count <= 1), ("Only the shipit-admins team is allowed to "
                              "have more than one open shipit request")
        if count == 1:
            return results[0]
        else:
            return None

    def searchTasks(self, search_params, *args):
        """See `IPerson`."""
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
            """ % sqlvalues(person=self)]
        if match_name is not None:

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
        return KarmaCache.select(
            AND(
                KarmaCache.q.personID == self.id,
                KarmaCache.q.categoryID != None,
                KarmaCache.q.productID == None,
                KarmaCache.q.projectID == None,
                KarmaCache.q.distributionID == None,
                KarmaCache.q.sourcepackagenameID == None),
            orderBy=['category'])

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
        try:
            if ValidPersonOrTeamCache.get(self.id) is not None:
                return True
        except SQLObjectNotFound:
            pass
        return False

    @property
    def is_valid_person(self):
        """See `IPerson`."""
        if self.is_team:
            return False
        return self.is_valid_person_or_team

    @property
    def is_openid_enabled(self):
        """See `IPerson`."""
        if not self.is_valid_person:
            return False

        if config.launchpad.openid_users == 'all':
            return True

        openid_users = getUtility(IPersonSet).getByName(
                config.launchpad.openid_users
                )
        assert openid_users is not None, \
                'No Person %s found' % config.launchpad.openid_users
        if self.inTeam(openid_users):
            return True

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

    # XXX: StuartBishop 2006-05-10:
    # This cache should no longer be needed once CrowdControl lands,
    # as apparently it will also cache this information.
    _inTeam_cache = None

    def inTeam(self, team):
        """See `IPerson`."""
        if team is None:
            return False

        # Translate the team name to an ITeam if we were passed a team.
        if isinstance(team, str):
            team = PersonSet().getByName(team)

        if team.id == self.id: # Short circuit - would return True anyway
            return True

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
    def getSuperTeams(self):
        """See `IPerson`."""
        query = """
            Person.id = TeamParticipation.team AND
            TeamParticipation.person = %s AND
            TeamParticipation.team != %s
            """ % sqlvalues(self.id, self.id)
        return Person.select(query, clauseTables=['TeamParticipation'])

    def getSubTeams(self):
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
            to_addrs.update(contactEmailAddresses(person))
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
        if tm is not None:
            # We can't use tm.setExpirationDate() here because the reviewer
            # here will be the member themselves when they join an OPEN team.
            tm.dateexpires = expires
            tm.setStatus(status, reviewer, comment)
        else:
            TeamMembershipSet().new(
                person, self, status, reviewer, dateexpires=expires,
                comment=comment)
            notify(event(person, self))

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
        query = AND(EmailAddress.q.personID==self.id,
                    EmailAddress.q.status==status)
        return EmailAddress.select(query)

    @property
    def ubuntuwiki(self):
        """See `IPerson`."""
        return getUtility(IWikiNameSet).getUbuntuWikiByPerson(self)

    @property
    def otherwikis(self):
        """See `IPerson`."""
        return getUtility(IWikiNameSet).getOtherWikisByPerson(self)

    @property
    def allwikis(self):
        return getUtility(IWikiNameSet).getAllWikisByPerson(self)

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
    def open_membership_invitations(self):
        """See `IPerson`."""
        return TeamMembership.select("""
            TeamMembership.person = %s AND status = %s
            AND Person.id = TeamMembership.team
            """ % sqlvalues(self.id, TeamMembershipStatus.INVITED),
            clauseTables=['Person'],
            orderBy=Person.sortingColumns)

    def deactivateAccount(self, comment):
        """Deactivate this person's Launchpad account.

        Deactivating an account means:
            - Setting its password to NULL;
            - Removing the user from all teams he's a member of;
            - Changing all his email addresses' status to NEW;
            - Revoking Code of Conduct signatures of that user;
            - Reassigning bugs/specs assigned to him;
            - Changing the ownership of products/projects/teams owned by him.
        """
        assert self.is_valid_person, (
            "You can only deactivate an account of a valid person.")

        for membership in self.myactivememberships:
            self.leave(membership.team)
        # Make sure all further queries don't see this person as a member of
        # any teams.
        flush_database_updates()

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

            # XXX flacoste 2007/11/26 The comparison using id in the assert
            # below works around a nasty intermittent failure.
            # See bug #164635.
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
            # XXX flacoste 2007/11/26 The comparison using id below
            # works around a nasty intermittent failure. See bug #164635.
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

        # Update the account's status, password, preferred email and name.
        self.account_status = AccountStatus.DEACTIVATED
        self.account_status_comment = comment
        self.password = None
        self.preferredemail.status = EmailAddressStatus.NEW
        self._preferredemail_cached = None
        base_new_name = self.name + '-deactivatedaccount'
        new_name = base_new_name
        count = 1
        while Person.selectOneBy(name=new_name) is not None:
            new_name = base_new_name + str(count)
            count += 1
        self.name = new_name

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
            # This table is handled entirely by triggers.
            ('validpersonorteamcache', 'id'),
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

        row = cur.dictfetchone()
        for column, warning in [
            ('product_count', 'a project subscriber'),
            ('productseries_count', 'a project series subscriber'),
            ('project_count', 'a project subscriber'),
            ('milestone_count', 'a milestone subscriber'),
            ('distribution_count', 'a distribution subscriber'),
            ('distroseries_count', 'a distroseries subscriber'),
            ('sourcepackagename_count', 'a source package subscriber'),
            ]:
            if row[column] > 0:
                warnings.add(warning)

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
            query, clauseTables=['Person'], orderBy=Person.sortingColumns)

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
        # Note that we can't use selectBy here because of the prejoins.
        query = ['POFileTranslator.person = %s' % sqlvalues(self),
                 'POFileTranslator.pofile = POFile.id',
                 'POFile.language = Language.id',
                 "Language.code != 'en'"]
        history = POFileTranslator.select(
            ' AND '.join(query),
            prejoins=[
                'pofile.potemplate',
                'latest_message',
                'latest_message.potmsgset.msgid_singular',
                'latest_message.msgstr0'],
            clauseTables=['Language', 'POFile'],
            orderBy="-date_last_touched")
        return history

    @property
    def translation_groups(self):
        """See `IPerson`."""
        return getUtility(ITranslationGroupSet).getByPerson(self)

    def validateAndEnsurePreferredEmail(self, email):
        """See `IPerson`."""
        assert not self.is_team, "This method must not be used for teams."
        if not IEmailAddress.providedBy(email):
            raise TypeError, (
                "Any person's email address must provide the IEmailAddress "
                "interface. %s doesn't." % email)
        # XXX stevea 2005-07-05:
        # This is here because of an SQLobject comparison oddity.
        assert email.person.id == self.id, 'Wrong person! %r, %r' % (
            email.person, self)

        # This email is already validated and is this person's preferred
        # email, so we have nothing to do.
        if self.preferredemail == email:
            return

        if self.preferredemail is None:
            # This branch will be executed only in the first time a person
            # uses Launchpad. Either when creating a new account or when
            # resetting the password of an automatically created one.
            self._setPreferredEmail(email)
        else:
            email.status = EmailAddressStatus.VALIDATED
            getUtility(IHWSubmissionSet).setOwnership(email)
        # Now that we have validated the email, see if this can be
        # matched to an existing RevisionAuthor.
        getUtility(IRevisionSet).checkNewVerifiedEmail(email)

    def setContactAddress(self, email):
        """See `IPerson`."""
        assert self.is_team, "This method must be used only for teams."

        if email is None:
            if self.preferredemail is not None:
                email_address = self.preferredemail
                email_address.status = EmailAddressStatus.VALIDATED
                email_address.syncUpdate()
            self._preferredemail_cached = None
        else:
            self._setPreferredEmail(email)

    def setPreferredEmail(self, email):
        """See `IPerson`."""
        assert not self.is_team, "This method must not be used for teams."
        if self.preferredemail is None:
            # This is the first time we're confirming this person's email
            # address, so we now assume this person has a Launchpad account.
            # XXX: This is a hack! In the future we won't have this
            # association between accounts and confirmed addresses, but this
            # will do for now. -- Guilherme Salgado, 2007-07-03
            self.account_status = AccountStatus.ACTIVE
            self.account_status_comment = None
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
        assert email.person.id == self.id

        if self.preferredemail is not None:
            self.preferredemail.status = EmailAddressStatus.VALIDATED
            # We need to flush updates, because we don't know what order
            # SQLObject will issue the changes and we can't set the new
            # address to PREFERRED until the old one has been set to VALIDATED
            self.preferredemail.syncUpdate()

        # Get the non-proxied EmailAddress object, so we can call
        # syncUpdate() on it.
        email = EmailAddress.get(email.id)
        email.status = EmailAddressStatus.PREFERRED
        email.syncUpdate()
        getUtility(IHWSubmissionSet).setOwnership(email)
        # Now we update our cache of the preferredemail
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
        if ((self.preferredemail is not None) and
            not(self.hide_email_addresses)):
            return self.preferredemail.email
        else:
            return ''

    @property
    def preferredemail_sha1(self):
        """See `IPerson`."""
        preferredemail = self.preferredemail
        if preferredemail:
            return sha.new(
                'mailto:' + preferredemail.email).hexdigest().upper()
        else:
            return None

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
                    sspph.status = %(pub_status)s AND
                    %(more_query_clauses)s
                ORDER BY upload_distroseries, sourcepackagename,
                    upload_archive, dateuploaded DESC
              )
              """ % dict(pub_status=quote(PackagePublishingStatus.PUBLISHED),
                         more_query_clauses=query_clauses)

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
        return Archive.selectOneBy(owner=self, purpose=ArchivePurpose.PPA)

    def isBugContributor(self, user=None):
        """See `IPerson`."""
        search_params = BugTaskSearchParams(user=user, assignee=self)
        bugtask_count = self.searchTasks(search_params).count()
        return bugtask_count > 0

    def isBugContributorInTarget(self, user=None, target=None):
        """See `IPerson`."""
        assert IBugTarget.providedBy(target), (
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
        if mailinglist is None or not mailinglist.isUsable():
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


class PersonSet:
    """The set of persons."""
    implements(IPersonSet)

    def __init__(self):
        self.title = 'People registered with Launchpad'

    def topPeople(self):
        """See `IPersonSet`."""
        # The odd ordering here is to ensure we hit the PostgreSQL
        # indexes. It will not make any real difference outside of tests.
        query = """
            id in (
                SELECT person FROM KarmaTotalCache
                ORDER BY karma_total DESC, person DESC
                LIMIT 5
                )
            """
        top_people = shortlist(Person.select(query))
        top_people.sort(key=lambda obj: (obj.karma, obj.id), reverse=True)
        return top_people

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
        if not valid_email(email):
            raise InvalidEmailAddress(
                "%s is not a valid email address." % email)

        if name is None:
            name = nickname.generate_nick(email)
        elif not valid_name(name):
            raise InvalidName(
                "%s is not a valid name for a person." % name)
        else:
            # The name should be okay, move on...
            pass
        if self.getByName(name, ignore_merged=False) is not None:
            raise NameAlreadyTaken(
                "The name '%s' is already taken." % name)

        if not passwordEncrypted and password is not None:
            password = getUtility(IPasswordEncryptor).encrypt(password)

        if not displayname:
            displayname = name.capitalize()
        person = self._newPerson(
            name, displayname, hide_email_addresses, rationale=rationale,
            comment=comment, password=password, registrant=registrant)

        email = getUtility(IEmailAddressSet).new(email, person)
        return person, email

    def _newPerson(self, name, displayname, hide_email_addresses,
                   rationale, comment=None, password=None, registrant=None):
        """Create and return a new Person with the given attributes.

        Also generate a wikiname for this person that's not yet used in the
        Ubuntu wiki.
        """
        assert self.getByName(name, ignore_merged=False) is None
        person = Person(
            name=name, displayname=displayname, password=password,
            creation_rationale=rationale, creation_comment=comment,
            hide_email_addresses=hide_email_addresses, registrant=registrant)

        wikinameset = getUtility(IWikiNameSet)
        wikiname = nickname.generate_wikiname(
            person.displayname, wikinameset.exists)
        wikinameset.new(person, UBUNTU_WIKI_URL, wikiname)
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

    def getByOpenIdIdentifier(self, openid_identifier):
        """Returns a Person with the given openid_identifier, or None."""
        person = Person.selectOneBy(openid_identifier=openid_identifier)
        if person is not None and person.is_valid_person:
            return person
        else:
            return None

    def updateStatistics(self, ztm):
        """See `IPersonSet`."""
        stats = getUtility(ILaunchpadStatisticSet)
        stats.update('people_count', self.getAllPersons().count())
        ztm.commit()
        stats.update('teams_count', self.getAllTeams().count())
        ztm.commit()

    def peopleCount(self):
        """See `IPersonSet`."""
        return getUtility(ILaunchpadStatisticSet).value('people_count')

    def getAllPersons(self, orderBy=None):
        """See `IPersonSet`."""
        if orderBy is None:
            orderBy = Person.sortingColumns
        query = AND(Person.q.teamownerID==None, Person.q.mergedID==None)
        return Person.select(query, orderBy=orderBy)

    def getAllValidPersons(self, orderBy=None):
        """See `IPersonSet`."""
        if orderBy is None:
            orderBy = Person.sortingColumns
        return Person.select(
            "Person.id = ValidPersonOrTeamCache.id AND teamowner IS NULL",
            clauseTables=["ValidPersonOrTeamCache"], orderBy=orderBy
            )

    def teamsCount(self):
        """See `IPersonSet`."""
        return getUtility(ILaunchpadStatisticSet).value('teams_count')

    def getAllTeams(self, orderBy=None):
        """See `IPersonSet`."""
        if orderBy is None:
            orderBy = Person.sortingColumns
        query = AND(Person.q.teamownerID!=None, Person.q.mergedID==None)
        return Person.select(query, orderBy=orderBy)

    def find(self, text="", orderBy=None):
        """See `IPersonSet`."""
        if orderBy is None:
            orderBy = Person._sortingColumnsForSetOperations
        text = text.lower()
        base_query = ("Person.account_status not in (%s)"
                      % ','.join(sqlvalues(*INACTIVE_ACCOUNT_STATUSES)))
        # Teams may not have email addresses, so we need to either use a LEFT
        # OUTER JOIN or do a UNION between two queries. Using a UNION makes
        # it a lot faster than with a LEFT OUTER JOIN.
        email_query = base_query + """
            AND EmailAddress.person = Person.id
            AND lower(EmailAddress.email) LIKE %s || '%%'
            """ % quote_like(text)
        results = Person.select(email_query, clauseTables=['EmailAddress'])
        name_query = "fti @@ ftq(%s) AND merged is NULL" % quote(text)
        name_query += " AND " + base_query
        return results.union(Person.select(name_query), orderBy=orderBy)

    def findPerson(
            self, text="", orderBy=None, exclude_inactive_accounts=True):
        """See `IPersonSet`."""
        if orderBy is None:
            orderBy = Person._sortingColumnsForSetOperations
        text = text.lower()
        base_query = """
            Person.teamowner IS NULL
            AND Person.merged IS NULL
            AND EmailAddress.person = Person.id
            """
        if exclude_inactive_accounts:
            base_query += (" AND Person.account_status not in (%s)"
                           % ','.join(sqlvalues(*INACTIVE_ACCOUNT_STATUSES)))
        clauseTables = ['EmailAddress']
        if text:
            # We use a UNION here because this makes things *a lot* faster
            # than if we did a single SELECT with the two following clauses
            # ORed.
            email_query = ("%s AND lower(EmailAddress.email) LIKE %s || '%%'"
                           % (base_query, quote_like(text)))
            name_query = ('%s AND Person.fti @@ ftq(%s)'
                          % (base_query, quote(text)))
            results = Person.select(email_query, clauseTables=clauseTables)
            results = results.union(
                Person.select(name_query, clauseTables=clauseTables))
        else:
            results = Person.select(base_query, clauseTables=clauseTables)

        return results.orderBy(orderBy)

    def findTeam(self, text, orderBy=None):
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
        emailaddress = getUtility(IEmailAddressSet).getByEmail(email)
        if emailaddress is None:
            return None
        assert emailaddress.person is not None
        return emailaddress.person

    def getUbunteros(self, orderBy=None):
        """See `IPersonSet`."""
        if orderBy is None:
            # The fact that the query below is unique makes it
            # impossible to use person_sort_key(), and rewriting it to
            # use a subselect is more expensive. -- kiko
            orderBy = ["Person.displayname", "Person.name"]
        sigset = getUtility(ISignedCodeOfConductSet)
        lastdate = sigset.getLastAcceptedDate()

        query = AND(Person.q.id==SignedCodeOfConduct.q.ownerID,
                    SignedCodeOfConduct.q.active==True,
                    SignedCodeOfConduct.q.datecreated>=lastdate)

        return Person.select(query, distinct=True, orderBy=orderBy)

    def getPOFileContributors(self, pofile):
        """See `IPersonSet`."""
        contributors = Person.select("""
            POFileTranslator.person = Person.id AND
            POFileTranslator.pofile = %s""" % quote(pofile),
            clauseTables=["POFileTranslator"],
            distinct=True,
            # XXX: kiko 2006-10-19:
            # We can't use Person.sortingColumns because this is a
            # distinct query. To use it we'd need to add the sorting
            # function to the column results and then ignore it -- just
            # like selectAlso does, ironically.
            orderBy=["Person.displayname", "Person.name"])
        return contributors

    def getPOFileContributorsByDistroSeries(self, distroseries, language):
        """See `IPersonSet`."""
        contributors = Person.select("""
            POFileTranslator.person = Person.id AND
            POFileTranslator.pofile = POFile.id AND
            POFile.language = %s AND
            POFile.potemplate = POTemplate.id AND
            POTemplate.distroseries = %s AND
            POTemplate.iscurrent = TRUE"""
                % sqlvalues(language, distroseries),
            clauseTables=["POFileTranslator", "POFile", "POTemplate"],
            distinct=True,
            # See comment in getPOFileContributors about how we can't
            # use Person.sortingColumns.
            orderBy=["Person.displayname", "Person.name"])
        return contributors

    def latest_teams(self, limit=5):
        """See `IPersonSet`."""
        return Person.select("Person.teamowner IS NOT NULL",
            orderBy=['-datecreated'], limit=limit)

    def _merge_person_decoration(self, to_person, from_person, skip, cur,
        decorator_table, person_pointer_column, additional_person_columns):
        """Merge a table that "decorates" Person.

        Because "person decoration" is becoming more frequent, we create a
        helper function that can be used for tables that decorate person.

        :to_person:       the IPerson that is "real"
        :from_person:     the IPerson that is being merged away
        :skip:            a list of table/column pairs that have been
                          handled
        :cur:             a database cursor
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
        cur = cursor()

        # First, update the main UNIQUE pointer row which links the
        # decorator table to Person. We do not update rows if there are
        # already rows in the table that refer to the to_person
        cur.execute(
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
            cur.execute(
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
        assert getUtility(IMailingListSet).get(from_person.name) is None, (
            "Can't merge teams which have mailing lists into other teams.")

        # since we are doing direct SQL manipulation, make sure all
        # changes have been flushed to the database
        flush_database_updates()

        if getUtility(IEmailAddressSet).getByPerson(from_person).count() > 0:
            raise AssertionError('from_person still has email addresses.')

        if from_person.is_team and from_person.allmembers.count() > 0:
            raise AssertionError(
                "Only teams without active members can be merged")

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
            # This table is handled entirely by triggers.
            ('validpersonorteamcache', 'id'),
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
            to_person, from_person, skip, cur, 'PersonLocation', 'person',
            ['last_modified_by', ])

        # Update GPGKey. It won't conflict, but our sanity checks don't
        # know that.
        cur.execute(
            'UPDATE GPGKey SET owner=%(to_id)d WHERE owner=%(from_id)d'
            % vars())
        skip.append(('gpgkey','owner'))

        # Update OpenID. Just trash the authorizations for from_id - don't
        # risk opening up auth wider than the user actually wants.
        cur.execute("""
                DELETE FROM OpenIdAuthorization WHERE person=%(from_id)d
                """ % vars()
                )
        skip.append(('openidauthorization', 'person'))

        # Update WikiName. Delete the from entry for our internal wikis
        # so it can be reused. Migrate the non-internal wikinames.
        # Note we only allow one wikiname per person for the UBUNTU_WIKI_URL
        # wiki.
        quoted_internal_wikiname = quote(UBUNTU_WIKI_URL)
        cur.execute("""
            DELETE FROM WikiName
            WHERE person=%(from_id)d AND wiki=%(quoted_internal_wikiname)s
            """ % vars()
            )
        cur.execute("""
            UPDATE WikiName SET person=%(to_id)d WHERE person=%(from_id)d
            """ % vars()
            )
        skip.append(('wikiname', 'person'))

        # Update shipit shipments.
        cur.execute('''
            UPDATE ShippingRequest SET recipient=%(to_id)s
            WHERE recipient = %(from_id)s AND (
                shipment IS NOT NULL
                OR status IN (%(cancelled)s, %(denied)s)
                OR NOT EXISTS (
                    SELECT TRUE FROM ShippingRequest
                    WHERE recipient = %(to_id)s
                        AND status = %(shipped)s
                    LIMIT 1
                    )
                )
            ''' % sqlvalues(to_id=to_id, from_id=from_id,
                            cancelled=ShippingRequestStatus.CANCELLED,
                            denied=ShippingRequestStatus.DENIED,
                            shipped=ShippingRequestStatus.SHIPPED))
        # Technically, we don't need the not cancelled nor denied
        # filter, as these rows should have already been dealt with.
        # I'm using it anyway for added paranoia.
        cur.execute('''
            DELETE FROM RequestedCDs USING ShippingRequest
            WHERE RequestedCDs.request = ShippingRequest.id
                AND recipient = %(from_id)s
                AND status NOT IN (%(cancelled)s, %(denied)s, %(shipped)s)
            ''' % sqlvalues(from_id=from_id,
                            cancelled=ShippingRequestStatus.CANCELLED,
                            denied=ShippingRequestStatus.DENIED,
                            shipped=ShippingRequestStatus.SHIPPED))
        cur.execute('''
            DELETE FROM ShippingRequest
            WHERE recipient = %(from_id)s
                AND status NOT IN (%(cancelled)s, %(denied)s, %(shipped)s)
            ''' % sqlvalues(from_id=from_id,
                            cancelled=ShippingRequestStatus.CANCELLED,
                            denied=ShippingRequestStatus.DENIED,
                            shipped=ShippingRequestStatus.SHIPPED))
        skip.append(('shippingrequest', 'recipient'))

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
                ''', vars())
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
            WHERE owner=%(from_id)d AND id NOT IN
                (
                SELECT id
                FROM MentoringOffer
                WHERE owner = %(to_id)d
                )
            ''' % vars())
        cur.execute('''
            UPDATE MentoringOffer
            SET team=%(to_id)d
            WHERE team=%(from_id)d AND id NOT IN
                (
                SELECT id
                FROM MentoringOffer
                WHERE team = %(to_id)d
                )
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
            WHERE person=%(from_id)d AND id NOT IN (
                SELECT id FROM BugNotificationRecipient
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
            UPDATE PackageBugSupervisor SET bug_supervisor=%(to_id)s
            WHERE bug_supervisor=%(from_id)s
            ''', vars())
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
        # XXX: StuartBishop 2005-03-31:
        # Add sampledata and test to confirm this case.
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

        # Flag the account as merged
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

        # Since we've updated the database behind SQLObject's back,
        # flush its caches.
        flush_database_caches()

    def getTranslatorsByLanguage(self, language):
        """See `IPersonSet`."""
        # XXX CarlosPerelloMarin 2007-03-31 bug=102257:
        # The KarmaCache table doesn't have a field to store karma per
        # language, so we are actually returning the people with the most
        # translation karma that have this language selected in their
        # preferences.
        return Person.select('''
            PersonLanguage.person = Person.id AND
            PersonLanguage.language = %s AND
            KarmaCache.person = Person.id AND
            KarmaCache.product IS NULL AND
            KarmaCache.project IS NULL AND
            KarmaCache.sourcepackagename IS NULL AND
            KarmaCache.distribution IS NULL AND
            KarmaCache.category = KarmaCategory.id AND
            KarmaCategory.name = 'translations'
            ''' % sqlvalues(language), orderBy=['-KarmaCache.karmavalue'],
            clauseTables=[
                'PersonLanguage', 'KarmaCache', 'KarmaCategory'])

    def getValidPersons(self, persons):
        """See `IPersonSet.`"""
        person_ids = [person.id for person in persons]
        if len(person_ids) == 0:
            return []
        valid_person_cache = ValidPersonOrTeamCache.select(
            "id IN %s" % sqlvalues(person_ids))
        valid_person_ids = set(cache.id for cache in valid_person_cache)
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

    def getSubscribersForTargets(self, targets, recipients=None):
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


class PersonLanguage(SQLBase):
    _table = 'PersonLanguage'

    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)
    language = ForeignKey(foreignKey='Language', dbName='language',
                          notNull=True)


class SSHKey(SQLBase):
    implements(ISSHKey)

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


class WikiName(SQLBase):
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

    def getUbuntuWikiByPerson(self, person):
        """See `IWikiNameSet`."""
        return WikiName.selectOneBy(person=person, wiki=UBUNTU_WIKI_URL)

    def getOtherWikisByPerson(self, person):
        """See `IWikiNameSet`."""
        return WikiName.select(AND(WikiName.q.personID==person.id,
                                   WikiName.q.wiki!=UBUNTU_WIKI_URL))

    def getAllWikisByPerson(self, person):
        """See `IWikiNameSet`."""
        return WikiName.selectBy(person=person)

    def get(self, id):
        """See `IWikiNameSet`."""
        try:
            return WikiName.get(id)
        except SQLObjectNotFound:
            return None

    def new(self, person, wiki, wikiname):
        """See `IWikiNameSet`."""
        return WikiName(person=person, wiki=wiki, wikiname=wikiname)

    def exists(self, wikiname, wiki=UBUNTU_WIKI_URL):
        """See `IWikiNameSet`."""
        return WikiName.selectOneBy(wiki=wiki, wikiname=wikiname) is not None


class JabberID(SQLBase):
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


class IrcID(SQLBase):
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
