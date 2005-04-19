import StringIO
import base64
import datetime

# Zope interfaces
from zope.interface import implements
from zope.exceptions import NotFoundError

# SQL imports
from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote, flush_database_updates
from canonical.database.datetimecol import UtcDateTimeCol

# canonical imports
from canonical.launchpad.interfaces import IEditPOTemplate, IPOTemplateSet, \
    IPOTemplateSubset, IRawFileData, ITeam
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.pomsgidsighting import POMsgIDSighting
from canonical.lp.dbschema import EnumCol
from canonical.launchpad.database.potemplatename import POTemplateName
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.lp.dbschema import RosettaImportStatus
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad import helpers

from canonical.launchpad.components.pofile_adapters import TemplateImporter

standardPOFileTopComment = ''' %(languagename)s translation for %(origin)s
 Copyright (c) %(copyright)s %(year)s
 This file is distributed under the same license as the %(origin)s package.
 FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.

'''

standardPOFileHeader = (
"Project-Id-Version: %(origin)s\n"
"Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>\n"
"POT-Creation-Date: %(templatedate)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: %(languagename)s <%(languagecode)s@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"X-Rosetta-Version: 0.1\n"
"Plural-Forms: nplurals=%(nplurals)d; plural=%(pluralexpr)s\n"
)

class POTemplateSubset:
    implements(IPOTemplateSubset)

    def __init__(self, sourcepackagename=None,
                 distrorelease=None, productrelease=None):
        """Create a new POTemplateSubset object.

        The set of POTemplate depends on the arguments you pass to this
        constructor. The sourcepackagename, distrorelease and productrelease
        are just filters for that set.
        """

        self.sourcepackagename = sourcepackagename
        self.distrorelease = distrorelease
        self.productrelease = productrelease

        if (productrelease is not None and (distrorelease is not None or
            sourcepackagename is not None)):
            raise ValueError(
                'A product release must not be used with a source package name'
                ' or a distro release.')
        elif productrelease is not None:
            self.query = ('POTemplate.productrelease = %d' %
                          productrelease.id)
            self.orderby = None
            self.clausetables = None
        elif distrorelease is not None and sourcepackagename is not None:
            self.query = ('POTemplate.sourcepackagename = %d AND'
                          ' POTemplate.distrorelease = %d ' %
                          (sourcepackagename.id, distrorelease.id))
            self.orderby = None
            self.clausetables = None
        elif distrorelease is not None:
            self.query = (
                'POTemplate.distrorelease = DistroRelease.id AND'
                ' DistroRelease.id = %d' % distrorelease.id)
            self.orderby = 'DistroRelease.name'
            self.clausetables = ['DistroRelease']
        else:
            raise ValueError(
                'You need to specify the kind of subset you want.')

    def __iter__(self):
        """See IPOTemplateSubset."""
        res = POTemplate.select(self.query, clauseTables=self.clausetables,
                                orderBy=self.orderby)

        for potemplate in res:
            yield potemplate

    def __getitem__(self, name):
        """See IPOTemplateSubset."""
        try:
            ptn = POTemplateName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError, name

        if self.query is None:
            query = 'POTemplate.potemplatename = %d' % ptn.id
        else:
            query = '%s AND POTemplate.potemplatename = %d' % (
                    self.query, ptn.id)

        res = POTemplate.select(query, clauseTables=self.clausetables)

        if res.count() == 0:
            raise NotFoundError, name
        else:
            return res[0]

    def title(self):
        titlestr = ''
        if self.distrorelease:
            titlestr += ' ' + self.distrorelease.displayname
        if self.sourcepackagename:
            titlestr += ' ' + self.sourcepackagename.name
        if self.productrelease:
            titlestr += ' '
            titlestr += self.productrelease.productseries.product.displayname
            titlestr += ' ' + self.productrelease.version
        return titlestr
    title = property(title)

    def new(self, potemplatename, title, contents, owner):
        if self.sourcepackagename is not None:
            sourcepackagename_id = self.sourcepackagename.id
        else:
            sourcepackagename_id = None
        if self.distrorelease is not None:
            distrorelease_id = self.distrorelease.id
        else:
            distrorelease_id = None
        if self.productrelease is not None:
            productrelease_id = self.productrelease.id
        else:
            productrelease_id = None

        encoded_file = base64.encodestring(contents)

        return POTemplate(potemplatenameID=potemplatename.id,
                          title=title,
                          sourcepackagenameID=sourcepackagename_id,
                          distroreleaseID=distrorelease_id,
                          productreleaseID=productrelease_id,
                          ownerID=owner.id,
                          daterawimport=UTC_NOW,
                          rawfile=encoded_file,
                          rawimporterID=owner.id,
                          rawimportstatus=RosettaImportStatus.PENDING)


class POTemplateSet:
    implements(IPOTemplateSet)

    def __iter__(self):
        """See IPOTemplateSet."""
        res = POTemplate.select()

        for potemplate in res:
            yield potemplate

    def __getitem__(self, name):
        """See IPOTemplateSet."""
        try:
            ptn = POTemplateName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError, name

        res = POTemplate.select('POTemplate.potemplatename = %d' % ptn.id)

        if res.count() == 0:
            raise NotFoundError, name
        else:
            return res[0]

    def getSubset(self, **kw):
        """See IPOTemplateSet."""
        if kw.get('distrorelease'):
            assert 'productrelease' not in kw

            distrorelease = kw['distrorelease']

            if kw.get('sourcepackagename'):
                sourcepackagename = kw['sourcepackagename']

                return POTemplateSubset(
                    distrorelease=distrorelease,
                    sourcepackagename=sourcepackagename)
            else:
                return POTemplateSubset(distrorelease=distrorelease)

        assert kw.get('productrelease')

        return POTemplateSubset(productrelease=kw['productrelease'])

    def getTemplatesPendingImport(self):
        """See IPOTemplateSet."""
        results = POTemplate.selectBy(
            rawimportstatus=RosettaImportStatus.PENDING)

        # XXX: Carlos Perello Marin 2005-03-24
        # Really ugly hack needed to do the initial import of the whole hoary
        # archive. It will disappear as soon as the whole
        # LaunchpadPackagePoAttach and LaunchpadPoImport are implemented so
        # rawfile is not used anymore and we start using Librarian.
        # The problem comes with the memory requirements to get more than 7500
        # rows into memory with about 200KB - 300KB of data each one.
        total = results.count()
        done = 0
        while done < total:
            for potemplate in results[done:done+100]:
                yield potemplate
            done = done + 100


class LanguageNotFound(ValueError):
    """Raised when a a language does not exists in the database."""


class POTemplate(SQLBase, RosettaStats):
    implements(IEditPOTemplate, IRawFileData)

    _table = 'POTemplate'

    productrelease = ForeignKey(foreignKey='ProductRelease',
        dbName='productrelease', notNull=False, default=None)
    priority = IntCol(dbName='priority', notNull=False, default=None)
    potemplatename = ForeignKey(foreignKey='POTemplateName',
        dbName='potemplatename', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=False, default=None)
    copyright = StringCol(dbName='copyright', notNull=False, default=None)
#   license = ForeignKey(foreignKey='License', dbName='license', notNull=True)
    license = IntCol(dbName='license', notNull=False, default=None)
    datecreated = UtcDateTimeCol(dbName='datecreated', default=DEFAULT)
    path = StringCol(dbName='path', notNull=False, default=None)
    iscurrent = BoolCol(dbName='iscurrent', notNull=True, default=True)
    messagecount = IntCol(dbName='messagecount', notNull=True, default=0)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=False, default=None)
    sourcepackageversion = StringCol(dbName='sourcepackageversion',
        notNull=False, default=None)
    distrorelease = ForeignKey(foreignKey='DistroRelease',
        dbName='distrorelease', notNull=False, default=None)
    header = StringCol(dbName='header', notNull=False, default=None)
    binarypackagename = ForeignKey(foreignKey='BinaryPackageName',
        dbName='binarypackagename', notNull=False, default=None)
    languagepack = BoolCol(dbName='languagepack', notNull=True, default=False)
    filename = StringCol(dbName='filename', notNull=False, default=None)

    # joins
    poFiles = MultipleJoin('POFile', joinColumn='potemplate')

    def __len__(self):
        '''Return the number of CURRENT POTMsgSets in this POTemplate.'''
        return self.messageCount()

    def __iter__(self):
            return iter(self.currentMessageSets())

    def __getitem__(self, key):
        return self.messageSet(key, onlyCurrent=True)

    # properties
    def name(self):
        return self.potemplatename.name
    name = property(name)

    def messageSet(self, key, onlyCurrent=False):
        query = '''potemplate = %d''' % self.id
        if onlyCurrent:
            query += ' AND sequence > 0'

        if isinstance(key, slice):
            return POTMsgSet.select(query, orderBy='sequence')[key]

        if not isinstance(key, unicode):
            raise TypeError(
                "Can't index with type %s. (Must be slice or unicode.)"
                    % type(key))

        # Find a message ID with the given text.
        try:
            messageID = POMsgID.byMsgid(key)
        except SQLObjectNotFound:
            raise KeyError, key

        # Find a message set with the given message ID.

        results = POTMsgSet.select(query +
            (' AND primemsgid = %d' % messageID.id))

        if results.count() == 0:
            raise KeyError, key
        else:
            assert results.count() == 1

            return results[0]

    def currentMessageSets(self):
        return POTMsgSet.select(
            '''
            POTMsgSet.potemplate = %d AND
            POTMsgSet.sequence > 0
            '''
            % self.id, orderBy='sequence')

    def getPOTMsgSetByID(self, id):
        """See IPOTemplate."""
        results = POTMsgSet.select("POTMsgSet.potemplate = %d AND"
                                   " POTMsgSet.id = %d" % (self.id, id))
        if results.count():
            return results[0]
        else:
            return None

    def filterMessageSets(self, current, translated, languages, slice = None):
        '''
        Return message sets from this PO template, filtered by various
        properties.

        current:
            Whether the message sets need be complete or not.
        translated:
            Wether the messages sets need be translated in the specified
            languages or not.
        languages:
            The languages used for testing translatedness.
        slice:
            The range of results to be selected, or None, for all results.
        '''

        if current is not None:
            if current:
                current_condition = 'POTMsgSet.sequence > 0'
            else:
                current_condition = 'POTMsgSet.sequence = 0'
        else:
            current_condition = 'TRUE'

        # Assuming that for each language being checked, each POT mesage set
        # has a corresponding PO message set for that language:
        #
        # A POT set is translated if all its PO message sets have iscomplete =
        # TRUE. In other words, none of its PO message sets have iscomplete =
        # FALSE.
        #
        # A POT set is untranslated if any of its PO message set has
        # iscomplete = FALSE. In other words, not all of its PO message sets
        # have iscomplete = TRUE.
        #
        # The possible non-existance of corresponding PO message sets
        # complicates matters a bit:
        #
        # - For translated == True, missing PO message sets must make the
        #   condition evaluate to FALSE.
        #
        # - For translated == False, missing PO message sets must make the
        #   condition evaluate to TRUE.
        #
        # So, we get around this problem by checking the number of PO message
        # sets against the number of languages.

        language_codes = ', '.join([ "'%s'" % str(l.code) for l in languages ])

        if translated is not None:
            # Search for PO message sets which aren't complete for this POT
            # set.
            subquery1 = '''
                SELECT poset.id FROM POMsgSet poset, POFile pofile,
                        Language language WHERE
                    poset.potmsgset = POTMsgSet.id AND
                    poset.pofile = pofile.id AND
                    pofile.language = language.id AND
                    pofile.variant IS NULL AND
                    language.code IN (%s) AND
                    iscomplete = FALSE
                ''' % language_codes

            # Count PO message sets for this POT set.
            subquery2 = '''
                SELECT COUNT(poset.id) FROM POMsgSet poset, POFile pofile,
                        Language language WHERE
                    poset.potmsgset = POTMsgSet.id AND
                    poset.pofile = pofile.id AND
                    pofile.language = language.id AND
                    pofile.variant IS NULL AND
                    language.code IN (%s)
                ''' % language_codes

            if translated:
                translated_condition = ('NOT EXISTS (%s) AND (%s) = %d' %
                    (subquery1, subquery2, len(languages)))
            else:
                translated_condition = ('EXISTS (%s) OR (%s) < %d' %
                    (subquery1, subquery2, len(languages)))
        else:
            translated_condition = 'TRUE'

        results = POTMsgSet.select(
            'POTMsgSet.potemplate = %d AND (%s) AND (%s) '
                % (self.id, translated_condition, current_condition),
                orderBy = 'POTMsgSet.sequence')

        if slice is not None:
            return results[slice]
        else:
            return results

    def languages(self):
        '''This returns the set of languages for which we have
        POFiles for this POTemplate. NOTE that variants are simply
        ignored, if we have three variants for en_GB we will simply
        return the one with variant=NULL.'''

        return Language.select("POFile.language = Language.id AND "
                               "POFile.potemplate = %d AND "
                               "POFile.variant IS NULL" % self.id,
                               clauseTables=('POFile', 'Language'),
                               distinct=True
                               )

    def poFilesToImport(self):
        for pofile in iter(self.poFiles):
            if pofile.rawimportstatus == RosettaImportStatus.PENDING:
                yield pofile

    def getPOFileByLang(self, language_code, variant=None):
        if variant is None:
            variantspec = 'IS NULL'
        elif isinstance(variant, unicode):
            variantspec = (u'= %s' % quote(variant))
        else:
            raise TypeError('Variant must be None or unicode.')

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
            raise KeyError, 'PO File for %s does not exist' % language_code
        else:
            return ret[0]

    def queryPOFileByLang(self, language_code, variant=None):
        try:
            pofile = self.getPOFileByLang(language_code, variant)
            return pofile
        except KeyError:
            return None

    def messageCount(self):
        return self.messagecount

    def currentCount(self, language):
        try:
            return self.getPOFileByLang(language).currentCount()
        except KeyError:
            return 0

    def updatesCount(self, language):
        try:
            return self.getPOFileByLang(language).updatesCount()
        except KeyError:
            return 0

    def rosettaCount(self, language):
        try:
            return self.getPOFileByLang(language).rosettaCount()
        except KeyError:
            return 0

    def hasMessageID(self, messageID):
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %d AND
            POTMsgSet.primemsgid = %d''' % (self.id, messageID.id))

        return results.count() > 0

    def hasPluralMessage(self):
        results = POMsgIDSighting.select('''
            pluralform = 1 AND
            potmsgset IN (SELECT id FROM POTMsgSet WHERE potemplate = %d)
            ''' % self.id)

        return results.count() > 0

    def canEditTranslations(self, person):
        """See IPOTemplate."""
        if self.distrorelease is None:
            return True

        owner = self.owner

        if ITeam.providedBy(owner) and person.inTeam(owner):
            return True
        elif owner.id == person.id:
            return True

        # Now we check for the owners of the PO files.
        for pofile in self.poFiles:
            owner = pofile.owner
            if ITeam.providedBy(owner) and person.inTeam(owner):
                return True
            elif owner.id == person.id:
                return True

        return False


    # Methods defined in IEditPOTemplate

    def expireAllMessages(self):
        for msgset in self.currentMessageSets():
            msgset.sequence = 0

    def getOrCreatePOFile(self, language_code, variant=None, owner=None):
        """See IPOFile."""
        # see if one exists already
        existingpo = self.queryPOFileByLang(language_code, variant)
        if existingpo is not None:
            return existingpo

        # since we don't have one, create one
        try:
            language = Language.byCode(language_code)
        except SQLObjectNotFound:
            raise LanguageNotFound(language_code)

        now = datetime.datetime.now()
        data = {
            'year': now.year,
            'languagename': language.englishname,
            'languagecode': language_code,
            'date': now.isoformat(' '),
            'templatedate': self.datecreated,
            'copyright': '(c) %d Canonical Ltd, and Rosetta Contributors' % now.year,
            'nplurals': language.pluralforms or 1,
            'pluralexpr': language.pluralexpression or '0',
            }

        if self.productrelease is not None:
            data['origin'] = self.productrelease.product.name
        else:
            data['origin'] = self.sourcepackagename.name

        if owner is None:
            # All POFiles should have an owner, by default, the Ubuntu
            # Translators team.
            # XXX: Carlos Perello Marin 2005-04-15: We should get a better
            # default depending on the POFile and the associated POTemplate.
            # The import is here to prevent circular dependencies
            from canonical.launchpad.database.person import PersonSet

            # XXX Carlos Perello Marin 2005-03-28
            # This should be done with a celebrity.
            personset = PersonSet()
            owner = personset.getByName('ubuntu-translators')

        return POFile(potemplate=self,
                      language=language,
                      title='Rosetta %(languagename)s translation of %(origin)s' % data,
                      topcomment=standardPOFileTopComment % data,
                      header=standardPOFileHeader % data,
                      fuzzyheader=True,
                      owner=owner,
                      pluralforms=data['nplurals'],
                      variant=variant)

    def createMessageIDSighting(self, potmsgset, messageID):
        """Creates in the database a new message ID sighting.

        Returns None.
        """

        POMsgIDSighting(
            potmsgsetID=potmsgset.id,
            pomsgid_ID=messageID.id,
            datefirstseen=UTC_NOW,
            datelastseen=UTC_NOW,
            inlastrevision=True,
            pluralform=0)

    def createMessageSetFromMessageID(self, messageID):
        """Creates in the database a new message set.

        As a side-effect, creates a message ID sighting in the database for the
        new set's prime message ID.

        Returns that message set.
        """
        messageSet = POTMsgSet(
            primemsgid_=messageID,
            sequence=0,
            potemplate=self,
            commenttext=None,
            filereferences=None,
            sourcecomment=None,
            flagscomment=None)

        self.createMessageIDSighting(messageSet, messageID)

        return messageSet

    def createMessageSetFromText(self, text):
        # This method used to accept 'text' parameters being string objects,
        # but this is depracated.
        if not isinstance(text, unicode):
            raise TypeError("Message ID text must be unicode.")

        try:
            messageID = POMsgID.byMsgid(text)
            if self.hasMessageID(messageID):
                raise KeyError(
                    "There is already a message set for this template, file "
                    "and primary msgid")
        except SQLObjectNotFound:
            # If there are no existing message ids, create a new one.
            # We do not need to check whether there is already a message set
            # with the given text in this template.
            messageID = POMsgID(msgid=text)

        return self.createMessageSetFromMessageID(messageID)

    # ICanAttachRawFileData implementation

    def attachRawFileData(self, contents, importer=None):
        """See ICanAttachRawFileData."""
        helpers.attachRawFileData(self, contents, importer)


    # IRawFileData implementation

    # Any use of this interface should adapt this object as an IRawFileData.

    rawfile = StringCol(dbName='rawfile', notNull=True)
    rawimporter = ForeignKey(foreignKey='Person', dbName='rawimporter',
        notNull=True)
    daterawimport = UtcDateTimeCol(dbName='daterawimport', notNull=True,
        default=UTC_NOW)
    rawimportstatus = EnumCol(dbName='rawimportstatus', notNull=True,
        schema=RosettaImportStatus, default=RosettaImportStatus.IGNORE)

    def doRawImport(self, logger=None):
        """See IRawFileData."""

        # The owner of the import is the person who imported it.

        importer = TemplateImporter(self, self.rawimporter)

        file = StringIO.StringIO(base64.decodestring(self.rawfile))

        try:
            importer.doImport(file)

            # The import has been done, we mark it that way.
            self.rawimportstatus = RosettaImportStatus.IMPORTED

            # Ask for a sqlobject sync before reusing the data we just
            # updated.
            flush_database_updates()

            # We update the cached value that tells us the number of msgsets this
            # .pot file has
            self.messagecount = self.currentMessageSets().count()

            # And now, we should update the statistics for all po files this .pot
            # file has because a number of msgsets could have change.
            # XXX: Carlos Perello Marin 09/12/2004 We should handle this case
            # better. The pofile don't get updated the currentcount updated...
            for pofile in self.poFiles:
                pofile.updateStatistics()
        except:
            # The import failed, we mark it as failed so we could review it
            # later in case it's a bug in our code.
            self.rawimportstatus = RosettaImportStatus.FAILED
            if logger:
                logger.warning('We got an error importing %s' ,
                    self.potemplatename.name, exc_info = 1)
