# Copyright 2005-2007 Canonical Ltd. All rights reserved.
# pylint: disable-msg=W0702

"""Functions for language pack creation script."""

__metaclass__ = type

__all__ = [
    'export_language_pack',
    ]

import datetime
import os
import sys
import tempfile
from shutil import copyfileobj

from zope.component import getUtility

from canonical.database.sqlbase import sqlvalues, cursor
from canonical.launchpad.interfaces import (
    IDistributionSet, ILanguagePackSet, IVPOExportSet, LanguagePackType,
    TranslationFileFormat)
from canonical.launchpad.translationformat.translation_export import (
    LaunchpadWriteTarFile)
from canonical.librarian.interfaces import ILibrarianClient, UploadFailed


def iter_sourcepackage_translationdomain_mapping(series):
    """Return an iterator of tuples with sourcepackagename - translationdomain
    mapping.

    With the output of this method we can know the translationdomains that
    a sourcepackage has.
    """
    cur = cursor()
    cur.execute("""
        SELECT SourcePackageName.name, POTemplate.translation_domain
        FROM
            SourcePackageName
            JOIN POTemplate ON
                POTemplate.sourcepackagename = SourcePackageName.id AND
                POTemplate.distroseries = %s AND
                POTemplate.languagepack = TRUE
        ORDER BY SourcePackageName.name, POTemplate.translation_domain
        """ % sqlvalues(series))

    for (sourcepackagename, translationdomain,) in cur.fetchall():
        yield (sourcepackagename, translationdomain)


def export(distroseries, component, update, force_utf8, logger):
    """Return a pair containing a filehandle from which the distribution's
    translations tarball can be read and the size of the tarball i bytes.

    :arg distroseries: The `IDistroSeries` we want to export from.
    :arg component: The component name from the given distribution series.
    :arg update: Whether the export should be an update from the last export.
    :arg force_utf8: Whether the export should have all files exported as
        UTF-8.
    :arg logger: A logger object.
    """
    # We will need when the export started later to add the timestamp for this
    # export inside the exported tarball.
    start_date = datetime.datetime.utcnow().strftime('%Y%m%d')
    export_set = getUtility(IVPOExportSet)

    logger.debug("Selecting PO files for export")

    date = None
    if update:
        # Get the export date for the current base language pack.
        date = distroseries.language_pack_base.date_exported

    pofile_count = export_set.get_distroseries_pofiles_count(
        distroseries, date, component, languagepack=True)
    logger.info("Number of PO files to export: %d" % pofile_count)

    filehandle = tempfile.TemporaryFile()
    archive = LaunchpadWriteTarFile(filehandle)

    # XXX JeroenVermeulen 2008-02-06: Is there anything here that we can unify
    # with the export-queue code?
    index = 0
    xpi_templates_to_export = set()
    path_prefix = 'rosetta-%s' % distroseries.name
    for pofile in export_set.get_distroseries_pofiles(
        distroseries, date, component, languagepack=True):
        logger.debug("Exporting PO file %d (%d/%d)" %
            (pofile.id, index + 1, pofile_count))

        potemplate = pofile.potemplate
        domain = potemplate.translation_domain.encode('ascii')
        language_code = pofile.language.code.encode('ascii')

        if pofile.variant is not None:
            code = '%s@%s' % (language_code, pofile.variant.encode('UTF-8'))
        else:
            code = language_code

        if potemplate.source_file_format == TranslationFileFormat.XPI:
            xpi_templates_to_export.add(potemplate)
            path = os.path.join(
                path_prefix, 'xpi', domain, '%s.po' % code)
        else:
            path = os.path.join(
                path_prefix, code, 'LC_MESSAGES', '%s.po' % domain)

        try:
            # We don't want obsolete entries here, it makes no sense for a
            # language pack.
            contents = pofile.export(
                ignore_obsolete=True, force_utf8=force_utf8)

            # Store it in the tarball.
            archive.add_file(path, contents)
        except:
            logger.exception(
                "Uncaught exception while exporting PO file %d" % pofile.id)

        index += 1

    logger.info("Exporting XPI template files.")
    librarian_client = getUtility(ILibrarianClient)
    for template in xpi_templates_to_export:
        if template.source_file is None:
            logger.warning(
                "%s doesn't have source file registered." % potemplate.title)
            continue
        domain = template.translation_domain.encode('ascii')
        archive.add_file(
            os.path.join(path_prefix, 'xpi', domain, 'en-US.xpi'),
            librarian_client.getFileByAlias(
                template.source_file.id).read())

    logger.info("Adding timestamp file")
    # Is important that the timestamp contain the date when the export
    # started, not when it finished because that notes how old is the
    # information the export contains.
    archive.add_file(
        'rosetta-%s/timestamp.txt' % distroseries.name, '%s\n' % start_date)

    logger.info("Adding mapping file")
    mapping_text = ''
    mapping = iter_sourcepackage_translationdomain_mapping(distroseries)
    for sourcepackagename, translationdomain in mapping:
        mapping_text += "%s %s\n" % (sourcepackagename, translationdomain)
    archive.add_file(
        'rosetta-%s/mapping.txt' % distroseries.name, mapping_text)

    logger.info("Done.")

    archive.close()
    size = filehandle.tell()
    filehandle.seek(0)

    return filehandle, size


def export_language_pack(distribution_name, series_name, logger,
                         component=None, force_utf8=False, output_file=None):
    """Export a language pack for the given distribution series.

    :param distribution_name: Name of the distribution we want to export the
        language pack from.
    :param series_name: Name of the distribution series we want to export the
        language pack from.
    :param logger: Logger object.
    :param component: The component for the given distribution series. This
        will be used as a filtering option when selecting the files to export.
    :param force_utf8: A flag indicating whether all files exported must be
        force to use the UTF-8 encoding.
    :param output_file: File path where this export file should be stored,
        instead of using Librarian. If '-' is given, we use standard output.
    :return: The exported language pack or None.
    """
    distribution = getUtility(IDistributionSet)[distribution_name]
    distroseries = distribution.getSeries(series_name)

    if distroseries.language_pack_full_export_requested:
        # We were instructed that this export must be a full one.
        update = False
        logger.info('Got a request to do a full language pack export.')
        # Also, unset that flag so next export will proceed normally.
        distroseries.language_pack_full_export_requested = False
    elif distroseries.language_pack_base is None:
        # There is no full export language pack being used, we cannot produce
        # an update.
        update = False
    else:
        # There is a base package with a full export and we didn't get a
        # request to do a full export, we will generate an update based on
        # latest full export being used as the base language pack.
        update = True

    # Export the translations to a tarball.
    try:
        filehandle, size = export(
            distroseries, component, update, force_utf8, logger)
    except:
        # Bare except statements are used in order to prevent premature
        # termination of the script.
        logger.exception('Uncaught exception while exporting')
        return None

    if output_file is not None:
        # Save the tarball to a file.

        if output_file == '-':
            output_filehandle = sys.stdout
        else:
            output_filehandle = file(output_file, 'wb')

        copyfileobj(filehandle, output_filehandle)
    else:
        # Upload the tarball to the librarian.

        if update:
            suffix = '-update'
        else:
            suffix = ''

        if component is None:
            filename = '%s-%s-translations%s.tar.gz' % (
                distribution_name, series_name, suffix)
        else:
            filename = '%s-%s-%s-translations%s.tar.gz' % (
                distribution_name, series_name, component, suffix)

        try:
            uploader = getUtility(ILibrarianClient)
            # For tar.gz files, the standard content type is
            # application/x-gtar. You can see more info on
            # http://en.wikipedia.org/wiki/List_of_archive_formats
            file_alias = uploader.addFile(
                name=filename,
                size=size,
                file=filehandle,
                contentType='application/x-gtar')
        except UploadFailed, e:
            logger.error('Uploading to the Librarian failed: %s', e)
            return None
        except:
            # Bare except statements are used in order to prevent premature
            # termination of the script.
            logger.exception(
                'Uncaught exception while uploading to the Librarian')
            return None

        logger.debug('Upload complete, file alias: %d' % file_alias)

        # Let's register this new language pack.
        language_pack_set = getUtility(ILanguagePackSet)
        if update:
            lang_pack_type = LanguagePackType.DELTA
        else:
            lang_pack_type = LanguagePackType.FULL

        language_pack = language_pack_set.addLanguagePack(
            distroseries, file_alias, lang_pack_type)

        logger.info('Registered the language pack.')

        return language_pack
