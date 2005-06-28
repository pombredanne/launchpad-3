# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Person', 'PersonSet', 'EmailAddress', 'EmailAddressSet',
    'GPGKey', 'GPGKeySet', 'SSHKey', 'SSHKeySet', 'ArchUserID',
    'ArchUserIDSet', 'WikiName', 'WikiNameSet', 'JabberID',
    'JabberIDSet', 'IrcID', 'IrcIDSet', 'TeamMembership',
    'TeamMembershipSet', 'TeamParticipation', 'Karma'
    ]

import itertools
import sets
from datetime import datetime, timedelta
import pytz
import sha

# Zope interfaces
from zope.interface import implements, directlyProvides, directlyProvidedBy
from zope.component import getUtility

# SQL imports
from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, SQLObjectNotFound
from sqlobject.sqlbuilder import AND
from canonical.database.sqlbase import SQLBase, quote, cursor, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database import postgresql

# canonical imports
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor

from canonical.launchpad.interfaces import \
    IPerson, ITeam, IPersonSet, ITeamMembership, ITeamParticipation, \
    ITeamMembershipSet, IEmailAddress, IWikiName, IIrcID, IArchUserID, \
    IJabberID, IIrcIDSet, IArchUserIDSet, ISSHKeySet, IJabberIDSet, \
    IWikiNameSet, IGPGKeySet, ISSHKey, IGPGKey, IKarma, IKarmaPointsManager, \
    IMaintainershipSet, IEmailAddressSet, ISourcePackageReleaseSet, \
    IPasswordEncryptor, ICalendarOwner

from canonical.launchpad.database.translation_effort import TranslationEffort
from canonical.launchpad.database.bug import BugTask
from canonical.launchpad.database.cal import Calendar
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.codeofconduct import SignedCodeOfConduct
from canonical.launchpad.database.logintoken import LoginToken

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.searchbuilder import NULL

from canonical.lp.dbschema import \
    EnumCol, SSHKeyType, KarmaType, EmailAddressStatus, \
    TeamSubscriptionPolicy, TeamMembershipStatus, GPGKeyAlgorithm

from canonical.foaf import nickname


class Person(SQLBase):
    """A Person."""

    implements(IPerson, ICalendarOwner)

    _defaultOrder = 'displayname'

    name = StringCol(dbName='name', alternateID=True, notNull=True)
    password = StringCol(dbName='password', default=None)
    givenname = StringCol(dbName='givenname', default=None)
    familyname = StringCol(dbName='familyname', default=None)
    displayname = StringCol(dbName='displayname', notNull=True)
    teamdescription = StringCol(dbName='teamdescription', default=None)

    teamowner = ForeignKey(dbName='teamowner', foreignKey='Person',
                           default=None)

    sshkeys = MultipleJoin('SSHKey', joinColumn='person')

    karma = IntCol(dbName='karma', default=0)
    karmatimestamp = UtcDateTimeCol(dbName='karmatimestamp', default=UTC_NOW)

    subscriptionpolicy = EnumCol(
        dbName='subscriptionpolicy',
        schema=TeamSubscriptionPolicy,
        default=TeamSubscriptionPolicy.MODERATED)
    defaultrenewalperiod = IntCol(dbName='defaultrenewalperiod', default=None)
    defaultmembershipperiod = IntCol(dbName='defaultmembershipperiod',
                                     default=None)

    merged = ForeignKey(dbName='merged', foreignKey='Person', default=None)

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    # RelatedJoin gives us also an addLanguage and removeLanguage for free
    languages = RelatedJoin('Language', joinColumn='person',
                            otherColumn='language',
                            intermediateTable='PersonLanguage')

    # relevant joins
    ownedBounties = MultipleJoin('Bounty', joinColumn='owner')
    reviewerBounties = MultipleJoin('Bounty', joinColumn='reviewer')
    claimedBounties = MultipleJoin('Bounty', joinColumn='claimant')
    subscribedBounties = RelatedJoin('Bounty', joinColumn='person',
                                     otherColumn='bounty',
                                     intermediateTable='BountySubscription')
    gpgkeys = MultipleJoin('GPGKey', joinColumn='owner')

    calendar = ForeignKey(dbName='calendar', foreignKey='Calendar',
                          default=None, forceDBName=True)
    def getOrCreateCalendar(self):
        if not self.calendar:
            self.calendar = Calendar(title=self.browsername,
                                     revision=0)
        return self.calendar

    timezone_name = StringCol(dbName='timezone_name', default=None)

    def get(cls, id, connection=None, selectResults=None):
        """Override the classmethod get from the base class.

        In this case when we're getting a team we mark it with ITeam.
        """
        # XXX: Use the same thing Bjorn used for malone here.
        #      -- SteveAlexander, 2005-04-23

        # This is simulating 'super' without using 'super' to show
        # how nasty sqlobject actually is.
        # -- SteveAlexander, 2005-04-23
        val = SQLBase.get.im_func(cls, id, connection=connection,
                                  selectResults=selectResults)
        if val.teamowner is not None:
            directlyProvides(val, directlyProvidedBy(val) + ITeam)
        return val
    get = classmethod(get)

    def browsername(self):
        """Return a name suitable for display on a web page.

        1. If we have a displayname, then browsername is the displayname.

        2. If we have a familyname or givenname, then the browsername
           is "FAMILYNAME Givenname".

        3. If we have no displayname, no familyname and no givenname,
           the browsername is self.name.

        >>> class DummyPerson:
        ...     displayname = None
        ...     familyname = None
        ...     givenname = None
        ...     name = 'the_name'
        ...     # This next line is some special evil magic to allow us to
        ...     # unit test browsername in isolation.
        ...     browsername = Person.browsername.im_func
        ...
        >>> person = DummyPerson()

        Check with just the name.

        >>> person.browsername
        'the_name'

        Check with givenname and name.  Just givenname is used.

        >>> person.givenname = 'the_givenname'
        >>> person.browsername
        'the_givenname'

        Check with givenname, familyname and name.  Both givenname and
        familyname are used.

        >>> person.familyname = 'the_familyname'
        >>> person.browsername
        'THE_FAMILYNAME the_givenname'

        Check with givenname, familyname, name and displayname.
        Only displayname is used.

        >>> person.displayname = 'the_displayname'
        >>> person.browsername
        'the_displayname'

        Remove familyname to check with givenname, name and displayname.
        Only displayname is used.

        >>> person.familyname = None
        >>> person.browsername
        'the_displayname'

        """
        if self.displayname:
            return self.displayname
        elif self.familyname or self.givenname:
            # Make a list containing either ['FAMILYNAME'] or
            # ['FAMILYNAME', 'Givenname'] or ['Givenname'].
            # Then turn it into a space-separated string.
            L = []
            if self.familyname is not None:
                L.append(self.familyname.upper())
            if self.givenname is not None:
                L.append(self.givenname)
            return ' '.join(L)
        else:
            return self.name
    browsername = property(browsername)

    def isTeam(self):
        """See IPerson."""
        return self.teamowner is not None

    def assignKarma(self, karmatype, points=None):
        if karmatype.schema is not KarmaType:
            raise TypeError('"%s" is not a valid KarmaType value' % karmatype)
        if points is None:
            try:
                points = getUtility(IKarmaPointsManager).getPoints(karmatype)
            except KeyError:
                # What about defining a default number of points?
                points = 0
                # Print a warning here, cause someone forgot to add the
                # karmatype to KARMA_POINTS.
        Karma(person=self, karmatype=karmatype, points=points)
        # XXX: salgado, 2005-01-12: I think we should recalculate the karma
        # here, but first we must define karma points and depreciation
        # methods.
        self.karma += points

    def inTeam(self, team):
        tp = TeamParticipation.selectOneBy(teamID=team.id, personID=self.id)
        if tp is not None or self.id == team.teamownerID:
            return True
        elif team.teamowner is not None and not team.teamowner.inTeam(team):
            # The owner is not a member but must retain his rights over
            # this team. This person may be a member of the owner, and in this
            # case it'll also have rights over this team.
            return self.inTeam(team.teamowner)
        else:
            return False

    def hasMembershipEntryFor(self, team):
        results = TeamMembership.selectBy(personID=self.id, teamID=team.id)
        return bool(results.count())

    def hasParticipationEntryFor(self, team):
        results = TeamParticipation.selectBy(personID=self.id, teamID=team.id)
        return bool(results.count())

    def leave(self, team):
        """See IPerson."""
        assert not ITeam.providedBy(self)

        active = [TeamMembershipStatus.ADMIN, TeamMembershipStatus.APPROVED]
        tm = TeamMembership.selectOneBy(personID=self.id, teamID=team.id)
        if tm is None or tm.status not in active:
            # Ok, we're done. You are not an active member and still not being.
            return

        team.setMembershipStatus(self, TeamMembershipStatus.DEACTIVATED,
                                 tm.dateexpires)

    def join(self, team):
        """See IPerson."""
        assert not ITeam.providedBy(self)

        expired = TeamMembershipStatus.EXPIRED
        proposed = TeamMembershipStatus.PROPOSED
        approved = TeamMembershipStatus.APPROVED
        declined = TeamMembershipStatus.DECLINED
        deactivated = TeamMembershipStatus.DEACTIVATED

        if team.subscriptionpolicy == TeamSubscriptionPolicy.RESTRICTED:
            return False
        elif team.subscriptionpolicy == TeamSubscriptionPolicy.MODERATED:
            status = proposed
        elif team.subscriptionpolicy == TeamSubscriptionPolicy.OPEN:
            status = approved

        tm = TeamMembership.selectOneBy(personID=self.id, teamID=team.id)
        expires = team.defaultexpirationdate
        if tm is None:
            team.addMember(self, status)
        else:
            if (tm.status == declined and
                team.subscriptionpolicy == TeamSubscriptionPolicy.MODERATED):
                # The user is a DECLINED member, we just have to change the
                # status to PROPOSED.
                team.setMembershipStatus(self, status, expires)
            elif (tm.status in [expired, deactivated, declined] and
                  team.subscriptionpolicy == TeamSubscriptionPolicy.OPEN):
                team.setMembershipStatus(self, status, expires)
            else:
                return False

        return True

    #
    # ITeam methods
    #

    def subscriptionPolicyDesc(self):
        return '%s. %s' % (self.subscriptionpolicy.title,
                           self.subscriptionpolicy.description)

    def getSuperTeams(self):
        query = ('Person.id = TeamParticipation.team AND '
                 'TeamParticipation.person = %d' % self.id)
        return Person.select(query, clauseTables=['TeamParticipation'])

    def getSubTeams(self):
        query = ('Person.id = TeamParticipation.person AND '
                 'TeamParticipation.team = %d AND '
                 'Person.teamowner IS NOT NULL' % self.id)
        return Person.select(query, clauseTables=['TeamParticipation'])

    def addMember(self, person, status=TeamMembershipStatus.APPROVED,
                  reviewer=None, comment=None):
        assert self.teamowner is not None
        if person.hasMembershipEntryFor(self):
            # <person> is already a member.
            return 

        assert status in [TeamMembershipStatus.APPROVED,
                          TeamMembershipStatus.PROPOSED]

        expires = self.defaultexpirationdate
        TeamMembership(personID=person.id, teamID=self.id, status=status,
                       dateexpires=expires, reviewer=reviewer, 
                       reviewercomment=comment)

        if status == TeamMembershipStatus.APPROVED:
            _fillTeamParticipation(person, self)

    def setMembershipStatus(self, person, status, expires=None, reviewer=None,
                            comment=None):
        tm = TeamMembership.selectOneBy(personID=person.id, teamID=self.id)

        # XXX: Do we need this assert?
        #      -- SteveAlexander, 2005-04-23
        assert tm is not None

        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN
        expired = TeamMembershipStatus.EXPIRED
        declined = TeamMembershipStatus.DECLINED
        deactivated = TeamMembershipStatus.DEACTIVATED
        proposed = TeamMembershipStatus.PROPOSED

        # Make sure the transition from the current status to the given status
        # is allowed. All allowed transitions are in the TeamMembership spec.
        if tm.status in [admin, approved]:
            assert status in [approved, admin, expired, deactivated]
        elif tm.status in [deactivated]:
            assert status in [approved]
        elif tm.status in [expired]:
            assert status in [approved]
        elif tm.status in [proposed]:
            assert status in [approved, declined]
        elif tm.status in [declined]:
            assert status in [proposed, approved]

        now = datetime.now(pytz.timezone('UTC'))
        if expires is not None and expires <= now:
            expires = now
            status = expired

        tm.status = status
        tm.dateexpires = expires
        tm.reviewer = reviewer
        tm.reviewercomment = comment

        if ((status == approved and tm.status != admin) or
            (status == admin and tm.status != approved)):
            _fillTeamParticipation(person, self)
        elif status in [deactivated, expired]:
            _cleanTeamParticipation(person, self)

    def _getMembersByStatus(self, status):
        # XXX Needs a system doc test. SteveAlexander 2005-04-23
        query = ("TeamMembership.team = %s AND TeamMembership.status = %s "
                 "AND TeamMembership.person = Person.id" %
                 sqlvalues(self.id, status))
        return Person.select(query, clauseTables=['TeamMembership'])

    def _getEmailsByStatus(self, status):
        query = AND(EmailAddress.q.personID==self.id,
                    EmailAddress.q.status==status)
        return EmailAddress.select(query)

    def title(self):
        return self.browsername
    title = property(title)

    def allmembers(self):
        return _getAllMembers(self)
    allmembers = property(allmembers)

    def deactivatedmembers(self):
        return self._getMembersByStatus(TeamMembershipStatus.DEACTIVATED)
    deactivatedmembers = property(deactivatedmembers)

    def expiredmembers(self):
        return self._getMembersByStatus(TeamMembershipStatus.EXPIRED)
    expiredmembers = property(expiredmembers)

    def declinedmembers(self):
        return self._getMembersByStatus(TeamMembershipStatus.DECLINED)
    declinedmembers = property(declinedmembers)

    def proposedmembers(self):
        return self._getMembersByStatus(TeamMembershipStatus.PROPOSED)
    proposedmembers = property(proposedmembers)

    def administrators(self):
        return self._getMembersByStatus(TeamMembershipStatus.ADMIN)
    administrators = property(administrators)

    def approvedmembers(self):
        return self._getMembersByStatus(TeamMembershipStatus.APPROVED)
    approvedmembers = property(approvedmembers)

    def activemembers(self):
        return self.approvedmembers.union(self.administrators)
    activemembers = property(activemembers)

    def inactivemembers(self):
        return self.expiredmembers.union(self.deactivatedmembers)
    inactivemembers = property(inactivemembers)

    def memberships(self):
        return TeamMembership.selectBy(personID=self.id)
    memberships = property(memberships)

    def defaultexpirationdate(self):
        days = self.defaultmembershipperiod
        if days:
            return datetime.now(pytz.timezone('UTC')) + timedelta(days)
        else:
            return None
    defaultexpirationdate = property(defaultexpirationdate)

    def defaultrenewedexpirationdate(self):
        days = self.defaultrenewalperiod
        if days:
            return datetime.now(pytz.timezone('UTC')) + timedelta(days)
        else:
            return None
    defaultrenewedexpirationdate = property(defaultrenewedexpirationdate)

    def validateAndEnsurePreferredEmail(self, email):
        """See IPerson."""
        if not IEmailAddress.providedBy(email):
            raise TypeError, (
                "Any person's email address must provide the IEmailAddress "
                "interface. %s doesn't." % email)
        assert email.person == self
        assert self.preferredemail != email

        if self.preferredemail is None:
            # This branch will be executed only in the first time a person
            # uses Launchpad. Either when creating a new account or when
            # resetting the password of an automatically created one.
            self.preferredemail = email
        else:
            email.status = EmailAddressStatus.VALIDATED

    def _setPreferredemail(self, email):
        """See IPerson."""
        if not IEmailAddress.providedBy(email):
            raise TypeError, (
                "Any person's email address must provide the IEmailAddress "
                "interface. %s doesn't." % email)
        assert email.person.id == self.id
        preferredemail = self.preferredemail
        if preferredemail is not None:
            preferredemail.status = EmailAddressStatus.VALIDATED
            # We need to flush updates, because we don't know what order
            # SQLObject will issue the changes and we can't set the new
            # address to PREFERRED until the old one has been set to VALIDATED
            preferredemail.syncUpdate()
        email.status = EmailAddressStatus.PREFERRED

    def _getPreferredemail(self):
        emails = self._getEmailsByStatus(EmailAddressStatus.PREFERRED)
        # There can be only one preferred email for a given person at a
        # given time, and this constraint must be ensured in the DB, but
        # it's not a problem if we ensure this constraint here as well.
        emails = list(emails)
        length = len(emails)
        assert length <= 1
        if length:
            return emails[0]
        else:
            return None
    preferredemail = property(_getPreferredemail, _setPreferredemail)

    def preferredemail_sha1(self):
        """See IPerson.preferredemail_sha1"""
        preferredemail = self.preferredemail
        if preferredemail:
            return sha.new(preferredemail.email).hexdigest().upper()
        else:
            return None
    preferredemail_sha1 = property(preferredemail_sha1)

    def validatedemails(self):
        return self._getEmailsByStatus(EmailAddressStatus.VALIDATED)
    validatedemails = property(validatedemails)

    def unvalidatedemails(self):
        query = "requester=%d AND email IS NOT NULL" % self.id
        return sets.Set([token.email for token in LoginToken.select(query)])
    unvalidatedemails = property(unvalidatedemails)

    def guessedemails(self):
        return self._getEmailsByStatus(EmailAddressStatus.NEW)
    guessedemails = property(guessedemails)

    def reportedbugs(self):
        return BugTask.selectBy(ownerID=self.id)
    reportedbugs= property(reportedbugs)

    def translations(self):
        return TranslationEffort.selectBy(ownerID=self.id)
    translations = property(translations)

    def activities(self):
        return Karma.selectBy(personID=self.id)
    activities = property(activities)

    def wiki(self):
        # XXX: salgado, 2005-01-14: This method will probably be replaced
        # by a MultipleJoin since we have a good UI to add multiple Wikis.
        return WikiName.selectOneBy(personID=self.id)
    wiki = property(wiki)

    def jabber(self):
        # XXX: salgado, 2005-01-14: This method will probably be replaced
        # by a MultipleJoin since we have a good UI to add multiple
        # JabberIDs.

        # XXX: Needs system doc test.  SteveAlexander 2005-04-24.
        return JabberID.selectOneBy(personID=self.id)
    jabber = property(jabber)

    def archuser(self):
        # XXX: salgado, 2005-01-14: This method will probably be replaced
        # by a MultipleJoin since we have a good UI to add multiple
        # ArchUserIDs.

        # XXX: Needs system doc test.  SteveAlexander 2005-04-24.
        return ArchUserID.selectOneBy(personID=self.id)
    archuser = property(archuser)

    def irc(self):
        # XXX: salgado, 2005-01-14: This method will probably be replaced
        # by a MultipleJoin since we have a good UI to add multiple
        # IrcIDs.

        # XXX: Needs system doc test.  SteveAlexander 2005-04-24.
        return IrcID.selectOneBy(personID=self.id)
    irc = property(irc)

    def maintainerships(self):
        maintainershipsutil = getUtility(IMaintainershipSet)
        return maintainershipsutil.getByPersonID(self.id)
    maintainerships = property(maintainerships)

    def packages(self):
        sprutil = getUtility(ISourcePackageReleaseSet)
        return sprutil.getByCreatorID(self.id)
    packages = property(packages)

    def ubuntite(self):
        # XXX: cprov 20050226
        # Verify the the SignedCoC version too
        # we can't do it before add the field version on
        # SignedCoC table. Then simple compare the already
        # checked field with what we grab from CoCConf utility.
        # Simply add 'SignedCodeOfConduct.version = %s' % conf.current
        # in query when the field was landed.
        query = AND(SignedCodeOfConduct.q.active==True,
                    SignedCodeOfConduct.q.ownerID==self.id)

        return bool(SignedCodeOfConduct.select(query).count())
    ubuntite = property(ubuntite)


class PersonSet:
    """The set of persons."""
    implements(IPersonSet)

    def __init__(self):
        self.title = 'Launchpad People'

    def __iter__(self):
        return self.getall()

    def __getitem__(self, personid):
        """See IPersonSet."""
        person = self.get(personid)
        if person is None:
            raise KeyError(personid)
        else:
            return person

    def newTeam(self, **kw):
        """See IPersonSet."""
        ownerID = kw.get('teamownerID')
        assert ownerID
        owner = Person.get(ownerID)
        team = Person(**kw)
        team.addMember(owner)
        team.setMembershipStatus(owner, TeamMembershipStatus.ADMIN)
        return team

    def newPerson(self, **kw):
        """See IPersonSet."""
        assert not kw.get('teamownerID')
        return Person(**kw)

    def getByName(self, name, default=None):
        """See IPersonSet."""
        query = AND(Person.q.name==name, Person.q.mergedID==None)
        person = Person.selectOne(query)
        if person is None:
            return default
        return person

    def search(self, password=None):
        """See IPersonSet."""
        query = None
        if password:
            if password == NULL:
                query = "password IS NULL"
            else:
                query = "password = '%s'" % quote(password)

        return Person.select(query)

    def nameIsValidForInsertion(self, name):
        if not valid_name(name) or self.getByName(name) is not None:
            return False
        else:
            return True

    def peopleCount(self):
        return self._getAllPersons().count()

    def getAllPersons(self, orderBy=None):
        return self._getAllPersons(orderBy=orderBy)

    def _getAllPersons(self, orderBy=None):
        query = AND(Person.q.teamownerID==None, Person.q.mergedID==None)
        return Person.select(query, orderBy=orderBy)

    def teamsCount(self):
        return self._getAllTeams().count()

    def getAllTeams(self, orderBy=None):
        return self._getAllTeams(orderBy=orderBy)

    def _getAllTeams(self, orderBy=None):
        return Person.select(Person.q.teamownerID!=None, orderBy=orderBy)

    def findByName(self, name, orderBy=None):
        query = "fti @@ ftq(%s) AND merged is NULL" % quote(name)
        return Person.select(query, orderBy=orderBy)

    def findPersonByName(self, name, orderBy=None):
        query = "fti @@ ftq(%s) AND teamowner is NULL AND merged is NULL"
        return Person.select(query % quote(name), orderBy=orderBy)

    def findTeamByName(self, name, orderBy=None):
        query = "fti @@ ftq(%s) AND teamowner is not NULL" % quote(name)
        return Person.select(query, orderBy=orderBy)

    def get(self, personid, default=None):
        """See IPersonSet."""
        try:
            return Person.get(personid)
        except SQLObjectNotFound:
            return default

    def getByEmail(self, email, default=None):
        """See IPersonSet."""
        result = EmailAddress.selectOne(
            "lower(email) = %s" % quote(email.lower()))
        if result is None:
            return default
        return result.person

    def getUbuntites(self, orderBy=None):
        """See IPersonSet."""
        clauseTables = ['SignedCodeOfConduct']

        # XXX: cprov 20050226
        # Verify the the SignedCoC version too
        # we can't do it before add the field version on
        # SignedCoC version.
        # Needs DISTINCT or check to prevent Sign CoC twice.
        query = ('Person.id = SignedCodeOfConduct.owner AND '
                 'SignedCodeOfConduct.active = True')
        return Person.select(query, clauseTables=clauseTables, orderBy=orderBy)

    def merge(self, from_person, to_person):
        """Merge a person into another.

        The old user (from_person) will be left as an atavism

        XXX: Are we game to delete from_person yet?
            -- StuartBishop 20050315
        XXX: let's let it roll for a while and see what cruft develops. If
             it's clean, let's start deleting
            -- MarkShuttleworth 20050528
        """
        # Sanity checks
        if ITeam.providedBy(from_person):
            raise TypeError('Got a team as from_person.')
        if ITeam.providedBy(to_person):
            raise TypeError('Got a team as to_person.')
        if not IPerson.providedBy(from_person):
            raise TypeError('from_person is not a person.')
        if not IPerson.providedBy(to_person):
            raise TypeError('to_person is not a person.')

        if len(getUtility(IEmailAddressSet).getByPerson(from_person.id)) > 0:
            raise ValueError('from_person still has email addresses.')

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

        # Update GPGKey. It won't conflict, but our sanity checks don't
        # know that
        cur.execute('UPDATE GPGKey SET owner=%(to_id)d WHERE owner=%(from_id)d'
                    % vars())
        skip.append(('gpgkey','owner'))

        # Update only the BountySubscriptions that will not conflict
        # XXX: Add sampledata and test to confirm this case
        # -- StuartBishop 20050331
        cur.execute('''
            UPDATE BountySubscription
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND id NOT IN (
                SELECT a.id
                FROM BountySubscription AS a, BountySubscription AS b
                WHERE a.person = %(from_id)d AND b.person = %(to_id)d
                AND a.bounty = b.bounty
                )
            ''' % vars())
        skip.append(('bountysubscription', 'person'))

        # Update only the POSubscriptions that will not conflict
        # XXX: Add sampledata and test to confirm this case
        # -- StuartBishop 20050331
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

        # Update the POSubmissions. They should not conflict since each of
        # them is independent
        cur.execute('''
            UPDATE POSubmission
            SET person=%(to_id)d
            WHERE person=%(from_id)d
            ''' % vars())
        skip.append(('posubmission', 'person'))
    
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

        # Flag the account as merged
        cur.execute('''
            UPDATE Person SET merged=%(to_id)d WHERE id=%(from_id)d
            ''' % vars())

    def createPerson(self, email, displayname=None, givenname=None,
                     familyname=None, password=None):
        """See IPersonSet."""
        try:
            name = nickname.generate_nick(email)
        except NicknameGenerationError:
            return None

        password = getUtility(IPasswordEncryptor).encrypt(password)
        person = self.newPerson(name=name, displayname=displayname,
                                givenname=givenname, familyname=familyname,
                                password=password)

        getUtility(IEmailAddressSet).new(email, person.id)
        return person


class EmailAddress(SQLBase):
    implements(IEmailAddress)

    _table = 'EmailAddress'

    email = StringCol(dbName='email', notNull=True, alternateID=True)
    status = EnumCol(dbName='status', schema=EmailAddressStatus, notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)

    def statusname(self):
        return self.status.title
    statusname = property(statusname)


class EmailAddressSet:
    implements(IEmailAddressSet)

    def get(self, emailid, default=None):
        """See IEmailAddressSet."""
        try:
            return EmailAddress.get(emailid)
        except SQLObjectNotFound:
            return default

    def __getitem__(self, emailid):
        """See IEmailAddressSet."""
        email = self.get(emailid)
        if email is None:
            raise KeyError(emailid)
        else:
            return email

    def getByPerson(self, personid):
        return EmailAddress.selectBy(personID=personid)

    def getByEmail(self, email, default=None):
        try:
            return EmailAddress.byEmail(email)
        except SQLObjectNotFound:
            return default

    def new(self, email, personID, status=EmailAddressStatus.NEW):
        email = email.strip()
        assert status in EmailAddressStatus.items
        return EmailAddress(email=email, status=status, person=personID)


class GPGKey(SQLBase):
    implements(IGPGKey)

    _table = 'GPGKey'

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    keyid = StringCol(dbName='keyid', notNull=True)
    fingerprint = StringCol(dbName='fingerprint', notNull=True)

    keysize = IntCol(dbName='keysize', notNull=True)

    algorithm = EnumCol(dbName='algorithm', notNull=True,
                        schema=GPGKeyAlgorithm)

    revoked = BoolCol(dbName='revoked', notNull=True)

    def algorithmname(self):
        return self.algorithm.title
    algorithmname = property(algorithmname)


class GPGKeySet:
    implements(IGPGKeySet)

    def new(self, ownerID, keyid, fingerprint, keysize,
            algorithm, revoked):
        # add new key in DB
        return GPGKey(owner=ownerID, keyid=keyid,
                      fingerprint=fingerprint, keysize=keysize,
                      algorithm=algorithm, revoked=revoked)

    def get(self, id, default=None):
        try:
            return GPGKey.get(id)
        except SQLObjectNotFound:
            return default

    def getByFingerprint(self, fingerprint, default=None):
        result = GPGKey.selectOneBy(fingerprint=fingerprint)
        if result is None:
            return default
        return result


class SSHKey(SQLBase):
    implements(ISSHKey)

    _table = 'SSHKey'

    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)
    keytype = EnumCol(dbName='keytype', notNull=True, schema=SSHKeyType)
    keytext = StringCol(dbName='keytext', notNull=True)
    comment = StringCol(dbName='comment', notNull=True)

    def keytypename(self):
        return self.keytype.title
    keytypename = property(keytypename)

    def keykind(self):
        # XXX: This seems rather odd, like it is meant for presentation
        #      of the name of a key.
        #      -- SteveAlexander, 2005-04-23
        if self.keytype == SSHKeyType.DSA:
            return 'ssh-dss'
        elif self.keytype == SSHKeyType.RSA:
            return 'ssh-rsa'
        else:
            return 'Unknown key type'
    keykind = property(keykind)


class SSHKeySet:
    implements(ISSHKeySet)

    def new(self, personID, keytype, keytext, comment):
        return SSHKey(personID=personID, keytype=keytype, keytext=keytext,
                      comment=comment)

    def get(self, id, default=None):
        try:
            return SSHKey.get(id)
        except SQLObjectNotFound:
            return default


class ArchUserID(SQLBase):
    implements(IArchUserID)

    _table = 'ArchUserID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    archuserid = StringCol(dbName='archuserid', notNull=True)


class ArchUserIDSet:
    implements(IArchUserIDSet)

    def new(self, personID, archuserid):
        return ArchUserID(personID=personID, archuserid=archuserid)


class WikiName(SQLBase):
    implements(IWikiName)

    _table = 'WikiName'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    wiki = StringCol(dbName='wiki', notNull=True)
    wikiname = StringCol(dbName='wikiname', notNull=True)


class WikiNameSet:
    implements(IWikiNameSet)

    def new(self, personID, wiki, wikiname):
        return WikiName(personID=personID, wiki=wiki, wikiname=wikiname)


class JabberID(SQLBase):
    implements(IJabberID)

    _table = 'JabberID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    jabberid = StringCol(dbName='jabberid', notNull=True)


class JabberIDSet:
    implements(IJabberIDSet)

    def new(self, personID, jabberid):
        return JabberID(personID=personID, jabberid=jabberid)


class IrcID(SQLBase):
    implements(IIrcID)

    _table = 'IrcID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    network = StringCol(dbName='network', notNull=True)
    nickname = StringCol(dbName='nickname', notNull=True)


class IrcIDSet:
    implements(IIrcIDSet)

    def new(self, personID, network, nickname):
        return IrcID(personID=personID, network=network, nickname=nickname)


class TeamMembership(SQLBase):
    implements(ITeamMembership)

    _table = 'TeamMembership'

    team = ForeignKey(dbName='team', foreignKey='Person', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    reviewer = ForeignKey(dbName='reviewer', foreignKey='Person', default=None)
    status = EnumCol(
        dbName='status', notNull=True, schema=TeamMembershipStatus)
    datejoined = UtcDateTimeCol(dbName='datejoined', default=UTC_NOW,
                                notNull=True)
    dateexpires = UtcDateTimeCol(dbName='dateexpires', default=None)
    reviewercomment = StringCol(dbName='reviewercomment', default=None)

    def statusname(self):
        return self.status.title
    statusname = property(statusname)

    def isExpired(self):
        return self.status == TeamMembershipStatus.EXPIRED


class TeamMembershipSet:

    implements(ITeamMembershipSet)

    _defaultOrder = 'Person.displayname'

    def getByPersonAndTeam(self, personID, teamID, default=None):
        result = TeamMembership.selectOneBy(personID=personID, teamID=teamID)
        if result is None:
            return default
        return result

    def getTeamMembersCount(self, teamID):
        return TeamMembership.selectBy(teamID=teamID).count()

    def _getMembershipsByStatuses(self, teamID, statuses, orderBy=None):
        # XXX: Don't use assert.
        #      SteveAlexander, 2005-04-23
        assert isinstance(teamID, int)
        orderBy = orderBy or self._defaultOrder
        clauses = []
        for status in statuses:
            clauses.append("TeamMembership.status = %s" % sqlvalues(status))
        clauses = " OR ".join(clauses)
        query = ("(%s) AND Person.id = TeamMembership.person AND "
                 "TeamMembership.team = %d" % (clauses, teamID))
        return TeamMembership.select(query, clauseTables=['Person'],
                                     orderBy=orderBy)

    def getActiveMemberships(self, teamID, orderBy=None):
        statuses = [TeamMembershipStatus.ADMIN, TeamMembershipStatus.APPROVED]
        return self._getMembershipsByStatuses(
            teamID, statuses, orderBy=orderBy)

    def getInactiveMemberships(self, teamID, orderBy=None):
        statuses = [TeamMembershipStatus.EXPIRED,
                    TeamMembershipStatus.DEACTIVATED]
        return self._getMembershipsByStatuses(
            teamID, statuses, orderBy=orderBy)

    def getProposedMemberships(self, teamID, orderBy=None):
        statuses = [TeamMembershipStatus.PROPOSED]
        return self._getMembershipsByStatuses(
            teamID, statuses, orderBy=orderBy)


class TeamParticipation(SQLBase):
    implements(ITeamParticipation)

    _table = 'TeamParticipation'

    team = ForeignKey(foreignKey='Person', dbName='team', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


def _getAllMembers(team, orderBy=None):
    query = ('Person.id = TeamParticipation.person AND '
             'TeamParticipation.team = %d' % team.id)
    return Person.select(query, clauseTables=['TeamParticipation'],
                         orderBy=orderBy)


def _cleanTeamParticipation(member, team):
    """Remove relevant entries in TeamParticipation for given member and team.

    Remove all tuples "member, team" from TeamParticipation for the given
    member and team (together with all its superteams), unless this member is
    an indirect member of the given team or the team owner. More information 
    on how to use the TeamParticipation table can be found in the 
    TeamParticipationUsage spec.
    """
    members = [member]
    if member.teamowner is not None:
        # The given member is, in fact, a team, and in this case we must 
        # remove all of its members from the given team and from its 
        # superteams.
        members.extend(_getAllMembers(member))

    for m in members:
        for subteam in team.getSubTeams():
            if m.hasParticipationEntryFor(subteam):
                # This member is an indirect member of this team. We cannot
                # remove its TeamParticipation entry.
                break
        else:
            for t in itertools.chain(team.getSuperTeams(), [team]):
                result = TeamParticipation.selectOneBy(
                    personID=m.id, teamID=t.id)
                if result is not None:
                    result.destroySelf()

def _fillTeamParticipation(member, team):
    """Add relevant entries in TeamParticipation for given member and team.

    Add a tuple "member, team" in TeamParticipation for the given team and all
    of its superteams. More information on how to use the TeamParticipation 
    table can be found in the TeamParticipationUsage spec.
    """
    members = [member]
    if member.teamowner is not None:
        # The given member is, in fact, a team, and in this case we must 
        # add all of its members to the given team and to its superteams.
        members.extend(_getAllMembers(member))

    for m in members:
        for t in itertools.chain(team.getSuperTeams(), [team]):
            if not m.hasParticipationEntryFor(t):
                TeamParticipation(personID=m.id, teamID=t.id)


class Karma(SQLBase):
    implements(IKarma)

    _table = 'Karma'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    points = IntCol(dbName='points', notNull=True, default=0)
    karmatype = EnumCol(dbName='karmatype', notNull=True, schema=KarmaType)
    datecreated = UtcDateTimeCol(dbName='datecreated', notNull=True,
                                 default=UTC_NOW)

    def karmatypename(self):
        return self.karmatype.title
    karmatypename = property(karmatypename)

