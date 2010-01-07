# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'collect_import_info',
    'HasTranslationImportsMixin',
    'TranslationImportQueueEntry',
    'TranslationImportQueue'
    ]

import logging
import tarfile
import os.path
import posixpath
import datetime
import re
import pytz
from cStringIO import StringIO
from textwrap import dedent
from zope.interface import implements
from zope.component import getUtility
from sqlobject import SQLObjectNotFound, StringCol, ForeignKey, BoolCol
from storm.expr import And, Or
from storm.locals import Int, Reference

from canonical.database.sqlbase import (
    cursor, quote, quote_like, SQLBase, sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.enumcol import EnumCol
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import (
    IDistroSeries, DistroSeriesStatus)
from lp.registry.interfaces.person import (
    IPerson, validate_person_not_private_membership)
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.services.permission_helpers import is_admin_or_rosetta_expert
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.translations.interfaces.pofile import IPOFileSet
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat)
from lp.translations.interfaces.translationimporter import (
    ITranslationImporter)
from lp.translations.interfaces.translationimportqueue import (
    IHasTranslationImports,
    ITranslationImportQueue,
    ITranslationImportQueueEntry,
    RosettaImportStatus,
    SpecialTranslationImportTargetFilter,
    TranslationImportQueueConflictError,
    UserCannotSetTranslationImportStatus)
from lp.translations.interfaces.potemplate import IPOTemplate
from lp.translations.interfaces.translations import TranslationConstants
from lp.translations.utilities.gettext_po_importer import (
    GettextPOImporter)
from canonical.librarian.interfaces import ILibrarianClient


# Period to wait before entries with terminal statuses are removed from
# the queue.
entry_gc_age = {
    RosettaImportStatus.DELETED: datetime.timedelta(days=3),
    RosettaImportStatus.IMPORTED: datetime.timedelta(days=3),
    RosettaImportStatus.FAILED: datetime.timedelta(days=30),
}


def is_gettext_name(path):
    """Does given file name indicate it's in gettext (PO or POT) format?"""
    base_name, extension = os.path.splitext(path)
    return extension in GettextPOImporter().file_extensions


def collect_import_info(queue_entry, imported_object, warnings):
    """Collect basic information about import for feedback to user.

    :return: a dict providing substitutions for various items used in
        generating import notices.
    """
    info = {
        'dateimport': queue_entry.dateimported.strftime('%F %Rz'),
        'elapsedtime': queue_entry.getElapsedTimeText(),
        'file_link': queue_entry.content.http_url,
        'importer': queue_entry.importer.displayname,
        'max_plural_forms': TranslationConstants.MAX_PLURAL_FORMS,
        'warnings': '',
    }

    if IPOTemplate.providedBy(imported_object):
        template = imported_object
    else:
        template = imported_object.potemplate
    info['template'] = template.displayname

    if warnings:
        info['warnings'] = dedent("""
            There were warnings while parsing the file.  These are not
            fatal, but please correct them if you can.

            %s""") % '\n\n'.join(warnings)

    return info


class TranslationImportQueueEntry(SQLBase):
    implements(ITranslationImportQueueEntry)

    _table = 'TranslationImportQueueEntry'

    path = StringCol(dbName='path', notNull=True)
    content = ForeignKey(foreignKey='LibraryFileAlias', dbName='content',
        notNull=False)
    importer = ForeignKey(
        dbName='importer', foreignKey='Person',
        storm_validator=validate_person_not_private_membership,
        notNull=True)
    dateimported = UtcDateTimeCol(dbName='dateimported', notNull=True,
        default=DEFAULT)
    sourcepackagename_id = Int(name='sourcepackagename', allow_none=True)
    sourcepackagename = Reference(
        sourcepackagename_id, 'SourcePackageName.id')
    distroseries_id = Int(name='distroseries', allow_none=True)
    distroseries = Reference(distroseries_id, 'DistroSeries.id')
    productseries_id = Int(name='productseries', allow_none=True)
    productseries = Reference(productseries_id, 'ProductSeries.id')
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
    error_output = StringCol(notNull=False, default=None)

    @property
    def is_targeted_to_ubuntu(self):
        return (self.distroseries is not None and
            self.distroseries.distribution ==
            getUtility(ILaunchpadCelebrities).ubuntu)

    @property
    def sourcepackage(self):
        """See ITranslationImportQueueEntry."""
        from lp.registry.model.sourcepackage import SourcePackage

        if self.sourcepackagename is None or self.distroseries is None:
            return None

        return SourcePackage(self.sourcepackagename, self.distroseries)

    @property
    def guessed_potemplate(self):
        """See ITranslationImportQueueEntry."""
        importer = getUtility(ITranslationImporter)
        assert importer.isTemplateName(self.path), (
            "We cannot handle file %s here: not a template." % self.path)

        potemplate_set = getUtility(IPOTemplateSet)
        candidate = potemplate_set.getPOTemplateByPathAndOrigin(
            self.path, productseries=self.productseries,
            distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename)
        if candidate is not None:
            # This takes care of most of the auto-approvable cases.
            return candidate

        directory, filename = os.path.split(self.path)
        if not directory:
            # Uploads don't always have paths associated with them, but
            # there may still be a unique single active template with
            # the right filename.
            subset = potemplate_set.getSubset(
                distroseries=self.distroseries,
                sourcepackagename=self.sourcepackagename,
                productseries=self.productseries, iscurrent=True)
            return subset.findUniquePathlessMatch(filename)

        # I give up.
        return None

    @property
    def _guessed_potemplate_for_pofile_from_path(self):
        """Return an `IPOTemplate` that we think is related to this entry.

        We make this guess by matching the path of the queue entry with those
        of the `IPOTemplate`s for the same product series, or for the same
        distro series and source package name (whichever applies to this
        request).

        So if there is a candidate template in the same directory as the
        request's translation file, and we find no other templates in the same
        directory in the database, we have a winner.
        """
        importer = getUtility(ITranslationImporter)
        potemplateset = getUtility(IPOTemplateSet)
        translationimportqueue = getUtility(ITranslationImportQueue)

        assert importer.isTranslationName(self.path), (
            "We cannot handle file %s here: not a translation." % self.path)

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
        # a template file pending of being imported in our queue.
        if self.productseries is None:
            target = self.sourcepackage
        else:
            target = self.productseries

        entries = translationimportqueue.getAllEntries(
            target=target,
            file_extensions=importer.template_suffixes)

        for entry in entries:
            if (os.path.dirname(entry.path) == os.path.dirname(
                guessed_potemplate.path) and
                entry.status not in (
                RosettaImportStatus.IMPORTED, RosettaImportStatus.DELETED)):
                # There is a template entry pending to be imported that has
                # the same path.
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

    def isUbuntuAndIsUserTranslationGroupOwner(self, user):
        """See `ITranslationImportQueueEntry`."""
        # As a special case, the Ubuntu translation group owners can
        # manage Ubuntu uploads.
        if self.is_targeted_to_ubuntu:
            group = self.distroseries.distribution.translationgroup
            if group is not None and user.inTeam(group.owner):
                return True
        return False

    def isUserUploaderOrOwner(self, user):
        """See `ITranslationImportQueueEntry`."""
        if user.inTeam(self.importer):
            return True
        if self.productseries is not None:
            return user.inTeam(self.productseries.product.owner)
        if self.distroseries is not None:
            return user.inTeam(self.distroseries.distribution.owner)
        return False

    def canSetStatus(self, new_status, user):
        """See `ITranslationImportQueueEntry`."""
        if user is None:
            # Anonymous user cannot do anything.
            return False
        can_admin = (is_admin_or_rosetta_expert(user) or
                     self.isUbuntuAndIsUserTranslationGroupOwner(user))
        if new_status == RosettaImportStatus.APPROVED:
            # Only administrators are able to set the APPROVED status, and
            # that's only possible if we know where to import it
            # (import_into not None).
            return can_admin and self.import_into is not None
        if new_status == RosettaImportStatus.IMPORTED:
            # Only rosetta experts are able to set the IMPORTED status, and
            # that's only possible if we know where to import it
            # (import_into not None).
            return (is_admin_or_rosetta_expert(user) and
                    self.import_into is not None)
        if new_status == RosettaImportStatus.FAILED:
            # Only rosetta experts are able to set the FAILED status.
            return is_admin_or_rosetta_expert(user)
        # All other statuses can bset set by all authorized persons.
        return self.isUserUploaderOrOwner(user) or can_admin

    def setStatus(self, new_status, user):
        """See `ITranslationImportQueueEntry`."""
        if not self.canSetStatus(new_status, user):
            raise UserCannotSetTranslationImportStatus()
        self.status = new_status
        self.date_status_changed = UTC_NOW

    def setErrorOutput(self, output):
        """See `ITranslationImportQueueEntry`."""
        self.error_output = output

    def addWarningOutput(self, output):
        """See `ITranslationImportQueueEntry`."""
        # Very crude implementation: if there is no error output, and
        # there is warning output, set error_output to the warning text.
        # Otherwise, merely keep whatever error_output there already is.
        if output and not self.error_output:
            self.setErrorOutput(output)

    def _findCustomLanguageCode(self, language_code):
        """Find applicable custom language code, if any."""
        if self.distroseries is not None:
            target = self.distroseries.distribution.getSourcePackage(
                self.sourcepackagename)
        else:
            target = self.productseries.product
        
        return target.getCustomLanguageCode(language_code)

    def _guessLanguage(self):
        """See ITranslationImportQueueEntry."""
        importer = getUtility(ITranslationImporter)
        if not importer.isTranslationName(self.path):
            # This does not look like the name of a translation file.
            return None
        filename = os.path.basename(self.path)
        language_code, file_ext = os.path.splitext(filename)

        custom_language_code = self._findCustomLanguageCode(language_code)
        if custom_language_code:
            if custom_language_code.language is None:
                language_code = None
            else:
                language_code = custom_language_code.language.code

        return language_code

    @property
    def import_into(self):
        """See ITranslationImportQueueEntry."""
        importer = getUtility(ITranslationImporter)
        if self.pofile is not None:
            # The entry has an IPOFile associated where it should be imported.
            return self.pofile
        elif (self.potemplate is not None and
              importer.isTemplateName(self.path)):
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
            productseries=self.productseries,
            iscurrent=True)
        potemplate = potemplate_subset.getPOTemplateByTranslationDomain(
            translation_domain)

        is_for_distro = self.distroseries is not None
        know_package = (
            sourcepackagename is not None and
            self.sourcepackagename is not None and
            self.sourcepackagename.name == sourcepackagename.name)

        if potemplate is None and is_for_distro and not know_package:
            # The source package from where this translation doesn't have the
            # template that this translation needs it, and thus, we look for
            # it in a different source package as a second try. To do it, we
            # need to get a subset of all packages in current distro series.
            potemplate_subset = potemplateset.getSubset(
                distroseries=self.distroseries, iscurrent=True)
            potemplate = potemplate_subset.getPOTemplateByTranslationDomain(
                translation_domain)

        if potemplate is None:
            # The potemplate is not yet imported; we cannot attach this
            # translation file.
            return None

        # Get or create an IPOFile based on the info we guess.
        pofile = potemplate.getPOFileByLang(language.code, variant=variant)
        if pofile is None:
            pofile = potemplate.newPOFile(language.code, variant=variant)
            if pofile.canEditTranslations(self.importer):
                pofile.owner = self.importer

        if self.is_published:
            # This entry comes from upstream, which means that the path we got
            # is exactly the right one. If it's different from what pofile
            # has, that would mean that either the entry changed its path
            # since previous upload or that we had to guess it and now that we
            # got the right path, we should fix it.
            pofile.setPathIfUnique(self.path)

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
        """See `ITranslationImportQueueEntry`."""
        importer = getUtility(ITranslationImporter)
        assert importer.isTranslationName(self.path), (
            "We cannot handle file %s here: not a translation." % self.path)

        if self.potemplate is None:
            # We don't have the IPOTemplate object associated with this entry.
            # Try to guess it from the file path.
            pofile = self._guessed_pofile_from_path
            if pofile is not None:
                # We were able to guess an IPOFile.
                return pofile

            # Multi-directory trees layout are non-standard layouts of gettext
            # files where the .pot file and its .po files are stored in
            # different directories.
            if is_gettext_name(self.path):
                pofile = self._guess_multiple_directories_with_pofile()
                if pofile is not None:
                    # This entry is fits our multi directory trees layout and
                    # we found a place where it should be imported.
                    return pofile

            # We were not able to find an IPOFile based on the path, try
            # to guess an IPOTemplate before giving up.
            potemplate = self._guessed_potemplate_for_pofile_from_path
            if potemplate is None:
                # No way to guess anything...
                return None

            existing_entry = TranslationImportQueueEntry.selectOneBy(
                importer=self.importer, path=self.path, potemplate=potemplate,
                distroseries=self.distroseries,
                sourcepackagename=self.sourcepackagename,
                productseries=self.productseries)
            if existing_entry is not None:
                logging.warn(
                    "%s: can't approve entry %d ('%s') "
                    "because entry %d is in the way." % (
                        potemplate.title, self.id, self.path,
                        existing_entry.id))
                return None

            # We got the potemplate, try to guess the language from
            # the info we have.
            self.potemplate = potemplate

        # We know the IPOTemplate associated with this entry so we can try to
        # detect the right IPOFile.
        # Let's try to guess the language.
        guessed_language = self._guessLanguage()
        if guessed_language is None:
            # Custom language code says to ignore imports with this language
            # code.
            self.setStatus(RosettaImportStatus.DELETED,
                           getUtility(ILaunchpadCelebrities).rosetta_experts)
            return None
        elif guessed_language == '':
            # We don't recognize this as a translation file with a name
            # consisting of language code and format extension.  Look for an
            # existing translation file based on path match.
            return self._guessed_pofile_from_path
        else:
            return self._get_pofile_from_language(guessed_language,
                self.potemplate.translation_domain,
                sourcepackagename=self.potemplate.sourcepackagename)

    def _guess_multiple_directories_with_pofile(self):
        """Return `IPOFile` that we think is related to this entry, or None.

        Multi-directory tree layouts are non-standard layouts where the .pot
        file and its .po files are stored in different directories.  We only
        know of this happening with gettext files.

        The known layouts are:

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
        have the sourcepackagename following the pattern 'kde-i18n-LANGCODE'
        (KDE3) or kde-l10n-LANGCODE (KDE4).
        """
        # Recognize "kde-i18n-LANGCODE" and "kde-l10n-LANGCODE" as
        # special cases.
        kde_prefix_pattern = '^kde-(i18n|l10n)-'

        importer = getUtility(ITranslationImporter)

        assert is_gettext_name(self.path), (
            "We cannot handle file %s here: not a gettext file." % self.path)
        assert importer.isTranslationName(self.path), (
            "We cannot handle file %s here: not a translation." % self.path)

        if self.productseries is not None:
            # This method only works for sourcepackages. It makes no sense use
            # it with productseries.
            return None

        if re.match(kde_prefix_pattern, self.sourcepackagename.name):
            # We need to extract the language information from the package
            # name

            # These language codes have special meanings.
            lang_mapping = {
                'engb': 'en_GB',
                'ptbr': 'pt_BR',
                'srlatn': 'sr@Latn',
                'zhcn': 'zh_CN',
                'zhtw': 'zh_TW',
                }

            lang_code = re.sub(
                kde_prefix_pattern, '', self.sourcepackagename.name)
            lang_code = lang_mapping.get(lang_code, lang_code)
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
                # We have another directory between the language code
                # directory and the filename (second and third case).
                dir_path = os.path.dirname(dir_path)
                lang_code = os.path.basename(dir_path)
            else:
                # The .po file is stored inside the directory with the
                # language code as its name or an unsupported layout.
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
            translation_domain = potemplate.translation_domain
        else:
            # The guessed language from the directory doesn't match the
            # language from the filename. Leave it for an admin.
            return None

        if (self.sourcepackagename.name in ('k3b-i18n', 'koffice-l10n') or
            re.match(kde_prefix_pattern, self.sourcepackagename.name)):
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
        importer = getUtility(ITranslationImporter)
        path = os.path.dirname(self.path)

        suffix_clauses = [
            "path LIKE '%%' || %s" % quote_like(suffix)
            for suffix in importer.template_suffixes]

        clauses = [
            "path LIKE %s || '%%'" % quote_like(path),
            "id <> %s" % quote(self.id),
            "(%s)" % " OR ".join(suffix_clauses)]

        if self.distroseries is not None:
            clauses.append('distroseries = %s' % quote(self.distroseries))
        if self.sourcepackagename is not None:
            clauses.append(
                'sourcepackagename = %s' % quote(self.sourcepackagename))
        if self.productseries is not None:
            clauses.append("productseries = %s" % quote(self.productseries))

        return TranslationImportQueueEntry.select(" AND ".join(clauses))

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

    def countEntries(self):
        """See `ITranslationImportQueue`."""
        return TranslationImportQueueEntry.select().count()

    def _iterNeedsReview(self):
        """Iterate over all entries in the queue that need review."""
        return iter(TranslationImportQueueEntry.selectBy(
            status=RosettaImportStatus.NEEDS_REVIEW,
            orderBy=['dateimported']))

    def _getMatchingEntry(self, path, importer, potemplate, pofile,
                           sourcepackagename, distroseries, productseries):
        """Find an entry that best matches the given parameters, if such an
        entry exists.

        When the user uploads a file, we need to figure out whether to update
        an existing entry or create a new one.  There may be zero, one, or
        multiple entries that match the new upload.  If it's more than one,
        that will be because one matching entry is more specific than the
        other.  'More specific' refers to how well the import location has
        been specified for this entry.  There are three cases, ordered from
        least specific to most specific:

        1. potemplate and pofile are None,
        2. potemplate is not None but pofile is None,
        3. potemplate and pofile are both not None.

        If no exactly matching entry can be found, the next more specific
        entry is chosen, if it exists. If there is more than one such entry,
        there is no best choice and `TranslationImportQueueConflictError`
        is raised.

        :return: The matching entry or None, if no matching entry was found
            at all."""

        # Find possible candidates by querying the database.
        queries = ['TranslationImportQueueEntry.path = %s' % sqlvalues(path)]
        queries.append(
            'TranslationImportQueueEntry.importer = %s' % sqlvalues(importer))
        # Depending on how specific the new entry is, potemplate and pofile
        # may be None.
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
        # Order the results by level of specificity.
        entries = TranslationImportQueueEntry.select(
                ' AND '.join(queries),
                orderBy="potemplate IS NULL DESC, pofile IS NULL DESC")

        # Deal with the simple cases.
        if entries.count() == 0:
            return None
        if entries.count() == 1:
            return entries[0]

        # Check that the top two entries differ in levels of specificity.
        # Other entries don't matter because they are either of the same
        # or even greater specificity, as specified in the query.
        pofile_specificity_is_equal = (
            (entries[0].pofile is None) == (entries[1].pofile is None))
        potemplate_specificity_is_equal = (
            (entries[0].potemplate is None) ==
            (entries[1].potemplate is None))
        if pofile_specificity_is_equal and potemplate_specificity_is_equal:
            raise TranslationImportQueueConflictError

        return entries[0]

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

        try:
            entry = self._getMatchingEntry(path, importer, potemplate,
                    pofile, sourcepackagename, distroseries, productseries)
        except TranslationImportQueueConflictError:
            return None
        if entry is None:
            # It's a new row.
            entry = TranslationImportQueueEntry(path=path, content=alias,
                importer=importer, sourcepackagename=sourcepackagename,
                distroseries=distroseries, productseries=productseries,
                is_published=is_published, potemplate=potemplate,
                pofile=pofile, format=format)
        else:
            # It's an update.
            entry.setErrorOutput(None)
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
                entry.setStatus(RosettaImportStatus.NEEDS_REVIEW, importer)

            entry.date_status_changed = UTC_NOW
            entry.format = format
            entry.sync()

        return entry

    def addOrUpdateEntriesFromTarball(self, content, is_published, importer,
        sourcepackagename=None, distroseries=None, productseries=None,
        potemplate=None, filename_filter=None):
        """See ITranslationImportQueue."""
        # XXX: kiko 2008-02-08 bug=4473: This whole set of ifs is a
        # workaround for bug 44773 (Python's gzip support sometimes fails to
        # work when using plain tarfile.open()). The issue is that we can't
        # rely on tarfile's smart detection of filetypes and instead need to
        # hardcode the type explicitly in the mode. We simulate magic
        # here to avoid depending on the python-magic package. We can
        # get rid of this when http://bugs.python.org/issue1488634 is
        # fixed.
        #
        # XXX: 2008-02-08 kiko bug=1982: Incidentally, this also works around
        # bug #1982 (Python's bz2 support is not able to handle external file
        # objects). That bug is worked around by using tarfile.open() which
        # wraps the fileobj in a tarfile._Stream instance. We can get rid of
        # this when we upgrade to python2.5 everywhere.
        num_files = 0
        conflict_files = []

        if content.startswith('BZh'):
            mode = "r|bz2"
        elif content.startswith('\037\213'):
            mode = "r|gz"
        elif content[257:262] == 'ustar':
            mode = "r|tar"
        else:
            # Not a tarball, we ignore it.
            return (num_files, conflict_files)

        translation_importer = getUtility(ITranslationImporter)

        try:
            tarball = tarfile.open('', mode, StringIO(content))
        except tarfile.ReadError:
            # If something went wrong with the tarfile, assume it's
            # busted and let the user deal with it.
            return (num_files, conflict_files)

        for tarinfo in tarball:
            if not tarinfo.isfile():
                # Don't be tricked into reading directories, symlinks,
                # or worst of all: devices.
                continue

            filename = posixpath.normpath(tarinfo.name)
            if filename_filter:
                filename = filename_filter(filename)
            if filename is None or filename == '':
                continue

            if posixpath.basename(filename).startswith('.'):
                # Dotfile.  Probably an editor backup or somesuch.
                continue

            base, ext = posixpath.splitext(filename)
            if ext not in translation_importer.supported_file_extensions:
                # Doesn't look like a supported translation file type.
                continue

            file_content = tarball.extractfile(tarinfo).read()

            if len(file_content) == 0:
                # Empty.  Ignore.
                continue

            entry = self.addOrUpdateEntry(
                filename, file_content, is_published, importer,
                sourcepackagename=sourcepackagename,
                distroseries=distroseries, productseries=productseries,
                potemplate=potemplate)
            if entry == None:
                conflict_files.append(filename)
            else:
                num_files += 1

        tarball.close()

        return (num_files, conflict_files)

    def get(self, id):
        """See ITranslationImportQueue."""
        try:
            return TranslationImportQueueEntry.get(id)
        except SQLObjectNotFound:
            return None

    def _getQueryByFiltering(self, target=None, status=None,
                             file_extensions=None):
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
            elif target == SpecialTranslationImportTargetFilter.PRODUCT:
                queries.append('productseries IS NOT NULL')
            elif target == SpecialTranslationImportTargetFilter.DISTRIBUTION:
                queries.append('distroseries IS NOT NULL')
            else:
                raise AssertionError(
                    'Target argument must be one of IPerson, IProduct,'
                    ' IProductSeries, IDistribution, IDistroSeries or'
                    ' ISourcePackage')
        if status is not None:
            queries.append(
                'TranslationImportQueueEntry.status = %s' % sqlvalues(status))
        if file_extensions:
            extension_clauses = [
                "path LIKE '%%' || %s" % quote_like(extension)
                for extension in file_extensions]
            queries.append("(%s)" % " OR ".join(extension_clauses))

        return queries, clause_tables

    def getAllEntries(self, target=None, import_status=None,
                      file_extensions=None):
        """See ITranslationImportQueue."""
        queries, clause_tables = self._getQueryByFiltering(
            target, import_status, file_extensions)
        return TranslationImportQueueEntry.select(
            " AND ".join(queries), clauseTables=clause_tables,
            orderBy=['status', 'dateimported', 'id'])

    def getFirstEntryToImport(self, target=None):
        """See ITranslationImportQueue."""
        # Prepare the query to get only APPROVED entries.
        queries, clause_tables = self._getQueryByFiltering(
            target, status=RosettaImportStatus.APPROVED)

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

    def getRequestTargets(self, status=None):
        """See `ITranslationImportQueue`."""
        # XXX DaniloSegan 2007-05-22: When imported on the module level,
        # it errs out with: "ImportError: cannot import name Person"
        from lp.registry.model.distroseries import DistroSeries
        from lp.registry.model.product import Product

        if status is None:
            status_clause = "TRUE"
        else:
            status_clause = (
                "TranslationImportQueueEntry.status = %s" % sqlvalues(status))

        def distroseries_sort_key(distroseries):
            return (distroseries.distribution.name, distroseries.name)

        query = [
            'ProductSeries.product = Product.id',
            'TranslationImportQueueEntry.productseries = ProductSeries.id',
            'Product.active IS TRUE']
        if status is not None:
            query.append(status_clause)

        products = list(Product.select(
            ' AND '.join(query),
            clauseTables=['ProductSeries', 'TranslationImportQueueEntry'],
            distinct=True, orderBy='Product.name'))

        distroseriess = shortlist(DistroSeries.select("""
            defer_translation_imports IS FALSE AND
            id IN (
                SELECT DISTINCT distroseries
                FROM TranslationImportQueueEntry
                WHERE %s
                )
            """ % status_clause))
        distroseriess.sort(key=distroseries_sort_key)

        return distroseriess + products

    def executeOptimisticApprovals(self, txn=None):
        """See ITranslationImportQueue."""
        there_are_entries_approved = False
        importer = getUtility(ITranslationImporter)
        for entry in self._iterNeedsReview():
            if entry.import_into is None:
                # We don't have a place to import this entry. Try to guess it.
                if importer.isTranslationName(entry.path):
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
                    # It's a template.
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
            entry.setStatus(RosettaImportStatus.APPROVED,
                            getUtility(ILaunchpadCelebrities).rosetta_experts)

            if txn is not None:
                txn.commit()

        return there_are_entries_approved

    def executeOptimisticBlock(self, txn=None):
        """See ITranslationImportQueue."""
        importer = getUtility(ITranslationImporter)
        num_blocked = 0
        for entry in self._iterNeedsReview():
            if importer.isTemplateName(entry.path):
                # Templates cannot be managed automatically.  Ignore them and
                # wait for an admin to do it.
                continue
            # As kiko would say... this method is crack, I know it, but we
            # need it to save time to our poor Rosetta Experts while handling
            # the translation import queue...
            # We need to look for all templates that we have on the same
            # directory for the entry we are processing, and check that all of
            # them are blocked. If there is at least one that's not blocked,
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
                # All templates on the same directory as this entry are
                # blocked, so we can block it too.
                entry.setStatus(
                    RosettaImportStatus.BLOCKED,
                    getUtility(ILaunchpadCelebrities).rosetta_experts)
                num_blocked += 1
                if txn is not None:
                    txn.commit()

        return num_blocked

    def _cleanUpObsoleteEntries(self, store):
        """Delete obsolete queue entries.

        :param store: The Store to delete from.
        :return: Number of entries deleted.
        """
        now = datetime.datetime.now(pytz.UTC)
        deletion_clauses = []
        for status, gc_age in entry_gc_age.iteritems():
            cutoff = now - gc_age
            deletion_clauses.append(And(
                TranslationImportQueueEntry.status == status,
                TranslationImportQueueEntry.date_status_changed < cutoff))

        entries = store.find(
            TranslationImportQueueEntry, Or(*deletion_clauses))

        return entries.remove()

    def _cleanUpInactiveProductEntries(self, store):
        """Delete queue entries for deactivated `Product`s.

        :param store: The Store to delete from.
        :return: Number of entries deleted.
        """
        # XXX JeroenVermeulen 2009-09-18 bug=271938: Stormify this once
        # the Storm remove() syntax starts working properly for joins.
        cur = cursor()
        cur.execute("""
            DELETE FROM TranslationImportQueueEntry AS Entry
            USING ProductSeries, Product
            WHERE
                ProductSeries.id = Entry.productseries AND
                Product.id = ProductSeries.product AND
                Product.active IS FALSE
            """)
        return cur.rowcount

    def _cleanUpObsoleteDistroEntries(self, store):
        """Delete some queue entries for obsolete `DistroSeries`.

        :param store: The Store to delete from.
        :return: Number of entries deleted.
        """
        # XXX JeroenVermeulen 2009-09-18 bug=271938,432484: Stormify
        # this once Storm's remove() supports joins and slices.
        cur = cursor()
        cur.execute("""
            DELETE FROM TranslationImportQueueEntry
            WHERE id IN (
                SELECT Entry.id
                FROM TranslationImportQueueEntry Entry
                JOIN DistroSeries ON
                    DistroSeries.id = Entry.distroseries
                JOIN Distribution ON
                    Distribution.id = DistroSeries.distribution
                WHERE DistroSeries.releasestatus = %s
                LIMIT 100)
            """ % quote(DistroSeriesStatus.OBSOLETE))
        return cur.rowcount

    def cleanUpQueue(self):
        """See `ITranslationImportQueue`."""
        store = IMasterStore(TranslationImportQueueEntry)

        return (
            self._cleanUpObsoleteEntries(store) +
            self._cleanUpInactiveProductEntries(store) +
            self._cleanUpObsoleteDistroEntries(store))

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
        if file_extension is None:
            extensions = None
        else:
            extensions = [file_extension]
        translation_import_queue = TranslationImportQueue()
        return translation_import_queue.getAllEntries(
            self, import_status=import_status, file_extensions=extensions)
