# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Person', 'PersonSet', 'createPerson', 'personFromPrincipal',
    'EmailAddress', 'EmailAddressSet', 'GPGKey', 'GPGKeySet',
    'SSHKey', 'SSHKeySet', 'ArchUserID', 'ArchUserIDSet',
    'WikiName', 'WikiNameSet', 'JabberID', 'JabberIDSet',
    'IrcID', 'IrcIDSet', 'TeamMembership', 'TeamMembershipSet',
    'TeamParticipation', 'Karma'
    ]

import sets
from datetime import datetime, timedelta

# Zope interfaces
from zope.interface import implements, directlyProvides, directlyProvidedBy
from zope.component import ComponentLookupError, getUtility

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, SQLObjectNotFound
from sqlobject.sqlbuilder import AND
from canonical.database.sqlbase import SQLBase, quote, cursor, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database import postgresql

# canonical imports
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor

from canonical.launchpad.interfaces import \
    IPerson, ITeam, IPersonSet, ITeamMembership, ITeamParticipation, \
    ITeamMembershipSet, IEmailAddress, IWikiName, IIrcID, IArchUserID, \
    IJabberID, IIrcIDSet, IArchUserIDSet, ISSHKeySet, IJabberIDSet, \
    IWikiNameSet, IGPGKeySet, ISSHKey, IGPGKey, IKarma, IKarmaPointsManager, \
    IMaintainershipSet, IEmailAddressSet, ISourcePackageReleaseSet

from canonical.launchpad.database.translation_effort import TranslationEffort
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.codeofconduct import SignedCodeOfConduct
from canonical.launchpad.database.logintoken import LoginToken

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.searchbuilder import NULL
from canonical.launchpad.helpers import shortlist

from canonical.lp.dbschema import \
    EnumCol, SSHKeyType, KarmaType, EmailAddressStatus, \
    TeamSubscriptionPolicy, TeamMembershipStatus, GPGKeyAlgorithms

from canonical.foaf import nickname


class Person(SQLBase):
    """A Person."""

    implements(IPerson)

    _defaultOrder = 'displayname'

    name = StringCol(dbName='name', alternateID=True)
    password = StringCol(dbName='password', default=None)
    givenname = StringCol(dbName='givenname', default=None)
    familyname = StringCol(dbName='familyname', default=None)
    displayname = StringCol(dbName='displayname', default=None)
    teamdescription = StringCol(dbName='teamdescription', default=None)

    teamowner = ForeignKey(dbName='teamowner', foreignKey='Person',
                           default=None)

    sshkeys = MultipleJoin('SSHKey', joinColumn='person')

    karma = IntCol(dbName='karma', default=0)
    karmatimestamp = DateTimeCol(dbName='karmatimestamp', default=UTC_NOW)

    subscriptionpolicy = EnumCol(
        dbName='subscriptionpolicy',
        schema=TeamSubscriptionPolicy,
        default=TeamSubscriptionPolicy.MODERATED)
    defaultrenewalperiod = IntCol(dbName='defaultrenewalperiod', default=None)
    defaultmembershipperiod = IntCol(dbName='defaultmembershipperiod',
                                     default=None)

    merged = ForeignKey(dbName='merged', foreignKey='Person', default=None)

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

    def translatedTemplates(self):
        """
        SELECT * FROM POTemplate WHERE
            id IN (SELECT potemplate FROM pomsgset WHERE
                id IN (SELECT pomsgset FROM POTranslationSighting WHERE
                    origin = 2
                ORDER BY datefirstseen DESC))
        """
        # XXX: This needs a proper descriptive English docstring.
        #      Also, what is it doing here?  It doesn't use 'self' at all.
        #      -- SteveAlexander, 2005-04-23
        return POTemplate.select('''
            id IN (
              SELECT potemplate FROM potmsgset WHERE id IN (
                SELECT potmsgset FROM pomsgset WHERE id IN (
                  SELECT pomsgset FROM POTranslationSighting WHERE origin = 2
                    ORDER BY datefirstseen DESC)))
            ''')

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
        tp = TeamParticipation.selectBy(teamID=team.id, personID=self.id)
        if tp.count() > 0:
            return True
        else:
            return False

    def hasMembershipEntryFor(self, team):
        results = TeamMembership.selectBy(personID=self.id, teamID=team.id)
        return bool(results.count())

    def leave(self, team):
        # XXX: Should these really be asserts?
        #      -- SteveAlexander, 2005-04-23
        assert not ITeam.providedBy(self)

        tm = TeamMembership.selectOneBy(personID=self.id, teamID=team.id)
        assert tm is not None
        assert tm.status in [TeamMembershipStatus.ADMIN,
                             TeamMembershipStatus.APPROVED]

        team.setMembershipStatus(self, TeamMembershipStatus.DEACTIVATED,
                                 tm.dateexpires)
        # XXX: Why is this returing anything?  What's the contract?
        #      Where's the docstring?
        #      -- SteveAlexander, 2005-04-23
        return True

    def join(self, team):
        # XXX: Don't use an assert.
        #      SteveAlexander, 2005-04-23
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

    def getSuperTeams(self):
        query = ('Person.id = TeamParticipation.team AND '
                 'TeamParticipation.person = %d' % self.id)
        results = Person.select(query, clauseTables=['TeamParticipation'])
        return shortlist(results)

    def getSubTeams(self):
        query = ('Person.id = TeamParticipation.person AND '
                 'TeamParticipation.team = %d AND '
                 'Person.teamowner IS NOT NULL' % self.id)
        results = Person.select(query, clauseTables=['TeamParticipation'])
        return shortlist(results)

    def addMember(self, person, status=TeamMembershipStatus.APPROVED,
                  reviewer=None, comment=None):
        assert self.teamowner is not None
        assert not person.hasMembershipEntryFor(self)
        assert status in [TeamMembershipStatus.APPROVED,
                          TeamMembershipStatus.PROPOSED]

        expires = self.defaultexpirationdate
        TeamMembership(personID=person.id, teamID=self.id, status=status,
                       dateexpires=expires, reviewer=reviewer, 
                       reviewercomment=comment)

        if status == TeamMembershipStatus.APPROVED:
            _fillTeamParticipation(person, self)

    def setMembershipStatus(self, person, status, expires, reviewer=None,
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

        now = datetime.utcnow()
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
        return shortlist(Person.select(query, clauseTables=['TeamMembership']))

    def _getEmailsByStatus(self, status):
        query = AND(EmailAddress.q.personID==self.id,
                    EmailAddress.q.status==status)
        return shortlist(EmailAddress.select(query))

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
        return self.approvedmembers + self.administrators
    activemembers = property(activemembers)

    def inactivemembers(self):
        return self.expiredmembers + self.deactivatedmembers
    inactivemembers = property(inactivemembers)

    def memberships(self):
        return shortlist(TeamMembership.selectBy(personID=self.id))
    memberships = property(memberships)

    def defaultexpirationdate(self):
        days = self.defaultmembershipperiod
        if days:
            return datetime.utcnow() + timedelta(days)
        else:
            return None
    defaultexpirationdate = property(defaultexpirationdate)

    def defaultrenewedexpirationdate(self):
        days = self.defaultrenewalperiod
        if days:
            return datetime.utcnow() + timedelta(days)
        else:
            return None
    defaultrenewedexpirationdate = property(defaultrenewedexpirationdate)

    def _setPreferredemail(self, email):
        # XXX: Should this be an assert?
        #      -- SteveAlexander, 2005-04-23
        assert email.person == self
        preferredemail = self.preferredemail
        if preferredemail is not None:
            preferredemail.status = EmailAddressStatus.VALIDATED
        email.status = EmailAddressStatus.PREFERRED

    def _getPreferredemail(self):
        emails = shortlist(
            self._getEmailsByStatus(EmailAddressStatus.PREFERRED))
        # There can be only one preferred email for a given person at a
        # given time, and this constraint must be ensured in the DB, but
        # it's not a problem if we ensure this constraint here as well.
        length = len(emails)
        assert length <= 1
        if length:
            return emails[0]
        else:
            return None
    preferredemail = property(_getPreferredemail, _setPreferredemail)

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

    def bugs(self):
        return list(Bug.selectBy(ownerID=self.id))
    bugs= property(bugs)

    def translations(self):
        return list(TranslationEffort.selectBy(ownerID=self.id))
    translations = property(translations)

    def activities(self):
        return list(Karma.selectBy(personID=self.id))
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
        return shortlist(maintainershipsutil.getByPersonID(self.id))
    maintainerships = property(maintainerships)

    def packages(self):
        sprutil = getUtility(ISourcePackageReleaseSet)
        return shortlist(sprutil.getByCreatorID(self.id))
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
            raise KeyError, personid
        else:
            return person

    def newTeam(self, **kw):
        """See IPersonSet."""
        ownerID = kw.get('teamownerID')
        assert ownerID
        owner = Person.get(ownerID)
        team = Person(**kw)
        _fillTeamParticipation(owner, team)
        return team

    def newPerson(self, **kw):
        """See IPersonSet."""
        assert not kw.get('teamownerID')
        if kw.has_key('password'):
            # encryptor = getUtility(IPasswordEncryptor)
            # XXX: Carlos Perello Marin 22/12/2004 We cannot use getUtility
            # from initZopeless scripts and Rosetta's import_daemon.py
            # calls indirectly to this function :-(
            encryptor = SSHADigestEncryptor()
            kw['password'] = encryptor.encrypt(kw['password'])

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
        return list(self._getAllPersons(orderBy=orderBy))

    def _getAllPersons(self, orderBy=None):
        query = AND(Person.q.teamownerID==None, Person.q.mergedID==None)
        return Person.select(query, orderBy=orderBy)

    def teamsCount(self):
        return self._getAllTeams().count()

    def getAllTeams(self, orderBy=None):
        return list(self._getAllTeams(orderBy=orderBy))

    def _getAllTeams(self, orderBy=None):
        return Person.select(Person.q.teamownerID!=None, orderBy=orderBy)

    def findByName(self, name, orderBy=None):
        query = "fti @@ ftq(%s) AND merged is NULL" % quote(name)
        return list(Person.select(query, orderBy=orderBy))

    def findPersonByName(self, name, orderBy=None):
        query = "fti @@ ftq(%s) AND teamowner is NULL AND merged is NULL"
        return list(Person.select(query % quote(name), orderBy=orderBy))

    def findTeamByName(self, name, orderBy=None):
        query = "fti @@ ftq(%s) AND teamowner is not NULL" % quote(name)
        return list(Person.select(query, orderBy=orderBy))

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

    def getContributorsForPOFile(self, pofile):
        """See IPersonSet."""
        return Person.select('''
            POTranslationSighting.person = Person.id AND
            POTranslationSighting.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = %d''' % pofile.id,
            clauseTables=('POTranslationSighting', 'POMsgSet'),
            distinct=True)

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
        """
        # Sanity checks
        if ITeam.providedBy(from_person):
            raise TypeError, 'Got a team as from_person'
        if ITeam.providedBy(to_person):
            raise TypeError, 'Got a team as to_person'
        if not IPerson.providedBy(from_person):
            raise TypeError, 'from_person is not a person'
        if not IPerson.providedBy(to_person):
            raise TypeError, 'to_person is not a person'

        if len(getUtility(IEmailAddressSet).getByPerson(from_person.id)) > 0:
            raise ValueError, 'from_person still has email addresses'

        # Get a database cursor.
        cur = cursor()

        references = list(postgresql.queryReferences(cur, 'person', 'id'))

        # These table.columns will be skipped by the 'catch all'
        # update performed later
        skip = [
            ('teammembership', 'person'),
            ('teammembership', 'team'),
            ('teamparticipation', 'person'),
            ('teamparticipation', 'team'),
            ('personlanguage', 'person'),
            ('person', 'merged'),
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

        # Update only the POTranslationSightngs that will not conflict
        # XXX: Add sampledata and test to confirm this case
        # -- StuartBishop 20050331
        cur.execute('''
            UPDATE POTranslationSighting
            SET person=%(to_id)d
            WHERE person=%(from_id)d AND id NOT IN (
                SELECT a.id
                FROM POTranslationSighting AS a, POTranslationSighting AS b
                WHERE a.person = %(from_id)d AND b.person = %(to_id)d
                    AND a.pomsgset = b.pomsgset
                    AND a.potranslation = b.potranslation
                    AND a.license = b.license
                AND a.pluralform = b.pluralform
                )
            ''' % vars())
        skip.append(('potranslationsighting', 'person'))
    
        # Sanity check. If we have a reference that participates in a
        # UNIQUE index, it must have already been handled by this point.
        # We can tell this by looking at the skip list.
        for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
            uniques = postgresql.queryUniques(cur, src_tab, src_col)
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

def createPerson(email, displayname=None, givenname=None, familyname=None,
                 password=None):
    """Create a new Person and an EmailAddress for that Person.

    Generate a unique nickname from the email address provided, create a
    Person with that nickname and then create the EmailAddress for the new
    Person. This function is provided mainly for nicole, debsync and POFile raw
    importer, which generally have only the email and displayname to create a
    new Person.
    """
    kw = {}
    try:
        kw['name'] = nickname.generate_nick(email)
    except NicknameGenerationError:
        return None

    kw['displayname'] = displayname
    kw['givenname'] = givenname
    kw['familyname'] = familyname
    kw['password'] = password
    person = PersonSet().newPerson(**kw)

    new = EmailAddressStatus.NEW
    EmailAddress(person=person.id, email=email.lower(), status=new)

    return person


def personFromPrincipal(principal):
    """Adapt canonical.launchpad.webapp.interfaces.ILaunchpadPrincipal
   to IPerson.
    """
    # XXX: Make this use getUtility(IPersonSet), and put it in components.
    #      -- SteveAlexander, 2005-04-23
    if ILaunchpadPrincipal.providedBy(principal):
        return Person.get(principal.id)
    else:
        # This is not actually necessary when this is used as an adapter
        # from ILaunchpadPrincipal, as we know we always have an
        # ILaunchpadPrincipal.
        #
        # When Zope3 interfaces allow returning None for "cannot adapt"
        # we can return None here.
        ##return None
        raise ComponentLookupError


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
            raise KeyError, emailid
        else:
            return email

    def getByPerson(self, personid):
        return shortlist(EmailAddress.selectBy(personID=personid))

    def getByEmail(self, email, default=None):
        try:
            return EmailAddress.byEmail(email)
        except SQLObjectNotFound:
            return default

    def new(self, email, status, personID):
        email = email.strip().lower()
        assert status in EmailAddressStatus.items
        return EmailAddress(email=email, status=status, person=personID)


class GPGKey(SQLBase):
    implements(IGPGKey)

    _table = 'GPGKey'

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    keyid = StringCol(dbName='keyid', notNull=True)
    pubkey = StringCol(dbName='pubkey', notNull=True)
    fingerprint = StringCol(dbName='fingerprint', notNull=True)

    keysize = IntCol(dbName='keysize', notNull=True)

    algorithm = EnumCol(dbName='algorithm', notNull=True,
                        schema=GPGKeyAlgorithms)

    revoked = BoolCol(dbName='revoked', notNull=True)

    def algorithmname(self):
        return self.algorithm.title
    algorithmname = property(algorithmname)


class GPGKeySet:
    implements(IGPGKeySet)

    def new(self, ownerID, keyid, pubkey, fingerprint, keysize,
            algorithm, revoked):
        return GPGKey(owner=ownerID, keyid=keyid, pubkey=pubkey,
                      fingerprint=fingerprint, keysize=keysize,
                      algorithm=algorithm, revoked=revoked)

    def get(self, id, default=None):
        try:
            return GPGKey.get(id)
        except SQLObjectNotFound:
            return default


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
    datejoined = DateTimeCol(dbName='datejoined', default=datetime.utcnow(),
                             notNull=True)
    dateexpires = DateTimeCol(dbName='dateexpires', default=None)
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
        return list(TeamMembership.select(query, clauseTables=['Person'],
                                          orderBy=orderBy))

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
    return list(Person.select(query, clauseTables=['TeamParticipation'],
                              orderBy=orderBy))


def _cleanTeamParticipation(person, team):
    """Remove relevant entries in TeamParticipation for given person and team.

    Remove all tuples "person, team" from TeamParticipation for the given
    person and team (together with all its superteams), unless this person is
    an indirect member of the given team. More information on how to use the 
    TeamParticipation table can be found in the TeamParticipationUsage spec.
    """
    members = [person]
    if person.teamowner is not None:
        # The given person is, in fact, a team, and in this case we must 
        # remove all of its members from the given team and from its 
        # superteams.
        members.extend(_getAllMembers(person))

    for member in members:
        for subteam in team.getSubTeams():
            # This person is an indirect member of this team. We cannot remove
            # its TeamParticipation entry.
            if member.inTeam(subteam):
                break
        else:
            for t in team.getSuperTeams() + [team]:
                result = TeamParticipation.selectOneBy(
                    personID=member.id, teamID=t.id)
                if result is not None:
                    result.destroySelf()

def _fillTeamParticipation(person, team):
    """Add relevant entries in TeamParticipation for given person and team.

    Add a tuple "person, team" in TeamParticipation for the given team and all
    of its superteams. More information on how to use the TeamParticipation 
    table can be found in the TeamParticipationUsage spec.
    """
    members = [person]
    if person.teamowner is not None:
        # The given person is, in fact, a team, and in this case we must 
        # add all of its members to the given team and to its superteams.
        members.extend(_getAllMembers(person))

    for member in members:
        for t in team.getSuperTeams() + [team]:
            if not member.inTeam(t):
                TeamParticipation(personID=member.id, teamID=t.id)


class Karma(SQLBase):
    implements(IKarma)

    _table = 'Karma'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    points = IntCol(dbName='points', notNull=True, default=0)
    karmatype = EnumCol(dbName='karmatype', notNull=True, schema=KarmaType)
    datecreated = DateTimeCol(dbName='datecreated', notNull=True,
                              default='NOW')

    def karmatypename(self):
        return self.karmatype.title
    karmatypename = property(karmatypename)

