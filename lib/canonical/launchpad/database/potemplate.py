
from canonical.database.sqlbase import SQLBase, quote

from types import NoneType
from datetime import datetime
from sets import Set

standardPOTemplateCopyright = 'Canonical Ltd'

from canonical.launchpad.interfaces import *
from canonical.database.constants import nowUTC
from canonical.launchpad.dlalo import POFile
from canonical.launchpad.database.pomsgset import POMessageSet

from sqlobject import ForeignKey, MultipleJoin, RelatedJoin, IntCol, \
    BoolCol, StringCol, DateTimeCol, SQLObjectNotFound
from zope.interface import implements, directlyProvides
from zope.component import getUtility
from canonical.lp.dbschema import RosettaTranslationOrigin


class POTemplate(SQLBase):
    implements(IEditPOTemplate)

    _table = 'POTemplate'

    _columns = [
        ForeignKey(name='product', foreignKey='Product', dbName='product',
            notNull=True),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
        StringCol(name='path', dbName='path', notNull=True),
        BoolCol(name='isCurrent', dbName='iscurrent', notNull=True),
        DateTimeCol(name='dateCreated', dbName='datecreated'),
        StringCol(name='copyright', dbName='copyright'),
        ForeignKey(name='branch', foreignKey='Branch', dbName='branch',
                   notNull=True),
        IntCol(name='messageCount', dbName='messagecount', notNull=True),
        IntCol(name='priority', dbName='priority', notNull=True),
        # XXX cheating, as we don't yet have classes for these
        IntCol(name='license', dbName='license', notNull=True),
    ]

    _poFilesJoin = MultipleJoin('POFile', joinColumn='potemplate')

    def poFiles(self):
        return iter(self._poFilesJoin)

    def languages(self):
        '''This returns the set of languages for which we have
        POFiles for this POTemplate. NOTE that variants are simply
        ignored, if we have three variants for en_GB we will simply
        return a single record for en_GB.

        XXX NEED DISTINCT=TRUE'''
        return Set(Language.select('''
            POFile.language = Language.id AND
            POFile.potemplate = %d
            ''' % self.id, clauseTables=('POFile', 'Language')))

    def poFile(self, language_code, variant=None):
        if variant is None:
            variantspec = 'IS NULL'
        else:
            variantspec = (u'= "%s"' % quote(variant)).encode('utf-8')

        ret = POFile.select("""
            POFile.potemplate = %d AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            """ % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=('Language',))

        if ret.count() == 0:
            raise KeyError, language_code
        else:
            return ret[0]

    def currentMessageSets(self):
        return POMessageSet.select(
            '''
            POMsgSet.potemplate = %d AND
            POMsgSet.pofile IS NULL AND
            POMsgSet.sequence > 0
            '''
            % self.id, orderBy='sequence')

    def __iter__(self):
            return iter(self.currentMessageSets())

    def __len__(self):
        '''Return the number of CURRENT MessageSets in this POTemplate.'''
        # XXX: Should we use the cached value POTemplate.messageCount instead?
        return self.currentMessageSets().count()

    def messageSet(self, key, onlyCurrent=False):
        query = '''potemplate = %d AND pofile is NULL''' % self.id
        if onlyCurrent:
            query += ' AND sequence > 0'

        if isinstance(key, slice):
            return POMessageSet.select(query, orderBy='sequence')[key]

        if not isinstance(key, unicode):
            raise TypeError(
                "Can't index with type %s. (Must be slice or unicode.)"
                    % type(key))

        # Find a message ID with the given text.
        try:
            messageID = POMessageID.byMsgid(key)
        except SQLObjectNotFound:
            raise KeyError, key

        # Find a message set with the given message ID.

        results = POMessageSet.select(query +
            (' AND primemsgid = %d' % messageID.id))

        if results.count() == 0:
            raise KeyError, key
        else:
            assert results.count() == 1

            return results[0]

    # XXX: currentCount, updatesCount and rosettaCount should be updated with
    # a way that let's us query the database instead of use the cached value

    def currentCount(self, language):
        try:
            return self.poFile(language).currentCount
        except KeyError:
            return 0

    def updatesCount(self, language):
        try:
            return self.poFile(language).updatesCount
        except KeyError:
            return 0

    def rosettaCount(self, language):
        try:
            return self.poFile(language).rosettaCount
        except KeyError:
            return 0

    def hasMessageID(self, messageID):
        results = POMessageSet.selectBy(
            poTemplateID=self.id,
            poFileID=None,
            primeMessageID_ID=messageID.id)

        return results.count() > 0

    def hasPluralMessage(self):
        results = POMessageIDSighting.select('''
            pluralform = 1 AND
            pomsgset IN (SELECT id FROM POMsgSet WHERE potemplate = %d)
            ''' % self.id)

        return results.count() > 0

    def __getitem__(self, key):
        return self.messageSet(key, onlyCurrent=True)

    # IEditPOTemplate

    def expireAllMessages(self):
        self._connection.query('UPDATE POMsgSet SET sequence = 0'
                               ' WHERE potemplate = %d AND pofile IS NULL'
                               % self.id)

    def newPOFile(self, person, language_code, variant=None):
        try:
            self.poFile(language_code, variant)
        except KeyError:
            pass
        else:
            raise KeyError(
                "This template already has a POFile for %s variant %s" %
                (language.englishName, variant))

        try:
            language = Language.byCode(language_code)
        except SQLObjectNotFound:
            raise ValueError, "Unknown language code '%s'" % language_code

        now = datetime.now()
        data = {
            'year': now.year,
            'languagename': language.englishName,
            'languagecode': language_code,
            'productname': self.product.title,
            'date': now.isoformat(' '),
            # XXX: This is not working and I'm not able to fix it easily
            #'templatedate': self.dateCreated.gmtime().Format('%Y-%m-%d %H:%M+000'),
            'templatedate': self.dateCreated,
            'copyright': self.copyright,
            'nplurals': language.pluralForms or 1,
            'pluralexpr': language.pluralExpression or '0',
            }

        return POFile(poTemplate=self,
                      language=language,
                      headerFuzzy=True,
                      title='%(languagename)s translation for %(productname)s' % data,
                      description="", # XXX: fill it
                      topComment=standardPOFileTopComment % data,
                      header=standardPOFileHeader % data,
                      lastTranslator=person,
                      currentCount=0,
                      updatesCount=0,
                      rosettaCount=0,
                      owner=person,
                      lastParsed=nowUTC,
                      pluralForms=data['nplurals'],
                      variant=variant)

    def createMessageSetFromMessageID(self, messageID):
        return createMessageSetFromMessageID(self, messageID)

    def createMessageSetFromText(self, text):
        return createMessageSetFromText(self, text)


