# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Zope interfaces
from zope.interface import implements
from zope.component import ComponentLookupError, getUtility

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW

# canonical imports
from canonical.launchpad.interfaces import IPerson, IPersonSet, IEmailAddress
from canonical.launchpad.interfaces import IObjectAuthorization
from canonical.launchpad.interfaces import IPasswordEncryptor
from canonical.launchpad.interfaces import ITeamParticipationSet
from canonical.launchpad.interfaces import ISourcePackageSet

from canonical.launchpad.database.translation_effort import TranslationEffort
from canonical.launchpad.database.soyuz import DistributionRole
from canonical.launchpad.database.soyuz import DistroReleaseRole
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.pofile import POTemplate

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal
from canonical.lp.dbschema import KarmaField
from canonical.lp import dbschema
from canonical.foaf import nickname

# python imports
from datetime import datetime


class Person(SQLBase):
    """A Person."""

    implements(IPerson, IObjectAuthorization)

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

    # RelatedJoin gives us also an addLanguage and removeLanguage for free
    languages = RelatedJoin('Language', joinColumn='person', 
                            otherColumn='language', 
                            intermediateTable='PersonLanguage')

    def checkPermission(self, principal, permission):
        if permission == "launchpad.Edit":
            teamowner = getattr(self.teamowner, 'id', None)
            if principal.id == teamowner:
                # I'm the team owner and want to change the team
                # information.
                return True
            return self.id == principal.id

    def browsername(self):
        """Returns a name suitable for display on a web page.

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

    # XXX: not implemented
    def maintainedProjects(self):
        '''SELECT Project.* FROM Project
            WHERE Project.owner = self.id
            '''

    # XXX: not implemented
    def translatedProjects(self):
        '''SELECT Project.* FROM Project, Product, POTemplate, POFile
            WHERE
                POFile.owner = self.id AND
                POFile.template = POTemplate.id AND
                POTemplate.product = Product.id AND
                Product.project = Project.id
            ORDER BY ???
        '''
        raise NotImplementedError

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

    def assignKarma(self, karmafield, points=None):
        if karmafield not in KarmaField.items:
            raise TypeError('"%s" is not a valid KarmaField value')
        if points is None:
            try:
                points = KARMA_POINTS[karmafield]
            except KeyError:
                # What about defining a default number of points?
                points = 0
                # Print a warning here, cause someone forgot to add the
                # karmafield to KARMA_POINTS.
        Karma(person=self, karmafield=karmafield.value, points=points)
        # XXX: I think we should recalculate the karma here.
        self.karma += points

    def inTeam(self, team_name):
        team = Person.byName(team_name)
        if not team.teamowner:
            raise ValueError, '%s not a team!' % team_name

        tp = TeamParticipation.selectBy(teamID=team.id, personID=self.id)
        if len(tp) > 0:
            return True
        else:
            return False

    #
    # Properties
    #

    def _roleset(self):
        return [item.title for item in dbschema.MembershipRole.items]

    roleset = property(_roleset)

    def _statusset(self):
        return [item.title for item in dbschema.MembershipStatus.items]

    statusset = property(_statusset)

    def _members(self): 
        members = Membership.selectBy(teamID=self.id)
        if members.count() == 0:
            members = None                
        return members

    members = property(_members)

    def _teams(self):
        # FIXME: (my_team) Daniel Debonzi 2004-10-13
        # My Teams should be:
        # -> the Teams owned by me
        # OR
        # -> the Teams which I'm member (as It is)
        teams = Membership.selectBy(personID=self.id)
        if teams.count() == 0:
            teams = None                
        return teams

    teams = property(_teams)

    def _subteams(self):
        teampart = getUtility(ITeamParticipationSet)
        subteams = teampart.getSubTeams(self.id)
        if subteams.count() == 0:
            subteams = None                
        return subteams

    subteams = property(_subteams)

    def _distroroles(self):
        distroroles = DistributionRole.selectBy(personID=self.id)
        if distroroles.count() == 0:
            distroroles = None
        return distroroles

    distroroles = property(_distroroles)

    def _distroreleaseroles(self):
        distroreleaseroles = DistroReleaseRole.selectBy(personID=self.id)
        if distroreleaseroles.count() == 0:
            distroreleaseroles = None
        return distroreleaseroles

    distroreleaseroles = property(_distroreleaseroles)

    def _emails(self):
        return EmailAddress.selectBy(personID=self.id)

    emails = property(_emails)

    def _bugs(self):
        return Bug.selectBy(ownerID=self.id)

    bugs= property(_bugs)

    def _translations(self):
        return TranslationEffort.selectBy(ownerID=self.id)

    translations = property(_translations)

    def _activities(self):
        return Karma.selectBy(personID=self.id)

    activities = property(_activities)

    def _wiki(self):
        wiki = WikiName.selectBy(personID=self.id)
        count = wiki.count()
        if count:
            assert count == 1
            return wiki[0]

    wiki = property(_wiki)

    def _jabber(self):
        jabber = JabberID.selectBy(personID=self.id)
        if jabber.count() == 0:
            return None
        return jabber[0]

    jabber = property(_jabber)

    def _archuser(self):
        archuser = ArchUserID.selectBy(personID=self.id)
        if archuser.count() == 0:
            return None
        return archuser[0]

    archuser = property(_archuser)

    def _irc(self):
        irc = IrcID.selectBy(personID=self.id)
        if irc.count() == 0:
            return None
        return irc[0]

    irc = property(_irc)

    def _gpg(self):
        gpg = GPGKey.selectBy(personID=self.id)
        if gpg.count() == 0:
            return None
        return gpg[0]

    gpg = property(_gpg)

    def _getSourcesByPerson(self):
        sputil = getUtility(ISourcePackageSet)
        return sputil.getByPersonID(self.id)

    packages = property(_getSourcesByPerson)


class PersonSet(object):
    """The set of persons."""
    implements(IPersonSet)

    def __iter__(self):
        return self.getall()

    def __getitem__(self, personid):
        """See IPersonSet."""
        person = self.get(personid)
        if person is None:
            raise KeyError, personid
        else:
            return person

    def getByName(self, name):
        results = Person.selectBy(name=name)
        assert results.count() == 1
        return results[0]

    def get(self, personid, default=None):
        """See IPersonSet."""
        try:
            return Person.get(personid)
        except SQLObjectNotFound:
            return default

    def getAll(self):
        return Person.select(orderBy='displayname')

    def getByEmail(self, email, default=None):
        """See IPersonSet."""
        results = EmailAddress.selectBy(email=email)
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
        return Person.select('''
            POTranslationSighting.active = True AND
            POTranslationSighting.person = Person.id AND
            POTranslationSighting.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = %d''' % pofile.id,
            clauseTables=('POTranslationSighting', 'POMsgSet',),
            distinct=True, orderBy='displayname')

    # XXX: Carlos Perello Marin 20/12/2004 We need this method from
    # pofile.py, I think we should remove the function and use it as this
    # method always.
    def createPerson(self, displayname, givenname, familyname, password, email):
        """Creates a new person"""
        return createPerson(displayname, givenname, familyname, password, email)


def createPerson(displayname, givenname, familyname, password, email):
    """Creates a new person"""

    nick = nickname.generate_nick(email)
    now = datetime.utcnow()

    if Person.selectBy(name=nick).count() > 0:
        return

    # XXX: Carlos Perello Marin 22/12/2004 We cannot use getUtility from
    # initZopeless scripts and Rosetta's import_daemon.py calls indirectly to
    # this function :-(
    from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
    password = SSHADigestEncryptor().encrypt(password)

    # password = getUtility(IPasswordEncryptor).encrypt(password)

    person = Person(displayname=displayname,
                    givenname=givenname,
                    familyname=familyname,
                    password=password,
                    teamownerID=None,
                    teamdescription=None,
                    karma=0,
                    karmatimestamp=now,
                    name=nick)

    EmailAddress(person=person.id,
                 email=email,
                 status=int(dbschema.EmailAddressStatus.NEW))

    return person


def createTeam(displayname, teamowner, teamdescription, email):
    """Creates a new team"""

    nick = nickname.generate_nick(email)
    now = datetime.utcnow()

    if Person.selectBy(name=nick).count() > 0:
        return
    
    role = dbschema.MembershipRole.ADMIN.value
    status = dbschema.MembershipStatus.CURRENT.value

    team = Person(displayname=displayname,
                  givenname=None,
                  familyname=None,
                  teamownerID=teamowner,
                  teamdescription=teamdescription,
                  karma=0,
                  karmatimestamp=now,
                  name=nick)

    EmailAddress(person=team.id,
                 email=email,
                 status=int(dbschema.EmailAddressStatus.NEW))

    Membership(personID=teamowner,
               team=team.id,
               role=role,
               status=status)

    TeamParticipation(personID=teamowner,
                      teamID=team.id)

    return team


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

    email = StringCol(dbName='email', notNull=True, unique=True)
    status = IntCol(dbName='status', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)

    def _statusname(self):
        for status in dbschema.EmailAddressStatus.items:
            if status.value == self.status:
                return status.title
        return 'Unknown (%d)' %self.status
    
    statusname = property(_statusname)


class GPGKey(SQLBase):
    _table = 'GPGKey'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)

    keyid = StringCol(dbName='keyid', notNull=True)
    pubkey = StringCol(dbName='pubkey', notNull=True)
    fingerprint = StringCol(dbName='fingerprint', notNull=True)

    keysize = IntCol(dbName='keysize', notNull=True)
    algorithm = IntCol(dbName='algorithm', notNull=True)

    revoked = BoolCol(dbName='revoked', notNull=True)

    def _algorithmname(self):
        for algorithm in dbschema.GPGKeyAlgorithms.items:
            if algorithm.value == self.algorithm:
                return algorithm.title
        return 'Unknown (%d)' %self.algorithm
    
    algorithmname = property(_algorithmname)


class SSHKey(SQLBase):
    _table = 'SSHKey'
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)
    keytype = StringCol(dbName='keytype', notNull=True)
    keytext = StringCol(dbName='keytext', notNull=True)
    comment = StringCol(dbName='comment', notNull=True)


class ArchUserID(SQLBase):
    _table = 'ArchUserID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    archuserid = StringCol(dbName='archuserid', notNull=True)
    

class WikiName(SQLBase):
    _table = 'WikiName'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    wiki = StringCol(dbName='wiki', notNull=True)
    wikiname = StringCol(dbName='wikiname', notNull=True)


class JabberID(SQLBase):
    _table = 'JabberID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    jabberid = StringCol(dbName='jabberid', notNull=True)


class IrcID(SQLBase):
    _table = 'IrcID'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    network = StringCol(dbName='network', notNull=True)
    nickname = StringCol(dbName='nickname', notNull=True)


class Membership(SQLBase):
    _table = 'Membership'

    team = ForeignKey(foreignKey='Person', dbName='team', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    role = IntCol(dbName='role', notNull=True)
    status = IntCol(dbName='status', notNull=True)

    def _rolename(self):
        for role in dbschema.MembershipRole.items:
            if role.value == self.role:
                return role.title
        return 'Unknown (%d)' %self.role
    
    rolename = property(_rolename)

    def _statusname(self):
        for status in dbschema.MembershipStatus.items:
            if status.value == self.status:
                return status.title
        return 'Unknown (%d)' %self.status
    
    statusname = property(_statusname)

class TeamParticipationSet(object):
    """ A Set for TeamParticipation objects. """

    implements(ITeamParticipationSet)

    def getSubTeams(self, teamID):
        clauseTables = ('person',)
        query = ("team = %d "
                 "AND Person.id = TeamParticipation.person "
                 "AND Person.teamowner IS NOT NULL" % teamID)

        return TeamParticipation.select(query, clauseTables=clauseTables)


class TeamParticipation(SQLBase):
    _table = 'TeamParticipation'

    team = ForeignKey(foreignKey='Person', dbName='team', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


class Karma(SQLBase):
    _table = 'Karma'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    points = IntCol(dbName='points', notNull=True, default=0)
    karmafield = IntCol(dbName='karmafield', notNull=True)
    datecreated = DateTimeCol(dbName='datecreated', notNull=True, default='NOW')

    def _karmafieldname(self):
        try:
            return KarmaField.items[self.karmafield].title
        except KeyError:
            return 'Unknown (%d)' % self.karmafield

    karmafieldname = property(_karmafieldname)


# XXX: These points are totally *CRAP*.
KARMA_POINTS = {KarmaField.BUG_REPORT: 10,
                KarmaField.BUG_FIX: 20,
                KarmaField.BUG_COMMENT: 5,
                KarmaField.WIKI_EDIT: 2,
                KarmaField.WIKI_CREATE: 3,
                KarmaField.PACKAGE_UPLOAD: 10}

