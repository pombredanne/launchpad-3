# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime, timedelta

# Zope interfaces
from zope.interface import implements
from zope.interface import directlyProvides, directlyProvidedBy
from zope.component import ComponentLookupError, getUtility

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, SQLObjectNotFound
from sqlobject.sqlbuilder import AND
from canonical.database.sqlbase import SQLBase, quote, cursor
from canonical.database.constants import UTC_NOW
from canonical.database import postgresql

# canonical imports
from canonical.launchpad.interfaces import IPerson, ITeam, IPersonSet
from canonical.launchpad.interfaces import ITeamMembership, ITeamParticipation
from canonical.launchpad.interfaces import ITeamMembershipSet
from canonical.launchpad.interfaces import IEmailAddress, IWikiName
from canonical.launchpad.interfaces import IIrcID, IArchUserID, IJabberID
from canonical.launchpad.interfaces import IIrcIDSet, IArchUserIDSet
from canonical.launchpad.interfaces import ISSHKeySet, IJabberIDSet
from canonical.launchpad.interfaces import IWikiNameSet, IGPGKeySet
from canonical.launchpad.interfaces import ISSHKey, IGPGKey, IKarma
from canonical.launchpad.interfaces import IKarmaPointsManager
from canonical.launchpad.interfaces import IPasswordEncryptor
from canonical.launchpad.interfaces import IMaintainershipSet, IEmailAddressSet
from canonical.launchpad.interfaces import ICodeOfConductConf
from canonical.launchpad.interfaces import ISourcePackageReleaseSet

from canonical.launchpad.database.translation_effort import TranslationEffort
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.pofile import POTemplate
from canonical.launchpad.database.codeofconduct import SignedCodeOfConduct
from canonical.launchpad.database.logintoken import LoginToken

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.searchbuilder import NULL

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import KarmaType
from canonical.lp.dbschema import EmailAddressStatus
from canonical.lp.dbschema import TeamSubscriptionPolicy
from canonical.lp.dbschema import TeamMembershipStatus
from canonical.lp.dbschema import GPGKeyAlgorithms
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

    merged = ForeignKey(dbName='merged', foreignKey='Person',
                           default=None)

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
        val = super(Person, cls).get(
            id, connection=connection, selectResults=selectResults)
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
        ...     # unit test browsername() in isolation.
        ...     browsername = Person.browsername.im_func
        ...
        >>> person = DummyPerson()

        Check with just the name.

        >>> person.browsername()
        'the_name'

        Check with givenname and name.  Just givenname is used.

        >>> person.givenname = 'the_givenname'
        >>> person.browsername()
        'the_givenname'

        Check with givenname, familyname and name.  Both givenname and
        familyname are used.

        >>> person.familyname = 'the_familyname'
        >>> person.browsername()
        'THE_FAMILYNAME the_givenname'

        Check with givenname, familyname, name and displayname.
        Only displayname is used.

        >>> person.displayname = 'the_displayname'
        >>> person.browsername()
        'the_displayname'

        Remove familyname to check with givenname, name and displayname.
        Only displayname is used.

        >>> person.familyname = None
        >>> person.browsername()
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

    def translatedTemplates(self):
        '''
        SELECT * FROM POTemplate WHERE
            id IN (SELECT potemplate FROM pomsgset WHERE
                id IN (SELECT pomsgset FROM POTranslationSighting WHERE
                    origin = 2
                ORDER BY datefirstseen DESC))
        '''
        return POTemplate.select('''
            id IN (
                SELECT potemplate FROM potmsgset WHERE id IN (
                    SELECT potmsgset FROM pomsgset WHERE id IN (
                        SELECT pomsgset FROM POTranslationSighting WHERE origin = 2
                            ORDER BY datefirstseen DESC)))
            ''')

    def assignKarma(self, karmatype, points=None):
        if karmatype.schema is not KarmaType:
            raise TypeError('"%s" is not a valid KarmaType value')
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
        assert self.teamowner is None

        results = TeamMembership.selectBy(personID=self.id, teamID=team.id)
        assert results.count() == 1

        tm = results[0]
        assert tm.status in (TeamMembershipStatus.ADMIN,
                             TeamMembershipStatus.APPROVED)

        team.setMembershipStatus(self, TeamMembershipStatus.DEACTIVATED)
        return True

    def join(self, team):
        assert self.teamowner is None

        if team.subscriptionpolicy == TeamSubscriptionPolicy.RESTRICTED:
            return False
        elif team.subscriptionpolicy == TeamSubscriptionPolicy.MODERATED:
            status = TeamMembershipStatus.PROPOSED
        elif team.subscriptionpolicy == TeamSubscriptionPolicy.OPEN:
            status = TeamMembershipStatus.APPROVED

        results = TeamMembership.selectBy(personID=self.id, teamID=team.id)
        if results.count() == 1:
            tm = results[0]
            if tm.status == TeamMembershipStatus.DECLINED:
                # The user is a DECLINED member, we just have to change the
                # status according to the team's subscriptionpolicy.
                team.setMembershipStatus(self, status)
            else:
                # The user is a member and the status is not DECLINED, there's
                # nothing we can do for it.
                return False
        else:
            team.addMember(self, status)

        return True

    #
    # ITeam methods
    #

    def getSuperTeams(self):
        query = ('Person.id = TeamParticipation.team AND '
                 'TeamParticipation.person = %d' % self.id)
        return list(Person.select(query, clauseTables=['TeamParticipation']))

    def getSubTeams(self):
        query = ('Person.id = TeamParticipation.person AND '
                 'TeamParticipation.team = %d AND '
                 'Person.teamowner IS NOT NULL' % self.id)
        return list(Person.select(query, clauseTables=['TeamParticipation']))

    def addMember(self, person, status=TeamMembershipStatus.APPROVED,
                  expires=None, reviewer=None, comment=None):
        assert self.teamowner is not None
        assert not person.hasMembershipEntryFor(self)
        assert status in [TeamMembershipStatus.APPROVED,
                          TeamMembershipStatus.PROPOSED]

        now = datetime.utcnow()
        if expires is None and self.defaultmembershipperiod:
            expires = now + timedelta(self.defaultmembershipperiod)
        elif expires is not None:
            assert expires > now

        TeamMembership(personID=person.id, teamID=self.id, status=status,
                       dateexpires=expires, reviewer=reviewer, 
                       reviewercomment=comment)

        if status == TeamMembershipStatus.APPROVED:
            _fillTeamParticipation(person, self)

    def setMembershipStatus(self, person, status, expires=None, reviewer=None,
                            comment=None):
        results = TeamMembership.selectBy(personID=person.id, teamID=self.id)
        assert results.count() == 1
        tm = results[0]

        if reviewer is not None:
            # Make sure the reviewer is either the team owner or one of the
            # administrators.
            assert reviewer in self.administrators + [self.teamowner]

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
        if expires is None and self.defaultmembershipperiod:
            expires = now + timedelta(self.defaultmembershipperiod)
        elif expires is not None and expires <= now:
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

    #
    # Private methods
    #

    def _getMembersByStatus(self, status):
        query = ("TeamMembership.team = %d AND TeamMembership.status = %d "
                 "AND TeamMembership.person = Person.id") % (
                 self.id, status.value)
        return list(Person.select(query, clauseTables=['TeamMembership']))

    def _getEmailsByStatus(self, status):
        query = AND(EmailAddress.q.personID==self.id,
                    EmailAddress.q.status==status)
        return list(EmailAddress.select(query))

    #
    # Properties
    #

    def title(self):
        return self.browsername()
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
        return list(TeamMembership.selectBy(personID=self.id))
    memberships = property(memberships)

    def _setPreferredemail(self, email):
        assert email.person == self
        preferredemail = self.preferredemail
        if preferredemail is not None:
            preferredemail.status = EmailAddressStatus.VALIDATED
        email.status = EmailAddressStatus.PREFERRED

    def _getPreferredemail(self):
        status = EmailAddressStatus.PREFERRED
        emails = list(self._getEmailsByStatus(status))
        # There can be only one preferred email for a given person at a
        # given time, and this constraint must be ensured in the DB, but
        # it's not a problem if we ensure this constraint here as well.
        length = len(emails)
        assert length <= 1
        if length:
            return emails[0]
        return None
    preferredemail = property(_getPreferredemail, _setPreferredemail)

    def validatedemails(self):
        status = EmailAddressStatus.VALIDATED
        return self._getEmailsByStatus(status)
    validatedemails = property(validatedemails)

    def unvalidatedemails(self):
        tokens = LoginToken.select("requester=%d AND email IS NOT NULL"
                % self.id)
        return [token.email for token in tokens]
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
        wiki = WikiName.selectBy(personID=self.id)
        count = wiki.count()
        if count:
            assert count == 1
            return wiki[0]
    wiki = property(wiki)

    def jabber(self):
        # XXX: salgado, 2005-01-14: This method will probably be replaced
        # by a MultipleJoin since we have a good UI to add multiple
        # JabberIDs. 
        jabber = JabberID.selectBy(personID=self.id)
        if jabber.count() == 0:
            return None
        return jabber[0]
    jabber = property(jabber)

    def archuser(self):
        # XXX: salgado, 2005-01-14: This method will probably be replaced
        # by a MultipleJoin since we have a good UI to add multiple
        # ArchUserIDs. 
        archuser = ArchUserID.selectBy(personID=self.id)
        if archuser.count() == 0:
            return None
        return archuser[0]
    archuser = property(archuser)

    def irc(self):
        # XXX: salgado, 2005-01-14: This method will probably be replaced
        # by a MultipleJoin since we have a good UI to add multiple
        # IrcIDs. 
        irc = IrcID.selectBy(personID=self.id)
        if irc.count() == 0:
            return None
        return irc[0]
    irc = property(irc)

    def maintainerships(self):
        maintainershipsutil = getUtility(IMaintainershipSet)
        return list(maintainershipsutil.getByPersonID(self.id))
    maintainerships = property(maintainerships)

    def packages(self):
        sprutil = getUtility(ISourcePackageReleaseSet)
        return list(sprutil.getByCreatorID(self.id))
    packages = property(packages)

    def isUbuntite(self):
        putil = getUtility(IPersonSet)
        return putil.isUbuntite(self.id)
    ubuntite = property(isUbuntite)
    

class PersonSet(object):
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
            from canonical.launchpad.webapp.authentication \
                import SSHADigestEncryptor
            encryptor = SSHADigestEncryptor()
            kw['password'] = encryptor.encrypt(kw['password'])

        return Person(**kw)

    def getByName(self, name, default=None):
        """See IPersonSet."""
        results = Person.selectBy(name=name)
        if results.count() == 1:
            return results[0]
        else:
            return default

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

    def getAllPersons(self):
        return list(Person.select(Person.q.teamownerID==None))

    def getAllTeams(self):
        return list(Person.select(Person.q.teamownerID!=None))

    def findByName(self, name):
        query = "fti @@ ftq(%s)" % quote(name)
        return list(Person.select(query))

    def findPersonByName(self, name):
        query = "fti @@ ftq(%s) AND teamowner is NULL" % quote(name)
        return list(Person.select(query))

    def findTeamByName(self, name):
        query = "fti @@ ftq(%s) AND teamowner is not NULL" % quote(name)
        return list(Person.select(query))

    def get(self, personid, default=None):
        """See IPersonSet."""
        try:
            return Person.get(personid)
        except SQLObjectNotFound:
            return default

    def getAll(self):
        """See IPersonSet."""
        return Person.select()

    def getByEmail(self, email, default=None):
        """See IPersonSet."""
        results = EmailAddress.select("""lower(email) = %s
                        """ % quote(email.lower()))
        resultscount = results.count()
        if resultscount == 0:
            return default
        elif resultscount == 1:
            return results[0].person
        else:
            raise AssertionError(
                'There were %s email addresses matching %s'
                % (resultscount, email))

    def getContributorsForPOFile(self, pofile):
        """See IPersonSet."""
        return Person.select('''
            POTranslationSighting.person = Person.id AND
            POTranslationSighting.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = %d''' % pofile.id,
            clauseTables=('POTranslationSighting', 'POMsgSet'),
            distinct=True)

    def isUbuntite(self, person):
        """See IPersonSet."""
        # XXX: cprov 20050226
        # Verify the the SignedCoC version too
        # we can't do it before add the field version on
        # SignedCoC table. Then simple compare the already
        # checked field with what we grab from CoCConf utility.
        # Simply add 'SignedCodeOfConduct.version = %s' % conf.current
        # in query when the field was landed.
        conf = getUtility(ICodeOfConductConf)

        query = ('SignedCodeOfConduct.active = True AND '
                 'SignedCodeOfConduct.owner = %s' % person)
                 
        sign = SignedCodeOfConduct.select(query)

        if sign.count():
            return True

    def getUbuntites(self):
        """See IPersonSet."""
        
        clauseTables = ['SignedCodeOfConduct']

        # XXX: cprov 20050226
        # Verify the the SignedCoC version too
        # we can't do it before add the field version on
        # SignedCoC version.
        # Needs DISTINCT or check to prevent Sign CoC twice.
        query = ('Person.id = SignedCodeOfConduct.owner AND '
                 'SignedCodeOfConduct.active = True')

        return Person.select(query, clauseTables=clauseTables)
    
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

        # XXX: Looks like I'm supposed to use EmailAddressSet here -
        # Person.emails would be useful, but it only exists in the
        # IPerson interface. -- StuartBishop 20050321
        if len(list(EmailAddress.selectBy(personID=from_person.id))) > 0:
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
                        '%s.%s reference to %s.%s must be ON UPDATE CASCADE'%(
                            src_tab, src_col, ref_tab, ref_col
                            )
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
        cur.execute('''
            UPDATE GPGKey SET owner=%(to_id)d WHERE owner=%(from_id)d
            ''' % vars())
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
       to IPerson
    """
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

    def _statusname(self):
        return self.status.title
    
    statusname = property(_statusname)


class EmailAddressSet(object):
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
        return list(EmailAddress.selectBy(personID=personid))

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

    def _algorithmname(self):
        return self.algorithm.title
    
    algorithmname = property(_algorithmname)


class GPGKeySet(object):
    implements(IGPGKeySet)

    def new(self, ownerID, keyid, pubkey, fingerprint, keysize,
            algorithm, revoked):
        return GPGKey(owner=ownerID, keyid=keyid, pubkey=pubkey,
                      figerprint=fingerprint, keysize=keysize,
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
    keytype = StringCol(dbName='keytype', notNull=True)
    keytext = StringCol(dbName='keytext', notNull=True)
    comment = StringCol(dbName='comment', notNull=True)


class SSHKeySet(object):
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
    

class ArchUserIDSet(object):
    implements(IArchUserIDSet)

    def new(self, personID, archuserid):
        return ArchUserID(personID=personID, archuserid=archuserid)


class WikiName(SQLBase):
    implements(IWikiName)

    _table = 'WikiName'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    wiki = StringCol(dbName='wiki', notNull=True)
    wikiname = StringCol(dbName='wikiname', notNull=True)


class WikiNameSet(object):
    implements(IWikiNameSet)

    def new(self, personID, wiki, wikiname):
        return WikiName(personID=personID, wiki=wiki, wikiname=wikiname)


class JabberID(SQLBase):
    implements(IJabberID)

    _table = 'JabberID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    jabberid = StringCol(dbName='jabberid', notNull=True)


class JabberIDSet(object):
    implements(IJabberIDSet)

    def new(self, personID, jabberid):
        return JabberID(personID=personID, jabberid=jabberid)


class IrcID(SQLBase):
    implements(IIrcID)

    _table = 'IrcID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    network = StringCol(dbName='network', notNull=True)
    nickname = StringCol(dbName='nickname', notNull=True)


class IrcIDSet(object):
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

    def _statusname(self):
        return self.status.title
    statusname = property(_statusname)

    def isExpired(self):
        return self.status == TeamMembershipStatus.EXPIRED


class TeamMembershipSet(object):

    implements(ITeamMembershipSet)

    def getByPersonAndTeam(self, personID, teamID, default=None):
        results = TeamMembership.selectBy(personID=personID, teamID=teamID)
        if results.count() < 1:
            return default
        assert results.count() == 1
        return results[0]

    def getTeamMembersCount(self, teamID):
        return TeamMembership.selectBy(teamID=teamID).count()

    def getMemberships(self, teamID, status):
        assert isinstance(status, int)
        assert isinstance(teamID, int)
        query = ("TeamMembership.team = %d AND TeamMembership.status = %d "
                 "AND Person.id = TeamMembership.person") % (
                 teamID, status)
        return list(TeamMembership.select(query, clauseTables=['Person'],
                                          orderBy='displayname'))


class TeamParticipation(SQLBase):
    implements(ITeamParticipation)

    _table = 'TeamParticipation'

    team = ForeignKey(foreignKey='Person', dbName='team', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


def _getAllMembers(team):
    query = ('Person.id = TeamParticipation.person AND '
             'TeamParticipation.team = %d' % team.id)
    return list(Person.select(query, clauseTables=['TeamParticipation']))


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
                r = TeamParticipation.selectBy(personID=member.id, teamID=t.id)
                if r.count() > 0:
                    assert r.count() == 1
                    r[0].destroySelf()


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

