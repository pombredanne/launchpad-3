# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""`SQLObject` implementation of `IPOTemplate` interface."""

__metaclass__ = type
__all__ = [
    'POTemplate',
    'POTemplateSet',
    'POTemplateSubset',
    'POTemplateToTranslationFileDataAdapter',
    ]

import datetime
import os
from sqlobject import (
    BoolCol, ForeignKey, IntCol, SQLMultipleJoin, SQLObjectNotFound,
    StringCol)
from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase, quote, flush_database_updates, sqlvalues)
from canonical.launchpad import helpers
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.pofile import POFile, DummyPOFile
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.translationimportqueue import (
    TranslationImportQueueEntry)
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IPOTemplate, IPOTemplateSet, IPOTemplateSubset,
    ITranslationExporter, ITranslationFileData, ITranslationImporter,
    IVPOTExportSet, LanguageNotFound, NotFoundError, RosettaImportStatus,
    TranslationConstants, TranslationFileFormat,
    TranslationFormatInvalidInputError, TranslationFormatSyntaxError)
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.translationformat import TranslationMessageData


standardPOFileTopComment = ''' %(languagename)s translation for %(origin)s
 Copyright %(copyright)s %(year)s
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
    implements(IPOTemplate)

    _table = 'POTemplate'

    productseries = ForeignKey(foreignKey='ProductSeries',
        dbName='productseries', notNull=False, default=None)
    priority = IntCol(dbName='priority', notNull=True, default=DEFAULT)
    name = StringCol(dbName='name', notNull=True)
    translation_domain = StringCol(dbName='translation_domain', notNull=True)
    description = StringCol(dbName='description', notNull=False, default=None)
    copyright = StringCol(dbName='copyright', notNull=False, default=None)
    license = IntCol(dbName='license', notNull=False, default=None)
    datecreated = UtcDateTimeCol(dbName='datecreated', default=DEFAULT)
    path = StringCol(dbName='path', notNull=False, default=None)
    source_file = ForeignKey(foreignKey='LibraryFileAlias',
        dbName='source_file', notNull=False, default=None)
    source_file_format = EnumCol(dbName='source_file_format',
        schema=TranslationFileFormat, default=TranslationFileFormat.PO,
        notNull=True)
    iscurrent = BoolCol(dbName='iscurrent', notNull=True, default=True)
    messagecount = IntCol(dbName='messagecount', notNull=True, default=0)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=False, default=None)
    from_sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='from_sourcepackagename', notNull=False, default=None)
    sourcepackageversion = StringCol(dbName='sourcepackageversion',
        notNull=False, default=None)
    distroseries = ForeignKey(foreignKey='DistroSeries',
        dbName='distrorelease', notNull=False, default=None)
    header = StringCol(dbName='header', notNull=False, default=None)
    binarypackagename = ForeignKey(foreignKey='BinaryPackageName',
        dbName='binarypackagename', notNull=False, default=None)
    languagepack = BoolCol(dbName='languagepack', notNull=True, default=False)
    date_last_updated = UtcDateTimeCol(dbName='date_last_updated',
        default=DEFAULT)

    # joins
    pofiles = SQLMultipleJoin('POFile', joinColumn='potemplate')

    # In-memory cache: maps (language code, variant) to list of POFiles
    # translating this template to that language (variant).
    _cached_pofiles_by_language = None

    # In-memory cache: code of last-requested language, and its Language.
    _cached_language_code = None
    _cached_language = None

    def __iter__(self):
        """See `IPOTemplate`."""
        for potmsgset in self.getPOTMsgSets():
            yield potmsgset

    def __getitem__(self, key):
        """See `IPOTemplate`."""
        potmsgset = self.getPOTMsgSetByMsgIDText(key, only_current=True)
        if potmsgset is None:
            raise NotFoundError(key)
        else:
            return potmsgset

    @property
    def displayname(self):
        """See `IPOTemplate`."""
        if self.productseries:
            dn = '%s in %s %s' % (
                self.name,
                self.productseries.product.displayname,
                self.productseries.displayname)
        if self.distroseries:
            dn = '%s in %s %s package "%s"' % (
                self.name,
                self.distroseries.distribution.displayname,
                self.distroseries.displayname,
                self.sourcepackagename.name)
        return dn

    @property
    def title(self):
        """See `IPOTemplate`."""
        if self.productseries:
            title = 'Template "%s" in %s %s' % (
                self.name,
                self.productseries.product.displayname,
                self.productseries.displayname)
        if self.distroseries:
            title = 'Template "%s" in %s %s package "%s"' % (
                self.name,
                self.distroseries.distribution.displayname,
                self.distroseries.displayname,
                self.sourcepackagename.name)
        return title

    @property
    def distribution(self):
        """See `IPOTemplate`."""
        if self.distroseries is not None:
            return self.distroseries.distribution
        else:
            return None

    @property
    def product(self):
        """See `IPOTemplate`."""
        if self.productseries is not None:
            return self.productseries.product
        else:
            return None

    @property
    def translationgroups(self):
        """See `IPOTemplate`."""
        ret = []
        if self.distroseries:
            tg = self.distroseries.distribution.translationgroup
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
        """See `IPOTemplate`."""
        if self.distroseries:
            # in the case of a distro template, use the distro translation
            # permission settings
            return self.distroseries.distribution.translationpermission
        elif self.productseries:
            # for products, use the "most restrictive permission" between
            # project and product.
            return self.productseries.product.aggregatetranslationpermission

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
        elif self.distroseries is not None:
            from canonical.launchpad.database.sourcepackage import \
                SourcePackage
            return SourcePackage(distroseries=self.distroseries,
                sourcepackagename=self.sourcepackagename)
        raise AssertionError('Unknown POTemplate translation target')

    def getHeader(self):
        """See `IPOTemplate`."""
        translation_importer = getUtility(ITranslationImporter)
        format_importer = translation_importer.getTranslationFormatImporter(
            self.source_file_format)
        header = format_importer.getHeaderFromString(self.header)
        header.has_plural_forms = self.hasPluralMessage()
        return header

    def getPOTMsgSetByMsgIDText(self, key, only_current=False, context=None):
        """See `IPOTemplate`."""
        query = 'potemplate = %s' % sqlvalues(self.id)
        if only_current:
            query += ' AND sequence > 0'
        if context is not None:
            query += ' AND context=%s' % sqlvalues(context)
        else:
            query += ' AND context IS NULL'

        # Find a message ID with the given text.
        try:
            pomsgid = POMsgID.byMsgid(key)
        except SQLObjectNotFound:
            return None

        # Find a message set with the given message ID.

        return POTMsgSet.selectOne(query +
            (' AND msgid_singular = %s' % sqlvalues(pomsgid.id)))

    def getPOTMsgSetBySequence(self, sequence):
        """See `IPOTemplate`."""
        assert sequence > 0, ('%r is out of range')

        return POTMsgSet.selectOne("""
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence = %s
            """ % sqlvalues (self.id, sequence))

    def getPOTMsgSets(self, current=True, slice=None):
        """See `IPOTemplate`."""
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

        return results

    def getPOTMsgSetsCount(self, current=True):
        """See `IPOTemplate`."""
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
        """See `IPOTemplate`."""
        return POTMsgSet.selectOne(
            "POTMsgSet.potemplate = %s AND POTMsgSet.id = %s" % sqlvalues(
                self.id, id))

    def languages(self):
        """See `IPOTemplate`."""
        return Language.select("POFile.language = Language.id AND "
                               "Language.code != 'en' AND "
                               "POFile.potemplate = %d AND "
                               "POFile.variant IS NULL" % self.id,
                               clauseTables=['POFile', 'Language'],
                               distinct=True
                               )

    def getPOFileByPath(self, path):
        """See `IPOTemplate`."""
        return POFile.selectOneBy(potemplate=self, path=path)

    def getPOFileByLang(self, language_code, variant=None):
        """See `IPOTemplate`."""
        # Consult cache first.
        language_spec = (language_code, variant)
        if self._cached_pofiles_by_language is None:
            self._cached_pofiles_by_language = {}
        elif language_spec in self._cached_pofiles_by_language:
            # Cache contains a remembered POFile for this language.  Don't do
            # the usual get() followed by "is None"; the dict may contain None
            # values to indicate we looked for a POFile and found none.
            return self._cached_pofiles_by_language[language_spec]

        if variant is None:
            variantspec = 'IS NULL'
        elif isinstance(variant, unicode):
            variantspec = (u'= %s' % quote(variant))
        else:
            raise TypeError('Variant must be None or unicode.')

        self._cached_pofiles_by_language[language_spec] = POFile.selectOne("""
            POFile.potemplate = %d AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            """ % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=['Language'])

        return self._cached_pofiles_by_language[language_spec]

    def messageCount(self):
        """See `IRosettaStats`."""
        return self.messagecount

    def currentCount(self, language=None):
        """See `IRosettaStats`."""
        if language is None:
            return 0
        pofile = self.getPOFileByLang(language)
        if pofile is None:
            return 0
        else:
            return pofile.currentCount()

    def updatesCount(self, language=None):
        """See `IRosettaStats`."""
        if language is None:
            return 0
        pofile = self.getPOFileByLang(language)
        if pofile is None:
            return 0
        else:
            pofile.updatesCount()

    def rosettaCount(self, language=None):
        """See `IRosettaStats`."""
        if language is None:
            return 0
        pofile = self.getPOFileByLang(language)
        if pofile is None:
            return 0
        else:
            pofile.rosettaCount()

    def hasMessageID(self, messageID, context=None):
        """See `IPOTemplate`."""
        results = POTMsgSet.selectBy(potemplate=self, msgid_singular=messageID,
                                     context=context)
        return bool(results)

    def hasPluralMessage(self):
        """See `IPOTemplate`."""
        results = POTMsgSet.select('''
            msgid_plural IS NOT NULL AND
            POTemplate = %s
            ''' % sqlvalues(self))
        return bool(results)

    def export(self):
        """See `IPOTemplate`."""
        translation_exporter = getUtility(ITranslationExporter)
        translation_format_exporter = (
            translation_exporter.getExporterProducingTargetFileFormat(
                self.source_file_format))

        template_file = ITranslationFileData(self)
        exported_file = translation_format_exporter.exportTranslationFiles(
            [template_file])

        try:
            file_content = exported_file.read()
        finally:
            exported_file.close()

        return file_content

    def exportWithTranslations(self):
        """See `IPOTemplate`."""
        translation_exporter = getUtility(ITranslationExporter)
        translation_format_exporter = (
            translation_exporter.getExporterProducingTargetFileFormat(
                self.source_file_format))

        translation_files = [
            ITranslationFileData(pofile)
            for pofile in self.pofiles
            ]
        translation_files.append(ITranslationFileData(self))
        return translation_format_exporter.exportTranslationFiles(
            translation_files)

    def expireAllMessages(self):
        """See `IPOTemplate`."""
        for potmsgset in self:
            potmsgset.sequence = 0

    def _lookupLanguage(self, language_code):
        """Look up named `Language` object, or raise `LanguageNotFound`."""
        # Caches last-requested language to deal with repetitive requests.
        if self._cached_language_code == language_code:
            assert self._cached_language is not None, (
                "Cached None as language in POTemplate.")
            return self._cached_language

        try:
            self._cached_language = Language.byCode(language_code)
        except SQLObjectNotFound:
            self._cached_language_code = None
            self._cached_language = None
            raise LanguageNotFound(language_code)

        self._cached_language_code = language_code
        return self._cached_language

    def newPOFile(self, language_code, variant=None, requester=None):
        """See `IPOTemplate`."""
        # Make sure we don't already have a PO file for this language.
        existingpo = self.getPOFileByLang(language_code, variant)
        assert existingpo is None, (
            'There is already a valid IPOFile (%s)' % existingpo.title)

        # Since we have no PO file for this language yet, create one.
        language = self._lookupLanguage(language_code)

        now = datetime.datetime.now()
        data = {
            'year': now.year,
            'languagename': language.englishname,
            'languagecode': language_code,
            'date': now.isoformat(' '),
            'templatedate': self.datecreated,
            'copyright': '(c) %d Rosetta Contributors and Canonical Ltd'
                         % now.year,
            'nplurals': language.pluralforms or 1,
            'pluralexpr': language.pluralexpression or '0',
            }

        if self.productseries is not None:
            data['origin'] = self.productseries.product.name
        else:
            data['origin'] = self.sourcepackagename.name

        # The default POFile owner is the Rosetta Experts team unless the
        # requester has rights to write into that file.
        dummy_pofile = self.getDummyPOFile(language.code, variant)
        if dummy_pofile.canEditTranslations(requester):
            owner = requester
        else:
            owner = getUtility(ILaunchpadCelebrities).rosetta_expert

        if variant is None:
            path_variant = ''
        else:
            path_variant = '@%s' % variant

        # By default, we set as the path directory the same as the POTemplate
        # one and set as the file name the translation domain + language.
        potemplate_dir = os.path.dirname(self.path)
        path = '%s/%s-%s%s.po' % (potemplate_dir,
            self.translation_domain, language.code, path_variant)

        pofile = POFile(
            potemplate=self,
            language=language,
            topcomment=standardPOFileTopComment % data,
            header=standardPOFileHeader % data,
            fuzzyheader=True,
            owner=owner,
            variant=variant,
            path=path)

        # Update cache to reflect the change.
        self._cached_pofiles_by_language[language_code, variant] = pofile

        # Store the changes.
        flush_database_updates()

        return pofile

    def getDummyPOFile(self, language_code, variant=None, requester=None):
        """See `IPOTemplate`."""
        # see if a valid one exists.
        existingpo = self.getPOFileByLang(language_code, variant)
        assert existingpo is None, (
            'There is already a valid IPOFile (%s)' % existingpo.title)

        language = self._lookupLanguage(language_code)
        return DummyPOFile(self, language, owner=requester)

    def createMessageSetFromMessageID(self, msgid_singular, msgid_plural,
                                      context=None):
        """See `IPOTemplate`."""
        messageSet = POTMsgSet(
            context=context,
            msgid_singular=msgid_singular,
            msgid_plural=msgid_plural,
            sequence=0,
            potemplate=self,
            commenttext=None,
            filereferences=None,
            sourcecomment=None,
            flagscomment=None)
        return messageSet

    def createMessageSetFromText(self, singular_text, plural_text,
                                 context=None):
        """See `IPOTemplate`."""
        try:
            msgid_singular = POMsgID.byMsgid(singular_text)
            msgid_plural = None
            if plural_text is not None:
                try:
                    msgid_plural = POMsgID.byMsgid(plural_text)
                except SQLObjectNotFound:
                    msgid_plural = POMsgID(msgid=singular_text)
        except SQLObjectNotFound:
            # If there are no existing message ids, create a new one.
            # We do not need to check whether there is already a message set
            # with the given text in this template.
            msgid_singular = POMsgID(msgid=singular_text)
        else:
            assert not self.hasMessageID(msgid_singular, context), (
                "There is already a message set for this template, file and"
                " primary msgid and context '%r'" % context)

        return self.createMessageSetFromMessageID(msgid_singular, msgid_plural,
                                                  context)

    def invalidateCache(self):
        """See `IPOTemplate`."""
        for pofile in self.pofiles:
            pofile.invalidateCache()

    def getNextToImport(self):
        """See `IPOTemplate`."""
        flush_database_updates()
        return TranslationImportQueueEntry.selectFirstBy(
                potemplate=self,
                status=RosettaImportStatus.APPROVED,
                orderBy='dateimported')

    def importFromQueue(self, logger=None):
        """See `IPOTemplate`."""
        entry_to_import = self.getNextToImport()

        if entry_to_import is None:
            # There is no new import waiting for being imported.
            return

        translation_importer = getUtility(ITranslationImporter)

        subject = 'Translation template import - %s' % self.displayname
        template_mail = 'poimport-template-confirmation.txt'
        try:
            translation_importer.importFile(entry_to_import, logger)
        except (TranslationFormatSyntaxError,
                TranslationFormatInvalidInputError):
            if logger:
                logger.warning(
                    'We got an error importing %s', self.title, exc_info=1)
            subject = 'Import problem - %s' % self.displayname
            template_mail = 'poimport-syntax-error.txt'
            entry_to_import.status = RosettaImportStatus.FAILED

        replacements = {
            'dateimport': entry_to_import.dateimported.strftime('%F %R%z'),
            'elapsedtime': entry_to_import.getElapsedTimeText(),
            'file_link': entry_to_import.content.http_url,
            'import_title': 'translation templates for %s' % self.displayname,
            'importer': entry_to_import.importer.displayname,
            'template': self.displayname
            }

        # Send email: confirmation or error.
        template = helpers.get_email_template(template_mail)
        message = template % replacements

        fromaddress = config.rosetta.rosettaadmin.email
        toaddress = helpers.contactEmailAddresses(entry_to_import.importer)

        simple_sendmail(fromaddress,
            toaddress,
            subject,
            MailWrapper().format(message))

        if entry_to_import.status == RosettaImportStatus.FAILED:
            # Give up on this file.
            return

        # The import has been done, we mark it that way.
        entry_to_import.status = RosettaImportStatus.IMPORTED
        # And add karma to the importer if it's not imported automatically
        # (all automatic imports come from the rosetta expert team).
        rosetta_expert = getUtility(ILaunchpadCelebrities).rosetta_expert
        if entry_to_import.importer.id != rosetta_expert.id:
            # The admins should not get karma.
            entry_to_import.importer.assignKarma(
                'translationtemplateimport',
                product=self.product,
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename)

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


class POTemplateSubset:
    implements(IPOTemplateSubset)

    def __init__(self, sourcepackagename=None, from_sourcepackagename=None,
                 distroseries=None, productseries=None):
        """Create a new `POTemplateSubset` object.

        The set of POTemplate depends on the arguments you pass to this
        constructor. The sourcepackagename, from_sourcepackagename,
        distroseries and productseries are just filters for that set.
        """
        self.sourcepackagename = sourcepackagename
        self.distroseries = distroseries
        self.productseries = productseries
        self.clausetables = []
        self.orderby = []

        assert productseries is None or distroseries is None, (
            'A product series must not be used with a distro series.')

        assert productseries is not None or distroseries is not None, (
            'Either productseries or distroseries must be not None.')

        if productseries is not None:
            self.query = ('POTemplate.productseries = %s' %
                sqlvalues(productseries.id))
        elif distroseries is not None and from_sourcepackagename is not None:
            self.query = ('POTemplate.from_sourcepackagename = %s AND'
                          ' POTemplate.distrorelease = %s ' %
                            sqlvalues(from_sourcepackagename.id,
                                      distroseries.id))
            self.sourcepackagename = from_sourcepackagename
        elif distroseries is not None and sourcepackagename is not None:
            self.query = ('POTemplate.sourcepackagename = %s AND'
                          ' POTemplate.distrorelease = %s ' %
                            sqlvalues(sourcepackagename.id, distroseries.id))
        else:
            self.query = (
                'POTemplate.distrorelease = DistroRelease.id AND'
                ' DistroRelease.id = %s' % sqlvalues(distroseries.id))
            self.orderby.append('DistroRelease.name')
            self.clausetables.append('DistroRelease')

        # Finally, we sort the query by its path in all cases.
        self.orderby.append('POTemplate.path')

    def __iter__(self):
        """See `IPOTemplateSubset`."""
        res = POTemplate.select(self.query, clauseTables=self.clausetables,
                                orderBy=self.orderby)

        for potemplate in res:
            yield potemplate

    def __len__(self):
        """See `IPOTemplateSubset`."""
        res = POTemplate.select(self.query, clauseTables=self.clausetables)
        return res.count()

    def __getitem__(self, name):
        """See `IPOTemplateSubset`."""
        potemplate = self.getPOTemplateByName(name)
        if potemplate is None:
            raise NotFoundError(name)
        else:
            return potemplate

    @property
    def title(self):
        """See `IPOTemplateSubset`."""
        titlestr = ''
        if self.distroseries:
            titlestr += ' ' + self.distroseries.displayname
        if self.sourcepackagename:
            titlestr += ' ' + self.sourcepackagename.name
        if self.productseries:
            titlestr += ' '
            titlestr += self.productseries.displayname
        return titlestr

    def new(self, name, path, owner):
        """See `IPOTemplateSubset`."""
        return POTemplate(name=name,
                          sourcepackagename=self.sourcepackagename,
                          distroseries=self.distroseries,
                          productseries=self.productseries,
                          path=path,
                          owner=owner)

    def getPOTemplateByName(self, name):
        """See `IPOTemplateSubset`."""
        queries = [self.query]
        clausetables = list(self.clausetables)
        queries.append('POTemplate.name = %s' % sqlvalues(name))

        return POTemplate.selectOne(' AND '.join(queries),
            clauseTables=clausetables)

    def getPOTemplateByTranslationDomain(self, translation_domain):
        """See `IPOTemplateSubset`."""
        queries = [self.query]
        clausetables = list(self.clausetables)

        queries.append('POTemplate.translation_domain = %s' % sqlvalues(
            translation_domain))

        return POTemplate.selectOne(' AND '.join(queries),
            clauseTables=clausetables)

    def getPOTemplateByPath(self, path):
        """See `IPOTemplateSubset`."""
        query = '%s AND POTemplate.path = %s' % (self.query, quote(path))

        return POTemplate.selectOne(query, clauseTables=self.clausetables)

    def getAllOrderByDateLastUpdated(self):
        """See `IPOTemplateSet`."""
        query = []
        if self.productseries is not None:
            query.append('productseries = %s' % sqlvalues(self.productseries))
        if self.distroseries is not None:
            query.append('distrorelease = %s' % sqlvalues(self.distroseries))
        if self.sourcepackagename is not None:
            query.append('sourcepackagename = %s' % sqlvalues(
                self.sourcepackagename))

        return POTemplate.select(
            ' AND '.join(query), orderBy=['-date_last_updated'])

    def getClosestPOTemplate(self, path):
        """See `IPOTemplateSubset`."""
        if path is None:
            return None

        closest_template = None
        closest_template_path_length = 0
        repeated = False
        for template in self:
            template_path_length = len(
                os.path.commonprefix([template.path, path]))
            if template_path_length > closest_template_path_length:
                # This template is more near than the one we got previously
                closest_template = template
                closest_template_path_length = template_path_length
                repeated = False
            elif template_path_length == closest_template_path_length:
                # We found two templates with the same length, we note that
                # fact, if we don't get a better template, we ignore them and
                # leave it to the admins.
                repeated = True
        if repeated:
            return None
        else:
            return closest_template


class POTemplateSet:
    implements(IPOTemplateSet)

    def __iter__(self):
        """See `IPOTemplateSet`."""
        res = POTemplate.select()
        for potemplate in res:
            yield potemplate

    def getByIDs(self, ids):
        """See `IPOTemplateSet`."""
        values = ",".join(sqlvalues(*ids))
        return POTemplate.select("POTemplate.id in (%s)" % values,
            prejoins=["productseries", "distroseries", "sourcepackagename"],
            orderBy=["POTemplate.id"])

    def getAllByName(self, name):
        """See `IPOTemplateSet`."""
        return POTemplate.selectBy(name=name, orderBy=['name', 'id'])

    def getAllOrderByDateLastUpdated(self):
        """See `IPOTemplateSet`."""
        return POTemplate.select(orderBy=['-date_last_updated'])

    def getSubset(self, distroseries=None, sourcepackagename=None,
                  productseries=None):
        """See `IPOTemplateSet`."""
        return POTemplateSubset(
            distroseries=distroseries,
            sourcepackagename=sourcepackagename,
            productseries=productseries)

    def getSubsetFromImporterSourcePackageName(self, distroseries,
        sourcepackagename):
        """See `IPOTemplateSet`."""
        if distroseries is None or sourcepackagename is None:
            raise AssertionError(
                'distroseries and sourcepackage must be not None.')

        return POTemplateSubset(
            distroseries=distroseries,
            sourcepackagename=sourcepackagename)

    def getPOTemplateByPathAndOrigin(self, path, productseries=None,
        distroseries=None, sourcepackagename=None):
        """See `IPOTemplateSet`."""
        if productseries is not None:
            return POTemplate.selectOne('''
                    POTemplate.productseries = %s AND
                    POTemplate.path = %s''' % sqlvalues(
                        productseries.id,
                        path)
                    )
        elif sourcepackagename is not None:
            # The POTemplate belongs to a distribution and it could come from
            # another package that the one it's linked at the moment so we
            # first check to find it at IPOTemplate.from_sourcepackagename
            potemplate = POTemplate.selectOne('''
                    POTemplate.distrorelease = %s AND
                    POTemplate.from_sourcepackagename = %s AND
                    POTemplate.path = %s''' % sqlvalues(
                        distroseries.id,
                        sourcepackagename.id,
                        path)
                    )
            if potemplate is not None:
                # There is no potemplate in that 'path' and
                # 'from_sourcepackagename' so we do a search using the usual
                # sourcepackagename.
                return potemplate

            return POTemplate.selectOne('''
                    POTemplate.distrorelease = %s AND
                    POTemplate.sourcepackagename = %s AND
                    POTemplate.path = %s''' % sqlvalues(
                        distroseries.id,
                        sourcepackagename.id,
                        path)
                    )
        else:
            raise AssertionError(
                'Either productseries or sourcepackagename arguments must be'
                ' not None.')


class POTemplateToTranslationFileDataAdapter:
    """Adapter from `IPOTemplate` to `ITranslationFileData`."""
    implements(ITranslationFileData)

    def __init__(self, potemplate):
        self._potemplate = potemplate
        self.messages = self._getMessages()

    @cachedproperty
    def path(self):
        """See `ITranslationFileData`."""
        return self._potemplate.path

    @cachedproperty
    def translation_domain(self):
        """See `ITranslationFileData`."""
        return self._potemplate.translation_domain

    @property
    def is_template(self):
        """See `ITranslationFileData`."""
        return True

    @property
    def language_code(self):
        """See `ITraslationFile`."""
        return None

    @cachedproperty
    def header(self):
        """See `ITranslationFileData`."""
        return self._potemplate.getHeader()

    def _getMessages(self):
        """Return a list of `ITranslationMessageData`."""
        potemplate = self._potemplate
        # Get all rows related to this file. We do this to speed the export
        # process so we have a single DB query to fetch all needed
        # information.
        rows = getUtility(IVPOTExportSet).get_potemplate_rows(potemplate)

        messages = []

        for row in rows:
            assert row.potemplate == potemplate, (
                'Got a row for a different IPOTemplate.')

            # Skip messages which aren't anymore in the PO template.
            if row.sequence == 0:
                continue

            # Create new message set
            msgset = TranslationMessageData()
            msgset.sequence = row.sequence
            msgset.obsolete = False
            msgset.msgid_singular = row.msgid_singular
            msgset.msgid_plural = row.msgid_plural
            msgset.context = row.context
            msgset.comment = row.comment_text
            msgset.source_comment = row.source_comment
            msgset.file_references = row.file_references

            if row.flags_comment:
                msgset.flags = set([
                    flag.strip()
                    for flag in row.flagscomment.split(',')
                    if flag
                    ])

            # Store sequences so we can detect later whether we changed the
            # message.
            sequence = row.sequence

        return messages
