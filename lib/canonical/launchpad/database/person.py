# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Zope interfaces
from zope.interface import implements
from zope.component import ComponentLookupError, getUtility
from zope.app.security.interfaces import IUnauthenticatedPrincipal

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, SQLObjectNotFound
from sqlobject import SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote
from canonical.database.constants import UTC_NOW

# canonical imports
from canonical.launchpad.interfaces import IPerson, IPersonSet, IEmailAddress
from canonical.launchpad.interfaces import ILanguageSet
from canonical.launchpad.interfaces import IPasswordEncryptor
from canonical.launchpad.interfaces import ITeamParticipationSet
from canonical.launchpad.database.pofile import POTemplate
from canonical.lp.dbschema import KarmaField
from canonical.lp import dbschema
from canonical.foaf import nickname

# python imports
from datetime import datetime


class Person(SQLBase):
    """A Person."""

    implements(IPerson)

    _columns = [
        StringCol('name', alternateID=True),
        StringCol('displayname', default=None),
        StringCol('givenname', default=None),
        StringCol('familyname', default=None),
        StringCol('password', default=None),
        ForeignKey(name='teamowner', foreignKey='Person', dbName='teamowner',
            default=None),
        StringCol('teamdescription', default=None),
        IntCol('karma', default=0),
        DateTimeCol('karmatimestamp', default=UTC_NOW)
    ]

    # RelatedJoin gives us also an addLanguage and removeLanguage for free
    languages = RelatedJoin('Language', joinColumn='person',
        otherColumn='language', intermediateTable='PersonLanguage')

    # XXX Steve Alexander, 2004-11-15.
    #     The rosetta team need to clean this up.
    _emailsJoin = MultipleJoin('RosettaEmailAddress', joinColumn='person')

    def emails(self):
        return iter(self._emailsJoin)

    def browsername(self):
        """Returns a name suitable for display on a web page."""
        if self.displayname: return self.displayname
        if self.familyname:
            browsername.append(self.familyname.upper())
        if self.givenname:
            browsername.append(self.givenname)
        if not browsername:
            browsername = 'UNKNOWN USER #'+str(self.id)
        return ' '.join(browsername)

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
        # XXX: Dafydd Harries, 2004/10/13.
        # Import done here as putting it at the top seems to break it and
        # right now I'd rather have this working than spend time on working
        # out the Right solution.
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

class PersonSet(object):
    """The set of persons."""
    implements(IPersonSet)

    def __getitem__(self, personid):
        """See IPersonSet."""
        person = self.get(personid)
        if person is None:
            raise KeyError, personid
        else:
            return person

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


def PersonFactory(context, **kw):
    now = datetime.utcnow()
    person = Person(teamowner=1,
                    teamdescription='',
                    karma=0,
                    karmatimestamp=now,
                    **kw)
    return person

# XXX: Daniel Debonzi 2004-10-28
# Shold not it and PersonFactory be only
# one function?
def createPerson(displayname, givenname, familyname,
                 password, email):
    """Creates a new person"""

    nick = nickname.generate_nick(email)
    now = datetime.utcnow()

    if Person.selectBy(name=nick).count() > 0:
        return
    
    password = getUtility(IPasswordEncryptor).encrypt(password)
    
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

def createTeam(displayname, teamowner, teamdescription,
               password, email):
    """Creates a new team"""

    nick = nickname.generate_nick(email)
    now = datetime.utcnow()

    if Person.selectBy(name=nick).count() > 0:
        return
    
    # XXX: I think Teams don't need or want passwords
    password = getUtility(IPasswordEncryptor).encrypt(password)

    role = dbschema.MembershipRole.ADMIN.value
    status = dbschema.MembershipStatus.CURRENT.value

    team = Person(displayname=displayname,
                  givenname=None,
                  familyname=None,
                  password=password,
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
    if IUnauthenticatedPrincipal.providedBy(principal):
        # When Zope3 interfaces allow returning None for "cannot adapt"
        # we can return None here.
        ##return None
        raise ComponentLookupError
    return Person.get(principal.id)

def getPermission(user, context):
    """
    return True if the logged user has permission to add/edit the current
    shown context (it might be the own person, or the teamowner)
    """
    permission = False
    
    if user:
        pid = user.id

        ## user is own person
        if pid == context.person.id:
            permission = True

        ## person is team
        if context.person.teamowner:
            ## user is teamowner
            if pid == context.person.teamowner.id:
                permission = True
                
    return permission


class EmailAddress(SQLBase):
    implements(IEmailAddress)

    _table = 'EmailAddress'
    _columns = [
        StringCol('email', notNull=True, unique=True),
        IntCol('status', notNull=True),
        ForeignKey(
            name='person', dbName='person', foreignKey='Person',
            )
        ]

    def _statusname(self):
        for status in dbschema.EmailAddressStatus.items:
            if status.value == self.status:
                return status.title
        return 'Unknown (%d)' %self.status
    
    statusname = property(_statusname)


class GPGKey(SQLBase):
    _table = 'GPGKey'
    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
                   notNull=True),
        StringCol('keyid', dbName='keyid', notNull=True),
        StringCol('fingerprint', dbName='fingerprint', notNull=True),
        StringCol('pubkey', dbName='pubkey', notNull=True),
        BoolCol('revoked', dbName='revoked', notNull=True),
        IntCol('algorithm', dbName='algorithm', notNull=True),
        IntCol('keysize', dbName='keysize', notNull=True),
        ]

    def _algorithmname(self):
        for algorithm in dbschema.GPGKeyAlgorithms.items:
            if algorithm.value == self.algorithm:
                return algorithm.title
        return 'Unknown (%d)' %self.algorithm
    
    algorithmname = property(_algorithmname)

class ArchUserID(SQLBase):
    _table = 'ArchUserID'
    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
                   notNull=True),
        StringCol('archuserid', dbName='archuserid', notNull=True)
        ]
    
class WikiName(SQLBase):
    _table = 'WikiName'
    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
                   notNull=True),
        StringCol('wiki', dbName='wiki', notNull=True),
        StringCol('wikiname', dbName='wikiname', notNull=True)
        ]

class JabberID(SQLBase):
    _table = 'JabberID'
    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
                   notNull=True),
        StringCol('jabberid', dbName='jabberid', notNull=True)
        ]

class IrcID(SQLBase):
    _table = 'IrcID'
    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
                   notNull=True),
        StringCol('network', dbName='network', notNull=True),
        StringCol('nickname', dbName='nickname', notNull=True)
        ]

class Membership(SQLBase):
    _table = 'Membership'
    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
                   notNull=True),
        ForeignKey(name='team', foreignKey='Person', dbName='team',
                   notNull=True),
        IntCol('role', dbName='role', notNull=True),
        IntCol('status', dbName='status', notNull=True)
        ]

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
    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
                   notNull=True),
        ForeignKey(name='team', foreignKey='Person', dbName='team',
                   notNull=True)
        ]


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

