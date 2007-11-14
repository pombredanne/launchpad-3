# Copyright 2005-2007 Canonical Ltd. All rights reserved.

__metaclass__ = type
__all__ = [
    'HasTranslationImportsMixin',
    'TranslationImportQueueEntry',
    'TranslationImportQueue'
    ]

import tarfile
import os.path
import datetime
import re
import pytz
from StringIO import StringIO
from zope.interface import implements
from zope.component import getUtility
from sqlobject import SQLObjectNotFound, StringCol, ForeignKey, BoolCol

from canonical.database.sqlbase import quote_like, SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces import (
    IDistribution, IDistroSeries, IHasTranslationImports, ILanguageSet,
    IPerson, IPOFileSet, IPOTemplateSet, IProduct, IProductSeries,
    ISourcePackage, ITranslationImporter, ITranslationImportQueue,
    ITranslationImportQueueEntry, NotFoundError, RosettaImportStatus,
    TranslationFileFormat)
from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.database.pillar import pillar_sort_key


# Number of days when the DELETED and IMPORTED entries are removed from the
# queue.
DAYS_TO_KEEP = 3

class TranslationImportQueueEntry(SQLBase):
    implements(ITranslationImportQueueEntry)

    _table = 'TranslationImportQueueEntry'

    path = StringCol(dbName='path', notNull=True)
    content = ForeignKey(foreignKey='LibraryFileAlias', dbName='content',
        notNull=False)
    importer = ForeignKey(foreignKey='Person', dbName='importer',
        notNull=True)
    dateimported = UtcDateTimeCol(dbName='dateimported', notNull=True,
        default=DEFAULT)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=False, default=None)
    distroseries = ForeignKey(foreignKey='DistroSeries',
        dbName='distroseries', notNull=False, default=None)
    productseries = ForeignKey(foreignKey='ProductSeries',
        dbName='productseries', notNull=False, default=None)
    is_published = BoolCol(dbName='is_published', notNull=True)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile',
        notNull=False, default=None)
    potemplate = ForeignKey(foreignKey='POTemplate',
        dbName='potemplate', notNull=False, default=None)
    format = EnumCol(dbName='format', schema=TranslationFileFormat,
        default=TranslationFileFormat.PO, notNull=True)
    status = EnumCol(dbName='status', notNull=True,
        schema=RosettaImportStatus, default=RosettaImportStatus.NEEDS_REVIEW)
    date_status_changed = UtcDateTimeCol(dbName='date_status_changed',
        notNull=True, default=DEFAULT)


    @property
    def sourcepackage(self):
        """See ITranslationImportQueueEntry."""
        from canonical.launchpad.database import SourcePackage

        if self.sourcepackagename is None or self.distroseries is None:
            return None

        return SourcePackage(self.sourcepackagename, self.distroseries)

    @property
    def guessed_potemplate(self):
        """See ITranslationImportQueueEntry."""
        if self.path != 'en-US.xpi':
            assert self.path.endswith('.pot'), (
                "We cannot handle the file %s here." % self.path)

        # It's an IPOTemplate
        potemplate_set = getUtility(IPOTemplateSet)
        return potemplate_set.getPOTemplateByPathAndOrigin(
            self.path, productseries=self.productseries,
            distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename)

    @property
    def _guessed_potemplate_for_pofile_from_path(self):
        """Return an IPOTemplate that we think is related to this entry.

        We get it based on the path of the entry and the IPOTemplate's one
        so if both are on the same directory and there are no others
        IPOTemplates on the same directory, we have a winner.
        """
        assert self.path.endswith('.po'), (
            "We cannot handle the file %s here." % self.path)
        potemplateset = getUtility(IPOTemplateSet)
        translationimportqueue = getUtility(ITranslationImportQueue)
        subset = potemplateset.getSubset(
            distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename,
            productseries=self.productseries)
        entry_dirname = os.path.dirname(self.path)
        guessed_potemplate = None
        for potemplate in subset:
            if guessed_potemplate is not None:
                # We already got a winner, should check if we could have
                # another one, which means we cannot be sure which one is the
                # right one.
                if (os.path.dirname(guessed_potemplate.path) ==
                    os.path.dirname(potemplate.path)):
                    # Two matches, cannot be sure which one is the good one.
                    return None
                else:
                    # Current potemplate is in other directory, need to check
                    # the next.
                    continue
            elif entry_dirname == os.path.dirname(potemplate.path):
                # We have a match; we can't stop checking, though, because
                # there may be other matches.
                guessed_potemplate = potemplate

        if guessed_potemplate is None:
            return None

        # We have a winner, but to be 100% sure, we should not have
        # a .pot file pending of being imported in our queue.
        if self.productseries is not None:
            target = self.productseries
        else:
            target = self.sourcepackage

        entries = translationimportqueue.getAllEntries(
            target=target, file_extension='.pot')

        for entry in entries:
            if (os.path.dirname(entry.path) == os.path.dirname(
                guessed_potemplate.path) and
                entry.status not in (
                RosettaImportStatus.IMPORTED, RosettaImportStatus.DELETED)):
                # There is a .pot entry pending to be imported that has the
                # same path.
                return None

        return guessed_potemplate

    @property
    def _guessed_pofile_from_path(self):
        """Return an IPOFile that we think is related to this entry.

        We get it based on the path it's stored or None.
        """
        pofile_set = getUtility(IPOFileSet)
        return pofile_set.getPOFileByPathAndOrigin(
            self.path, productseries=self.productseries,
            distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename)

    @property
    def guessed_language(self):
        """See ITranslationImportQueueEntry."""
        filename = os.path.basename(self.path)
        guessed_language, file_ext = os.path.splitext(filename)
        if file_ext != '.po':
            # The filename does not follows the pattern 'LANGCODE.po'
            # so we cannot guess its language.
            return None

        return guessed_language

    @property
    def import_into(self):
        """See ITranslationImportQueueEntry."""
        if self.pofile is not None:
            # The entry has an IPOFile associated where it should be imported.
            return self.pofile
        elif (self.potemplate is not None and
              (self.path.endswith('.pot') or self.path == 'en-US.xpi')):
            # The entry has an IPOTemplate associated where it should be
            # imported.
            return self.potemplate
        else:
            # We don't know where this entry should be imported.
            return None

    def _get_pofile_from_language(self, lang_code, translation_domain,
        sourcepackagename=None):
        """Return an IPOFile for the given language and domain.

        :arg lang_code: The language code we are interested on.
        :arg translation_domain: The translation domain for the given
            language.
        :arg sourcepackagename: The ISourcePackageName that uses this
            translation or None if we don't know it.
        """
        assert (lang_code is not None and translation_domain is not None) , (
            "lang_code and translation_domain cannot be None")

        language_set = getUtility(ILanguageSet)
        (language, variant) = language_set.getLanguageAndVariantFromString(
            lang_code)

        if language is None or not language.visible:
            # Either we don't know the language or the language is hidden by
            # default what means that we got a bad import and that should be
            # reviewed by someone before importing. The 'visible' check is to
            # prevent the import of languages like 'es_ES' or 'fr_FR' instead
            # of just 'es' or 'fr'.
            return None

        potemplateset = getUtility(IPOTemplateSet)

        # Let's try first the sourcepackagename or productseries where the
        # translation comes from.
        potemplate_subset = potemplateset.getSubset(
            distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename,
            productseries=self.productseries)
        potemplate = potemplate_subset.getPOTemplateByTranslationDomain(
            translation_domain)

        if (potemplate is None and (sourcepackagename is None or
            self.sourcepackagename.name != sourcepackagename.name)):
            # The source package from where this translation doesn't have the
            # template that this translation needs it, and thus, we look for
            # it in a different source package as a second try. To do it, we
            # need to get a subset of all packages in current distro series.
            potemplate_subset = potemplateset.getSubset(
                distroseries=self.distroseries)
            potemplate = potemplate_subset.getPOTemplateByTranslationDomain(
                translation_domain)

        if potemplate is None:
            # The potemplate is not yet imported, we cannot attach this .po
            # file.
            return None

        # Get or create an IPOFile based on the info we guess.
        pofile = potemplate.getPOFileByLang(language.code, variant=variant)
        if pofile is None:
            pofile = potemplate.newPOFile(
                language.code, variant=variant, requester=self.importer)

        if self.is_published and pofile.path != self.path:
            # This entry comes from upstream, which means that the path we got
            # is exactly the right one. If it's different from what pofile
            # has, that would mean that either the entry changed its path
            # since previous upload or that we had to guess it and now that we
            # got the right path, we should fix it.
            pofile.path = self.path

        if (sourcepackagename is None and
            potemplate.sourcepackagename is not None):
            # We didn't know the sourcepackagename when we called this method,
            # but know, we know it.
            sourcepackagename = potemplate.sourcepackagename

        if (self.sourcepackagename is not None and
            self.sourcepackagename.name != sourcepackagename.name):
            # We need to note the sourcepackagename from where this entry came
            # because it's different from the place where we are going to
            # import it.
            pofile.from_sourcepackagename = self.sourcepackagename

        return pofile

    def getGuessedPOFile(self):
        """See ITranslationImportQueueEntry."""
        assert self.path.endswith('.po'), (
            "We cannot handle the file %s here." % self.path)
        if self.potemplate is None:
            # We don't have the IPOTemplate object associated with this entry.
            # Try to guess it from the file path.
            pofile = self._guessed_pofile_from_path
            if pofile is not None:
                # We were able to guess an IPOFile.
                return pofile

            # Multi directory trees layout are non standard layouts where the
            # .pot file and its .po files are stored in different directories.
            pofile = self._guess_multiple_directories_with_pofile()
            if pofile is not None:
                # This entry is fits our multi directory trees layout and we
                # found a place where it should be imported.
                return pofile

            # We were not able to find an IPOFile based on the path, try
            # to guess an IPOTemplate before giving up.
            potemplate = self._guessed_potemplate_for_pofile_from_path
            if potemplate is None:
                # No way to guess anything...
                return None
            # We got the potemplate, try to guess the language from
            # the info we have.
            self.potemplate = potemplate

        # We know the IPOTemplate associated with this entry so we can try to
        # detect the right IPOFile.
        # Let's try to guess the language.
        filename = os.path.basename(self.path)
        guessed_language, file_ext = os.path.splitext(filename)
        if file_ext != '.po':
            # The filename does not follows the pattern 'LANGCODE.po'
            # so we cannot guess it as a language, fallback to get it based
            # on the path.
            return self._guessed_pofile_from_path

        return self._get_pofile_from_language(guessed_language,
            self.potemplate.potemplatename.translationdomain,
            sourcepackagename=self.potemplate.sourcepackagename)

    def _guess_multiple_directories_with_pofile(self):
        """Return an IPOFile that we think is related to this entry or None.

        Multi directory trees layout are non standard layouts where the .pot
        file and its .po files are stored in different directories

        The know layouts are:

        DIRECTORY/TRANSLATION_DOMAIN.pot
        DIRECTORY/LANG_CODE/TRANSLATION_DOMAIN.po

        or

        DIRECTORY/TRANSLATION_DOMAIN.pot
        DIRECTORY/LANG_CODE/messages/TRANSLATION_DOMAIN.po

        or

        DIRECTORY/TRANSLATION_DOMAIN.pot
        DIRECTORY/LANG_CODE/LC_MESSAGES/TRANSLATION_DOMAIN.po

        or

        DIRECTORY/TRANSLATION_DOMAIN.pot
        DIRECTORY/LANG_CODE/LANG_CODE.po

        where DIRECTORY would be any path, even '', LANG_CODE is a language
        code and TRANSLATION_DOMAIN the translation domain is the one used for
        that .po file.

        If this isn't enough, there are some packages that have a non standard
        layout where the .pot files are stored inside the sourcepackage with
        the binaries that will use it and the translations are stored in
        external packages following the same language pack ideas that we use
        with Ubuntu.

        This layout breaks completely Rosetta because we don't have a way
        to link the .po and .pot files coming from different packages. The
        solution we take is to look for the translation domain across the
        whole distro series. In the concrete case of KDE language packs, they
        have the sourcepackagename following the pattern 'kde-i18n-LANGCODE'.
        """
        assert self.path.endswith('.po'), (
            "We cannot handle the file %s here." % self.path)

        if self.productseries is not None:
            # This method only works for sourcepackages. It makes no sense use
            # it with productseries.
            return None

        if self.sourcepackagename.name.startswith('kde-i18n-'):
            # We need to extract the language information from the package
            # name

            # Here we have the set of language codes that have special meanings.
            lang_mapping = {
                'engb': 'en_GB',
                'ptbr': 'pt_BR',
                'srlatn': 'sr@Latn',
                'zhcn': 'zh_CN',
                'zhtw': 'zh_TW',
                }

            lang_code = self.sourcepackagename.name[len('kde-i18n-'):]
            if lang_code in lang_mapping:
                lang_code = lang_mapping[lang_code]
        elif (self.sourcepackagename.name == 'koffice-l10n' and
              self.path.startswith('koffice-i18n-')):
            # This package has the language information included as part of a
            # directory: koffice-i18n-LANG_CODE-VERSION
            # Let's get the root directory that has the language information.
            lang_directory = self.path.split('/')[0]
            # Extract the language information.
            match = re.match('koffice-i18n-(\S+)-(\S+)', self.path)
            if match is None:
                # No idea what to do with this.
                return None
            lang_code = match.group(1)
        else:
            # In this case, we try to get the language information from the
            # path name.
            dir_path = os.path.dirname(self.path)
            dir_name = os.path.basename(dir_path)

            if dir_name == 'messages' or dir_name == 'LC_MESSAGES':
                # We have another directory between the language code directory
                # and the filename (second and third case).
                dir_path = os.path.dirname(dir_path)
                lang_code = os.path.basename(dir_path)
            else:
                # The .po file is stored inside the directory with the language
                # code as its name or an unsupported layout.
                lang_code = dir_name

            if lang_code is None:
                return None

        basename = os.path.basename(self.path)
        filename, file_ext = os.path.splitext(basename)

        # Let's check if whether the filename is a valid language.
        language_set = getUtility(ILanguageSet)
        (language, variant) = language_set.getLanguageAndVariantFromString(
            filename)

        if language is None:
            # The filename is not a valid language, so let's try it as a
            # translation domain.
            translation_domain = filename
        elif filename == lang_code:
            # The filename is a valid language so we need to look for the
            # template nearest to this pofile to link with it.
            potemplateset = getUtility(IPOTemplateSet)
            potemplate_subset = potemplateset.getSubset(
                distroseries=self.distroseries,
                sourcepackagename=self.sourcepackagename)
            potemplate = potemplate_subset.getClosestPOTemplate(self.path)
            if potemplate is None:
                # We were not able to find such template, someone should
                # review it manually.
                return None
            translation_domain = potemplate.potemplatename.translationdomain
        else:
            # The guessed language from the directory doesn't math the
            # language from the filename. Leave it for an admin.
            return None

        if (self.sourcepackagename.name in ('k3b-i18n', 'koffice-l10n') or
            self.sourcepackagename.name.startswith('kde-i18n-')):
            # K3b and official KDE packages store translations and code in
            # different packages, so we don't know the sourcepackagename that
            # use the translations.
            return self._get_pofile_from_language(
                lang_code, translation_domain)
        else:
            # We assume that translations and code are together in the same
            # package.
            return self._get_pofile_from_language(
                lang_code, translation_domain,
                sourcepackagename=self.sourcepackagename)

    def getFileContent(self):
        """See ITranslationImportQueueEntry."""
        client = getUtility(ILibrarianClient)
        return client.getFileByAlias(self.content.id).read()

    def getTemplatesOnSameDirectory(self):
        """See ITranslationImportQueueEntry."""
        path = os.path.dirname(self.path)
        query = ("path LIKE %s || '%%.pot' AND id <> %s" %
                 (quote_like(path), self.id))
        if self.distroseries is not None:
            query += ' AND distroseries = %s' % sqlvalues(
                self.distroseries)
        if self.sourcepackagename is not None:
            query += ' AND sourcepackagename = %s' % sqlvalues(
                self.sourcepackagename)
        if self.productseries is not None:
            query += ' AND productseries = %s' % sqlvalues(
                self.productseries)

        return TranslationImportQueueEntry.select(query)

    def getElapsedTimeText(self):
        """See ITranslationImportQueue."""
        UTC = pytz.timezone('UTC')
        # XXX: Carlos Perello Marin 2005-06-29: This code should be using the
        # solution defined by PresentingLengthsOfTime spec when it's
        # implemented.
        elapsedtime = (
            datetime.datetime.now(UTC) - self.dateimported)
        elapsedtime_text = ''
        hours = elapsedtime.seconds / 3600
        minutes = (elapsedtime.seconds % 3600) / 60
        if elapsedtime.days > 0:
            elapsedtime_text += '%d days ' % elapsedtime.days
        if hours > 0:
            elapsedtime_text += '%d hours ' % hours
        if minutes > 0:
            elapsedtime_text += '%d minutes ' % minutes

        if len(elapsedtime_text) > 0:
            elapsedtime_text += 'ago'
        else:
            elapsedtime_text = 'just requested'

        return elapsedtime_text


class TranslationImportQueue:
    implements(ITranslationImportQueue)

    def __iter__(self):
        """See ITranslationImportQueue."""
        return iter(self.getAllEntries())

    def __getitem__(self, id):
        """See ITranslationImportQueue."""
        try:
            idnumber = int(id)
        except ValueError:
            raise NotFoundError(id)

        entry = self.get(idnumber)

        if entry is None:
            # The requested entry does not exist.
            raise NotFoundError(str(id))

        return entry

    def entryCount(self):
        """See ITranslationImportQueue."""
        return TranslationImportQueueEntry.select().count()

    def iterNeedsReview(self):
        """See ITranslationImportQueue."""
        return iter(TranslationImportQueueEntry.selectBy(
            status=RosettaImportStatus.NEEDS_REVIEW,
            orderBy=['dateimported']))

    def addOrUpdateEntry(self, path, content, is_published, importer,
        sourcepackagename=None, distroseries=None, productseries=None,
        potemplate=None, pofile=None, format=None):
        """See ITranslationImportQueue."""
        if ((sourcepackagename is not None or distroseries is not None) and
            productseries is not None):
            raise AssertionError(
                'The productseries argument cannot be not None if'
                ' sourcepackagename or distroseries is also not None.')
        if (sourcepackagename is None and distroseries is None and
            productseries is None):
            raise AssertionError('Any of sourcepackagename, distroseries or'
                ' productseries must be not None.')

        if content is None or content == '':
            raise AssertionError('The content cannot be empty')

        if path is None or path == '':
            raise AssertionError('The path cannot be empty')

        filename = os.path.basename(path)
        root, ext = os.path.splitext(filename)
        translation_importer = getUtility(ITranslationImporter)
        if format is None:
            # Get it based on the file extension and file content.
            format = translation_importer.getTranslationFileFormat(
                ext, content)
        format_importer = translation_importer.getTranslationFormatImporter(
            format)

        # Upload the file into librarian.
        size = len(content)
        file = StringIO(content)
        client = getUtility(ILibrarianClient)
        alias = client.addFile(
            name=filename, size=size, file=file,
            contentType=format_importer.content_type)

        # Check if we got already this request from this user.
        queries = ['TranslationImportQueueEntry.path = %s' % sqlvalues(path)]
        queries.append(
            'TranslationImportQueueEntry.importer = %s' % sqlvalues(importer))
        if potemplate is not None:
            queries.append(
                'TranslationImportQueueEntry.potemplate = %s' % sqlvalues(
                    potemplate))
        if pofile is not None:
            queries.append(
                'TranslationImportQueueEntry.pofile = %s' % sqlvalues(pofile))
        if sourcepackagename is not None:
            # The import is related with a sourcepackage and a distribution.
            queries.append(
                'TranslationImportQueueEntry.sourcepackagename = %s' % (
                    sqlvalues(sourcepackagename)))
            queries.append(
                'TranslationImportQueueEntry.distroseries = %s' % sqlvalues(
                    distroseries))
        else:
            # The import is related with a productseries.
            assert productseries is not None, (
                'sourcepackagename and productseries cannot be both None at'
                ' the same time.')

            queries.append(
                'TranslationImportQueueEntry.productseries = %s' % sqlvalues(
                    productseries))

        entry = TranslationImportQueueEntry.selectOne(' AND '.join(queries))

        if entry is not None:
            # It's an update.
            entry.content = alias
            entry.is_published = is_published
            if potemplate is not None:
                # Only set the linked IPOTemplate object if it's not None.
                entry.potemplate = potemplate

            if pofile is not None:
                # Set always the IPOFile link if we know it.
                entry.pofile = pofile

            if entry.status == RosettaImportStatus.IMPORTED:
                # The entry was already imported, so we need to update its
                # dateimported field so it doesn't get preference over old
                # entries.
                entry.dateimported = UTC_NOW

            if (entry.status == RosettaImportStatus.DELETED or
                entry.status == RosettaImportStatus.FAILED or
                entry.status == RosettaImportStatus.IMPORTED):
                # We got an update for this entry. If the previous import is
                # deleted or failed or was already imported we should retry
                # the import now, just in case it can be imported now.
                entry.status = RosettaImportStatus.NEEDS_REVIEW

            entry.date_status_changed = UTC_NOW
            entry.format = format
            entry.sync()
        else:
            # It's a new row.
            entry = TranslationImportQueueEntry(path=path, content=alias,
                importer=importer, sourcepackagename=sourcepackagename,
                distroseries=distroseries, productseries=productseries,
                is_published=is_published, potemplate=potemplate,
                pofile=pofile, format=format)

        return entry

    def addOrUpdateEntriesFromTarball(self, content, is_published, importer,
        sourcepackagename=None, distroseries=None, productseries=None,
        potemplate=None):
        """See ITranslationImportQueue."""
        # We need to know if we are handling .bz2 files, we could use the
        # python2.4-magic but it makes no sense to add that dependency just
        # for this check as the .bz2 files start with the 'BZh' string.
        if content.startswith('BZh'):
            # Workaround for the bug #1982. Python's bz2 support is not able
            # to handle external file objects.
            tarball = tarfile.open('', 'r|bz2', StringIO(content))
        else:
            tarball = tarfile.open('', 'r', StringIO(content))

        num_files = 0
        for tarinfo in tarball:
            filename = tarinfo.name
            # XXX: JeroenVermeulen 2007-06-18 bug=121798:
            # Work multi-format support in.
            # For now we're only interested in PO and POT files.  We skip
            # "dotfiles," i.e. files whose names start with a dot, and we
            # ignore anything that isn't a file (such as directories,
            # symlinks, and above all, device files which could cause some
            # serious security headaches).
            looks_useful = (
                tarinfo.isfile() and
                not filename.startswith('.') and
                (filename.endswith('.pot') or filename.endswith('.po')))
            if looks_useful:
                file_content = tarball.extractfile(tarinfo).read()
                if len(file_content) > 0:
                    self.addOrUpdateEntry(
                        tarinfo.name, file_content, is_published, importer,
                        sourcepackagename=sourcepackagename,
                        distroseries=distroseries,
                        productseries=productseries,
                        potemplate=potemplate)
                    num_files += 1

        tarball.close()

        return num_files

    def get(self, id):
        """See ITranslationImportQueue."""
        try:
            return TranslationImportQueueEntry.get(id)
        except SQLObjectNotFound:
            return None

    def _getQueryByFiltering(self, target=None, status=None,
                             file_extension=None):
        """See `ITranslationImportQueue.`"""
        queries = ["TRUE"]
        clause_tables = []
        if target is not None:
            if IPerson.providedBy(target):
                queries.append('importer = %s' % sqlvalues(target))
            elif IProduct.providedBy(target):
                queries.append('productseries = ProductSeries.id')
                queries.append(
                    'ProductSeries.product = %s' % sqlvalues(target))
                clause_tables.append('ProductSeries')
            elif IProductSeries.providedBy(target):
                queries.append('productseries = %s' % sqlvalues(target))
            elif IDistribution.providedBy(target):
                queries.append('distroseries = DistroSeries.id')
                queries.append(
                    'DistroSeries.distribution = %s' % sqlvalues(target))
                clause_tables.append('DistroSeries')
            elif IDistroSeries.providedBy(target):
                queries.append('distroseries = %s' % sqlvalues(target))
            elif ISourcePackage.providedBy(target):
                queries.append(
                    'distroseries = %s' % sqlvalues(target.distroseries))
                queries.append(
                    'sourcepackagename = %s' % sqlvalues(
                        target.sourcepackagename))
            else:
                raise AssertionError(
                    'Target argument must be one of IPerson, IProduct,'
                    ' IProductSeries, IDistribution, IDistroSeries or'
                    ' ISourcePackage')
        if status is not None:
            queries.append('status = %s' % sqlvalues(status.value))
        if file_extension is not None:
            queries.append("path LIKE '%%' || %s" % quote_like(file_extension))

        return queries, clause_tables

    def getAllEntries(self, target=None, import_status=None,
                      file_extension=None):
        """See ITranslationImportQueue."""
        queries, clause_tables = self._getQueryByFiltering(
            target, import_status, file_extension)
        return TranslationImportQueueEntry.select(
            " AND ".join(queries), clauseTables=clause_tables,
            orderBy=['status', 'dateimported', 'id'])

    def getFirstEntryToImport(self, target=None):
        """See ITranslationImportQueue."""
        # Prepare the query to get only APPROVED entries.
        queries, clause_tables = self._getQueryByFiltering(
            target, status=RosettaImportStatus.APPROVED, file_extension=None)

        if (IDistribution.providedBy(target) or
            IDistroSeries.providedBy(target) or
            ISourcePackage.providedBy(target)):
            # If the Distribution series has actived the option to defer
            # translation imports, we ignore those entries.
            if 'DistroSeries' not in clause_tables:
                clause_tables.append('DistroSeries')
                queries.append('distroseries = DistroSeries.id')

            queries.append('DistroSeries.defer_translation_imports IS FALSE')

        return TranslationImportQueueEntry.selectFirst(
            " AND ".join(queries), clauseTables=clause_tables,
            orderBy=['dateimported'])

    def getPillarObjectsWithImports(self, status=None):
        """See ITranslationImportQueue."""
        # XXX DaniloSegan 2007-05-22: When imported on the module level,
        # it errs out with: "ImportError: cannot import name Person"
        from canonical.launchpad.database.distroseries import DistroSeries
        from canonical.launchpad.database.product import Product

        query = []
        query.append('ProductSeries.product=Product.id')
        query.append(
            'TranslationImportQueueEntry.productseries=ProductSeries.id')
        if status is not None:
            query.append('TranslationImportQueueEntry.status=%s' % sqlvalues(
                status))

        products = Product.select(
            ' AND '.join(query),
            clauseTables=['ProductSeries', 'TranslationImportQueueEntry'],
            distinct=True)

        query = []
        query.append('TranslationImportQueueEntry.distroseries IS NOT NULL')
        query.append(
            'TranslationImportQueueEntry.distroseries=DistroSeries.id')
        query.append('DistroSeries.defer_translation_imports IS FALSE')
        if status is not None:
            query.append('TranslationImportQueueEntry.status=%s' % sqlvalues(
                status))

        distroseriess = DistroSeries.select(
            ' AND '.join(query),
            clauseTables=['TranslationImportQueueEntry'], distinct=True)

        results = set()
        for product in products:
            if IHasTranslationImports.providedBy(product):
                results.add(product)
        for distroseries in distroseriess:
            if IHasTranslationImports.providedBy(distroseries):
                results.add(distroseries)
        return sorted(results, key=pillar_sort_key)

    def executeOptimisticApprovals(self, ztm):
        """See ITranslationImportQueue."""
        there_are_entries_approved = False
        for entry in self.iterNeedsReview():
            if entry.import_into is None:
                # We don't have a place to import this entry. Try to guess it.
                if entry.path.endswith('.po'):
                    # Check if we can guess where it should be imported.
                    guess = entry.getGuessedPOFile()
                    if guess is None:
                        # We were not able to guess a place to import it,
                        # leave the status of this entry as
                        # RosettaImportStatus.NEEDS_REVIEW and wait for an
                        # admin to manually review it.
                        continue
                    # Set the place where it should be imported.
                    entry.pofile = guess

                else:
                    # It's a .pot file
                    # Check if we can guess where it should be imported.
                    guess = entry.guessed_potemplate
                    if guess is None:
                        # We were not able to guess a place to import it,
                        # leave the status of this entry as
                        # RosettaImportStatus.NEEDS_REVIEW and wait for an
                        # admin to manually review it.
                        continue
                    # Set the place where it should be imported.
                    entry.potemplate = guess

            assert not entry.import_into is None

            if entry.status != RosettaImportStatus.APPROVED:
                there_are_entries_approved = True

            # Already know where it should be imported. The entry is approved
            # automatically.
            entry.status = RosettaImportStatus.APPROVED
            # Do the commit to save the changes.
            ztm.commit()

        return there_are_entries_approved

    def executeOptimisticBlock(self, ztm=None):
        """See ITranslationImportQueue."""
        num_blocked = 0
        for entry in self.iterNeedsReview():
            if entry.path.endswith('.pot'):
                # .pot files cannot be managed automatically, ignore them and
                # wait for an admin to do it.
                continue
            # As kiko would say... this method is crack, I know it, but we
            # need it to save time to our poor Rosetta Experts while handling
            # the translation import queue...
            # We need to look for all .pot files that we have on the same
            # directory for the entry we are processin and check that all
            # them are blocked. If there is at least one not blocked,
            # we cannot block the entry.
            templates = entry.getTemplatesOnSameDirectory()
            has_templates = False
            has_templates_unblocked = False
            for template in templates:
                has_templates = True
                if template.status != RosettaImportStatus.BLOCKED:
                    # This template is not set as blocked, so we note it.
                    has_templates_unblocked = True

            if has_templates and not has_templates_unblocked:
                # All .pot templates on the same directory that this entry is,
                # are blocked, so we can block it too.
                entry.status = RosettaImportStatus.BLOCKED
                num_blocked += 1
                if ztm is not None:
                    # Do the commit to save the changes.
                    ztm.commit()

        return num_blocked

    def cleanUpQueue(self):
        """See ITranslationImportQueue."""
        # Get DELETED and IMPORTED entries.
        delta = datetime.timedelta(DAYS_TO_KEEP)
        last_date = datetime.datetime.utcnow() - delta
        res = TranslationImportQueueEntry.select(
            "(status = %s OR status = %s) AND date_status_changed < %s" %
                sqlvalues(RosettaImportStatus.DELETED.value,
                          RosettaImportStatus.IMPORTED.value,
                          last_date))

        n_entries = res.count()

        # Delete the entries.
        for entry in res:
            self.remove(entry)

        return n_entries

    def remove(self, entry):
        """See ITranslationImportQueue."""
        TranslationImportQueueEntry.delete(entry.id)


class HasTranslationImportsMixin:
    """Information related with translation import queue."""
    implements(IHasTranslationImports)

    def getFirstEntryToImport(self):
        """See `IHasTranslationImports`."""
        translation_import_queue = TranslationImportQueue()
        return translation_import_queue.getFirstEntryToImport(target=self)

    def getTranslationImportQueueEntries(self, import_status=None,
                                         file_extension=None):
        """See `IHasTranslationImports`."""
        translation_import_queue = TranslationImportQueue()
        return translation_import_queue.getAllEntries(
            self, import_status=import_status, file_extension=file_extension)
