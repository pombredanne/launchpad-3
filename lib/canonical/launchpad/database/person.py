

# Zope interfaces
from zope.interface import implements
from zope.component import ComponentLookupError
from zope.app.security.interfaces import IUnauthenticatedPrincipal

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
from canonical.launchpad.interfaces import *
from canonical.lp import dbschema


class Person(SQLBase):
    """A Person."""

    implements(IPerson)

    _columns = [
        StringCol('name', default=None),
        StringCol('displayname', default=None),
        StringCol('givenname', default=None),
        StringCol('familyname', default=None),
        StringCol('password', default=None),
        ForeignKey(name='teamowner', foreignKey='Person', dbName='teamowner'),
        StringCol('teamdescription', default=None),
        IntCol('karma'),
        DateTimeCol('karmatimestamp')
    ]

    _emailsJoin = MultipleJoin('RosettaEmailAddress', joinColumn='person')

    def emails(self):
        return iter(self._emailsJoin)

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

    def translatedTemplates(self):
        '''
        SELECT * FROM POTemplate WHERE
            id IN (SELECT potemplate FROM pomsgset WHERE
                id IN (SELECT pomsgset FROM POTranslationSighting WHERE
                    origin = 2
                ORDER BY datefirstseen DESC))
        '''
        return POTemplate.select('''
            id IN (SELECT potemplate FROM pomsgset WHERE
                id IN (SELECT pomsgset FROM POTranslationSighting WHERE
                    origin = 2
                ORDER BY datefirstseen DESC))
            ''')

    _labelsJoin = RelatedJoin('Label', joinColumn='person',
        otherColumn='label', intermediateTable='PersonLabel')

    def languages(self):
        languages = getUtility(ILanguages)
        try:
            schema = Schema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")

        for label in self._labelsJoin:
            if label.schema == schema:
                yield languages[label.name]

    def addLanguage(self, language):
        try:
            schema = Schema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        label = Label.selectBy(schemaID=schema.id, name=language.code)
        if label.count() < 1:
            # The label for this language does not exists yet into the
            # database, we should create it.
            label = Label(
                        schemaID=schema.id,
                        name=language.code,
                        title='Translates into ' + language.englishName,
                        description='A person with this label says that ' + \
                                    'knows how to translate into ' + \
                                    language.englishName)
        else:
            label = label[0]
        # This method comes from the RelatedJoin
        self.addLabel(label)

    def removeLanguage(self, language):
        try:
            schema = Schema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        label = Label.selectBy(schemaID=schema.id, name=language.code)[0]
        # This method comes from the RelatedJoin
        self.removeLabel(label)


class PersonSet(object):
    """The set of persons."""
    implements(IPersonSet)

    def __getitem__(self, personid):
        """See IPersonSet."""
	return Person.get(personid)


def personFromPrincipal(principal):
    """Adapt canonical.lp.placelessauth.interfaces.ILaunchpadPrincipal 
       to IPerson
    """
    if IUnauthenticatedPrincipal.providedBy(principal):
        # When Zope3 interfaces allow returning None for "cannot adapt"
        # we can return None here.
        ##return None
        raise ComponentLookupError
    return Person.get(principal.id)


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

class TeamParticipation(SQLBase):
    _table = 'TeamParticipation'
    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
                   notNull=True),
        ForeignKey(name='team', foreignKey='Person', dbName='team',
                   notNull=True)
        ]

