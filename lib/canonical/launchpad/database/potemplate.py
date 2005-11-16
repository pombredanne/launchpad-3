# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POTemplateSubset', 'POTemplateSet', 'POTemplate']

import StringIO
import datetime

# Zope interfaces
from zope.interface import implements, providedBy
from zope.event import notify

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, SQLObjectNotFound

from canonical.lp.dbschema import RosettaImportStatus, EnumCol

from canonical.database.sqlbase import (
    SQLBase, quote, flush_database_updates, sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import DEFAULT, UTC_NOW

from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPOTemplate, IPOTemplateSet, IPOTemplateSubset, IRawFileData,
    LanguageNotFound, TranslationConstants, NotFoundError, NameNotAvailable,
    RawFileBusy)

from canonical.launchpad.database.language import Language
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.pomsgidsighting import POMsgIDSighting
from canonical.launchpad.database.potemplatename import POTemplateName
from canonical.launchpad.database.pofile import POFile, DummyPOFile
from canonical.launchpad.database.pomsgid import POMsgID

from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.components.poimport import import_po
from canonical.launchpad.event.sqlobjectevent import SQLObjectModifiedEvent
from canonical.launchpad.components.poparser import (POSyntaxError,
    POInvalidInputError)

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
"Plural-Forms: nplurals=%(nplurals)d; plural=%(pluralexpr)s\n"
)

class POTemplate(SQLBase, RosettaStats):
    implements(IPOTemplate, IRawFileData)

    _table = 'POTemplate'

    productseries = ForeignKey(foreignKey='ProductSeries',
        dbName='productseries', notNull=False, default=None)
    priority = IntCol(dbName='priority', notNull=False, default=None)
    potemplatename = ForeignKey(foreignKey='POTemplateName',
        dbName='potemplatename', notNull=True)
    description = StringCol(dbName='description', notNull=False, default=None)
    copyright = StringCol(dbName='copyright', notNull=False, default=None)
    license = IntCol(dbName='license', notNull=False, default=None)
    datecreated = UtcDateTimeCol(dbName='datecreated', default=DEFAULT)
    path = StringCol(dbName='path', notNull=False, default=None)
    iscurrent = BoolCol(dbName='iscurrent', notNull=True, default=True)
    messagecount = IntCol(dbName='messagecount', notNull=True, default=0)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=False, default=None)
    from_sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='from_sourcepackagename', notNull=False, default=None)
    sourcepackageversion = StringCol(dbName='sourcepackageversion',
        notNull=False, default=None)
    distrorelease = ForeignKey(foreignKey='DistroRelease',
        dbName='distrorelease', notNull=False, default=None)
    header = StringCol(dbName='header', notNull=False, default=None)
    binarypackagename = ForeignKey(foreignKey='BinaryPackageName',
        dbName='binarypackagename', notNull=False, default=None)
    languagepack = BoolCol(dbName='languagepack', notNull=True, default=False)

    # joins
    pofiles = MultipleJoin('POFile', joinColumn='potemplate')

    def __len__(self):
        """Return the number of CURRENT POTMsgSets in this POTemplate."""
        return self.messageCount()

    def __iter__(self):
        """See IPOTemplate."""
        return self.getPOTMsgSets()

    def __getitem__(self, key):
        """See IPOTemplate."""
        return self.getPOTMsgSetByMsgIDText(key, onlyCurrent=True)

    # properties
    @property
    def name(self):
        """See IPOTemplate."""
        return self.potemplatename.name

    @property
    def displayname(self):
        """See IPOTemplate."""
        if self.productseries:
            dn = '%s in %s %s' % (
                self.name,
                self.productseries.product.displayname,
                self.productseries.displayname)
        if self.distrorelease:
            dn = '%s in %s %s package "%s"' % (
                self.name,
                self.distrorelease.distribution.displayname,
                self.distrorelease.displayname,
                self.sourcepackagename.name)
        return dn

    @property
    def title(self):
        """See IPOTemplate."""
        if self.productseries:
            title = 'Template "%s" in %s %s' % (
                self.name,
                self.productseries.product.displayname,
                self.productseries.displayname)
        if self.distrorelease:
            title = 'Template "%s" in %s %s package "%s"' % (
                self.name,
                self.distrorelease.distribution.displayname,
                self.distrorelease.displayname,
                self.sourcepackagename.name)
        return title


    @property
    def translationgroups(self):
        """See IPOTemplate."""
        ret = []
        if self.distrorelease:
            tg = self.distrorelease.distribution.translationgroup
            if tg is not None:
                ret.append(tg)
        elif self.productseries:
            product_tg = self.productseries.product.translationgroup
            if product_tg is not None:
                ret.append(product_tg)
            project = self.productseries.product.project
            if project is not None:
                if project.translationgroup is not None:
                    ret.append(project.translationgroup)
        else:
            raise NotImplementedError('Cannot find translation groups.')
        return ret

    @property
    def translationpermission(self):
        """See IPOTemplate."""
        if self.distrorelease:
            # in the case of a distro template, use the distro translation
            # permission settings
            return self.distrorelease.distribution.translationpermission
        elif self.productseries:
            # for products, use the "most restrictive permission" between
            # project and product.
            return self.productseries.product.aggregatetranslationpermission

    @property
    def relatives_by_name(self):
        "See IPOTemplate"
        return POTemplate.select('''
            id <> %s AND
            potemplatename = %s
            ''' % sqlvalues (self.id, self.potemplatename.id),
            orderBy=['datecreated'])

    @property
    def relatives_by_source(self):
        "See IPOTemplate"
        if self.productseries:
            return POTemplate.select('''
                id <> %s AND
                productseries = %s
                ''' % sqlvalues(self.id, self.productseries.id),
                orderBy=['id'])
        elif self.distrorelease and self.sourcepackagename:
            return POTemplate.select('''
                id <> %s AND
                distrorelease = %s AND
                sourcepackagename = %s
                ''' % sqlvalues(self.id,
                    self.distrorelease.id, self.sourcepackagename.id),
                orderBy=['id'])
        else:
            raise AssertionError('Unknown POTemplate source.')

    @property
    def language_count(self):
        return Language.select('''
            POFile.language = Language.id AND
            POFile.currentcount + POFile.rosettacount > 0 AND
            POFile.potemplate = %s
            ''' % sqlvalues(self.id),
            clauseTables=['POFile'],
            distinct=True).count()

    @property
    def translationtarget(self):
        if self.productseries is not None:
            return self.productseries
        elif self.distrorelease is not None:
            from canonical.launchpad.database.sourcepackage import \
                SourcePackage
            return SourcePackage(distrorelease=self.distrorelease,
                sourcepackagename=self.sourcepackagename)
        raise AssertionError('Unknown POTemplate translation target')

    def getPOTMsgSetByMsgIDText(self, key, onlyCurrent=False):
        """See IPOTemplate."""
        query = 'potemplate = %s' % sqlvalues(self.id)
        if onlyCurrent:
            query += ' AND sequence > 0'

        # Find a message ID with the given text.
        try:
            pomsgid = POMsgID.byMsgid(key)
        except SQLObjectNotFound:
            raise NotFoundError(key)

        # Find a message set with the given message ID.

        result = POTMsgSet.selectOne(query +
            (' AND primemsgid = %s' % sqlvalues(pomsgid.id)))

        if result is None:
            raise NotFoundError(key)
        return result

    def getPOTMsgSetBySequence(self, key, onlyCurrent=False):
        """See IPOTemplate."""
        query = 'potemplate = %s' % sqlvalues(self.id)
        if onlyCurrent:
            query += ' AND sequence > 0'

        return POTMsgSet.select(query, orderBy='sequence')[key]

    def getPOTMsgSets(self, current=True, slice=None):
        """See IPOTemplate."""
        if current:
            # Only count the number of POTMsgSet that are current.
            results = POTMsgSet.select(
                'POTMsgSet.potemplate = %s AND POTMsgSet.sequence > 0' %
                    sqlvalues(self.id),
                orderBy='sequence')
        else:
            results = POTMsgSet.select(
                'POTMsgSet.potemplate = %s' % sqlvalues(self.id),
                orderBy='sequence')

        if slice is not None:
            # Want only a subset specified by slice
            results = results[slice]

        for potmsgset in results:
            yield potmsgset

    def getPOTMsgSetsCount(self, current=True):
        """See IPOTemplate."""
        if current:
            # Only count the number of POTMsgSet that are current
            results = POTMsgSet.select(
                'POTMsgSet.potemplate = %s AND POTMsgSet.sequence > 0' %
                    sqlvalues(self.id))
        else:
            results = POTMsgSet.select(
                'POTMsgSet.potemplate = %s' % sqlvalues(self.id))

        return results.count()

    def getPOTMsgSetByID(self, id):
        """See IPOTemplate."""
        return POTMsgSet.selectOne(
            "POTMsgSet.potemplate = %d AND POTMsgSet.id = %d" % (self.id, id))

    def languages(self):
        """See IPOTemplate."""
        return Language.select("POFile.language = Language.id AND "
                               "POFile.potemplate = %d AND "
                               "POFile.variant IS NULL" % self.id,
                               clauseTables=['POFile', 'Language'],
                               distinct=True
                               )

    def poFilesToImport(self):
        """See IPOTemplate."""
        for pofile in self.pofiles:
            if pofile.rawimportstatus == RosettaImportStatus.PENDING:
                yield pofile

    def getPOFileByPath(self, path):
        """See IPOTemplate."""
        pofile = POFile.selectOne("""
            POFile.potemplate = %s AND
            POFile.path %s
            """ % sqlvalues(self.id, path))
        if pofile is None:
            raise NotFoundError(path)
        return pofile

    def getPOFileByLang(self, language_code, variant=None):
        """See IPOTemplate."""
        if variant is None:
            variantspec = 'IS NULL'
        elif isinstance(variant, unicode):
            variantspec = (u'= %s' % quote(variant))
        else:
            raise TypeError('Variant must be None or unicode.')

        pofile = POFile.selectOne("""
            POFile.potemplate = %d AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            """ % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=['Language'])
        if pofile is None:
            raise NotFoundError(language_code)
        return pofile

    def queryPOFileByLang(self, language_code, variant=None):
        try:
            pofile = self.getPOFileByLang(language_code, variant)
            return pofile
        except NotFoundError:
            return None

    def messageCount(self):
        return self.messagecount

    def currentCount(self, language):
        try:
            return self.getPOFileByLang(language).currentCount()
        except NotFoundError:
            return 0

    def updatesCount(self, language):
        try:
            return self.getPOFileByLang(language).updatesCount()
        except NotFoundError:
            return 0

    def rosettaCount(self, language):
        try:
            return self.getPOFileByLang(language).rosettaCount()
        except NotFoundError:
            return 0

    def hasMessageID(self, messageID):
        results = POTMsgSet.selectBy(
            potemplateID=self.id, primemsgid_ID=messageID.id)
        return results.count() > 0

    def hasPluralMessage(self):
        results = POMsgIDSighting.select('''
            POMsgIDSighting.pluralform = %s AND
            POMsgIDSighting.potmsgset = POTMsgSet.id AND
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0
            ''' % sqlvalues(
                TranslationConstants.PLURAL_FORM,
                self.id), clauseTables=['POTMsgSet'])
        return results.count() > 0

    def export(self):
        """See IPOTemplate."""
        rawfile = IRawFileData(self)
        return helpers.getRawFileData(rawfile)

    def expireAllMessages(self):
        """See IPOTemplate."""
        for potmsgset in self:
            potmsgset.sequence = 0

    def getOrCreatePOFile(self, language_code, variant=None, owner=None):
        """See IPOTemplate."""
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
            'copyright': '(c) %d Canonical Ltd, and Rosetta Contributors'
                         % now.year,
            'nplurals': language.pluralforms or 1,
            'pluralexpr': language.pluralexpression or '0',
            }

        if self.productseries is not None:
            data['origin'] = self.productseries.product.name
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

        pofile = POFile(potemplate=self,
                      language=language,
                      topcomment=standardPOFileTopComment % data,
                      header=standardPOFileHeader % data,
                      fuzzyheader=True,
                      owner=owner,
                      pluralforms=data['nplurals'],
                      variant=variant)
        flush_database_updates()
        return pofile

    def getPOFileOrDummy(self, language_code, variant=None, owner=None):
        """See IPOTemplate."""
        # see if one exists already
        existingpo = self.queryPOFileByLang(language_code, variant)
        if existingpo is not None:
            return existingpo

        # since we don't have one, we will return a dummy
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
            'copyright': '(c) %d Canonical Ltd, and Rosetta Contributors'
                         % now.year,
            'nplurals': language.pluralforms or 1,
            'pluralexpr': language.pluralexpression or '0',
            }

        if self.productseries is not None:
            data['origin'] = self.productseries.product.name
        else:
            data['origin'] = self.sourcepackagename.name

        return DummyPOFile(self, language, owner=owner,
            header=standardPOFileHeader % data)

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
        """See IPOTemplate."""
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
        """See IPOTemplate."""
        try:
            messageID = POMsgID.byMsgid(text)
            if self.hasMessageID(messageID):
                raise NameNotAvailable(
                    "There is already a message set for this template, file "
                    "and primary msgid")
        except SQLObjectNotFound:
            # If there are no existing message ids, create a new one.
            # We do not need to check whether there is already a message set
            # with the given text in this template.
            messageID = POMsgID(msgid=text)

        return self.createMessageSetFromMessageID(messageID)

    def invalidateCache(self):
        """See IPOTemplate."""
        for pofile in self.pofiles:
            pofile.invalidateCache()

    # ICanAttachRawFileData implementation

    def attachRawFileData(self, contents, published, importer=None,
        date_import=UTC_NOW):
        """See ICanAttachRawFileData."""
        rawfile = IRawFileData(self)
        if rawfile.rawimportstatus == RosettaImportStatus.PENDING:
            raise RawFileBusy

        # a POTemplate is ALWAYS "published"
        assert published == True, 'POTemplate is always "published"'

        filename = '%s.pot' % self.potemplatename.translationdomain
        helpers.attachRawFileData(
            self, filename, contents, importer, date_import)

    def attachRawFileDataAsFileAlias(self, alias, published, importer=None,
        date_import=UTC_NOW):
        """See ICanAttachRawFileData."""
        rawfile = IRawFileData(self)
        if rawfile.rawimportstatus == RosettaImportStatus.PENDING:
            raise RawFileBusy

        # a POTemplate is ALWAYS "published"
        assert published == True, 'POTemplate is always "published"'

        helpers.attachRawFileDataByFileAlias(
            self, alias, importer, date_import)

    # IRawFileData implementation

    # Any use of this interface should adapt this object as an IRawFileData.

    rawfile = ForeignKey(foreignKey='LibraryFileAlias', dbName='rawfile',
                         notNull=True)
    rawimporter = ForeignKey(foreignKey='Person', dbName='rawimporter',
        notNull=True)
    daterawimport = UtcDateTimeCol(dbName='daterawimport', notNull=True,
        default=UTC_NOW)
    rawimportstatus = EnumCol(dbName='rawimportstatus', notNull=True,
        schema=RosettaImportStatus, default=RosettaImportStatus.IGNORE)

    # preserve the interface semantics
    @property
    def rawfilepublished(self):
        return True

    def doRawImport(self, logger=None):
        """See IRawFileData."""
        rawdata = helpers.getRawFileData(self)

        file = StringIO.StringIO(rawdata)

        # Store the object status before the changes.
        object_before_modification = helpers.Snapshot(
            self, providing=providedBy(self))

        try:
            import_po(self, file)
        except (POSyntaxError, POInvalidInputError):
            # The import failed, we mark it as failed so we could review it
            # later in case it's a bug in our code.
            self.rawimportstatus = RosettaImportStatus.FAILED
            if logger:
                logger.warning(
                    'We got an error importing %s', self.title, exc_info=1)
            return

        # The import has been done, we mark it that way.
        self.rawimportstatus = RosettaImportStatus.IMPORTED

        # Ask for a sqlobject sync before reusing the data we just
        # updated.
        flush_database_updates()

        # We update the cached value that tells us the number of msgsets
        # this .pot file has
        self.messagecount = self.getPOTMsgSetsCount()

        # And now, we should update the statistics for all po files this
        # .pot file has because msgsets will have changed.
        for pofile in self.pofiles:
            pofile.updateStatistics()

        # List of fields that would be updated.
        fields = ['header', 'rawimportstatus', 'messagecount']

        # And finally, emit the modified event.
        notify(SQLObjectModifiedEvent(self, object_before_modification, fields))



class POTemplateSubset:
    implements(IPOTemplateSubset)

    def __init__(self, sourcepackagename=None,
                 distrorelease=None, productseries=None):
        """Create a new POTemplateSubset object.

        The set of POTemplate depends on the arguments you pass to this
        constructor. The sourcepackagename, distrorelease and productseries
        are just filters for that set.
        """
        self.sourcepackagename = sourcepackagename
        self.distrorelease = distrorelease
        self.productseries = productseries

        if (productseries is not None and (distrorelease is not None or
            sourcepackagename is not None)):
            raise ValueError('A product release must not be used '
                             'with a source package name or a distro '
                             'release.')
        elif productseries is not None:
            self.query = ('POTemplate.productseries = %d' % productseries.id)
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
            raise ValueError('You need to specify the kind '
                             'of subset you want.')

    def __iter__(self):
        """See IPOTemplateSubset."""
        res = POTemplate.select(self.query, clauseTables=self.clausetables,
                                orderBy=self.orderby)

        for potemplate in res:
            yield potemplate

    def __len__(self):
        """See IPOTemplateSubset."""
        res = POTemplate.select(self.query, clauseTables=self.clausetables)
        return res.count()

    def __getitem__(self, name):
        """See IPOTemplateSubset."""
        return self.getPOTemplateByName(name)

    @property
    def title(self):
        """See IPOTemplateSubset."""
        titlestr = ''
        if self.distrorelease:
            titlestr += ' ' + self.distrorelease.displayname
        if self.sourcepackagename:
            titlestr += ' ' + self.sourcepackagename.name
        if self.productseries:
            titlestr += ' '
            titlestr += self.productseries.displayname
        return titlestr

    def new(self, potemplatename, contents, owner):
        """See IPOTemplateSubset."""
        filename = '%s.pot' % potemplatename.translationdomain
        alias = helpers.uploadRosettaFile(filename, contents)
        return POTemplate(potemplatename=potemplatename,
                          sourcepackagename=self.sourcepackagename,
                          distrorelease=self.distrorelease,
                          productseries=self.productseries,
                          owner=owner,
                          daterawimport=UTC_NOW,
                          rawfile=alias,
                          rawimporter=owner,
                          rawimportstatus=RosettaImportStatus.PENDING)

    def getPOTemplateByName(self, name):
        """See IPOTemplateSubset."""
        try:
            ptn = POTemplateName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

        if self.query is None:
            query = 'POTemplate.potemplatename = %d' % ptn.id
        else:
            query = '%s AND POTemplate.potemplatename = %d' % (self.query,
                ptn.id)

        result = POTemplate.selectOne(query, clauseTables=self.clausetables)
        if result is None:
            raise NotFoundError(name)
        return result

    def getByPath(self, path):
        """See IPOTemplateSubset."""
        if self.query is None:
            query = 'POTemplate.path = %s' % path
        else:
            query = '%s POTemplate.path = %s' % (self.query, path)

        result = POTemplate.selectOne(query, clauseTables=self.clausetables)
        if result is None:
            raise NotFoundError(path)
        return result


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
            raise NotFoundError(name)

        result = POTemplate.selectOne('POTemplate.potemplatename = %d' % ptn.id)
        if result is None:
            raise NotFoundError(name)
        return result

    def getSubset(self, **kw):
        """See IPOTemplateSet."""
        if kw.get('distrorelease'):
            # XXX: Should this really be an assert?
            #      -- SteveAlexander 2005-04-23
            assert 'productseries' not in kw

            distrorelease = kw['distrorelease']

            if kw.get('sourcepackagename'):
                sourcepackagename = kw['sourcepackagename']
                return POTemplateSubset(
                    distrorelease=distrorelease,
                    sourcepackagename=sourcepackagename)
            else:
                return POTemplateSubset(distrorelease=distrorelease)

        # XXX: Should this really be an assert?
        #      -- SteveAlexander 2005-04-23
        assert kw.get('productseries')
        return POTemplateSubset(productseries=kw['productseries'])

    def getSubsetFromRealSourcePackageName(self, distrorelease,
        sourcepackagename):
        """See IPOTemplateSet."""
        if distrorelease is None or sourcepackage is None:
            raise RunTimeError(
                'distrorelease and sourcepackage must be not None.')

        return POTemplateSubset(
            distrorelease=distrorelease,
            from_sourcepackagename=sourcepackagename)

    def getTemplatesPendingImport(self):
        """See IPOTemplateSet."""
        results = POTemplate.selectBy(
            rawimportstatus=RosettaImportStatus.PENDING,
            orderBy='-daterawimport')

        for potemplate in results:
            yield potemplate

    def getPOTemplateByPathAndOrigin(self, path, productseries=None,
        distrorelease=None, sourcepackagename=None):
        """See IPOTemplateSet."""
        if sourcepackagename is not None:
            # The POTemplate belongs to a distribution and it could come from
            # another package that the one it's linked at the moment so we
            # first check to find it at IPOTemplate.from_sourcepackagename
            potemplate = POTemplate.selectOne('''
                    POTemplate.distrorelease = %s AND
                    POTemplate.from_sourcepackagename = %s AND
                    POTemplate.path = %s''' % sqlvalues(
                        distrorelease.id,
                        sourcepackagename.id,
                        path)
                    )
            if potemplate is not None:
                # There is no potemplate in that 'path' and
                # 'from_sourcepackagename' so we do a search using the usual
                # sourcepackagename.
                return potemplate

            potemplate = POTemplate.selectOne('''
                    POTemplate.distrorelease = %s AND
                    POTemplate.sourcepackagename = %s AND
                    POTemplate.path = %s''' % sqlvalues(
                        distrorelease.id,
                        sourcepackagename.id,
                        path)
                    )

            if potemplate is None:
                raise NotFoundError(
                    'There is no POTemplate at %s for %s that comes from'
                    ' %s' % (
                        sourcepackagename.name, distrorelease.name, path)
                    )
            else:
                return potemplate
        else:
            potemplate = POTemplate.selectOne('''
                    POTemplate.productseries = %s AND
                    POTemplate.path = %s''' % sqlvalues(
                        productseries.id,
                        path)
                    )

            if potemplate is None:
                raise NotFoundError(
                    'There is no POTemplate at %s that comes from %s' % (
                        productseries.title, path)
                    )
            else:
                return potemplate
