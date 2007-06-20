#!/usr/bin/python
# Copyright 2005 Canonical Ltd. All rights reserved.

"""Functions for language pack creation script."""

__metaclass__ = type

import datetime
import sys
import tempfile
import transaction
from shutil import copyfileobj

from zope.component import getUtility

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (flush_database_updates, sqlvalues,
    cursor)
from canonical.librarian.interfaces import ILibrarianClient, UploadFailed
from canonical.launchpad.components.poexport import (DistroSeriesPOExporter,
    DistroSeriesTarballPOFileOutput, RosettaWriteTarFile)
from canonical.launchpad.interfaces import IDistributionSet, IVPOExportSet
from canonical.launchpad.mail import simple_sendmail

def get_distribution(name):
    """Return the distribution with the given name."""
    return getUtility(IDistributionSet)[name]

def get_series(distribution_name, series_name):
    """Return the series with the given name in the distribution with the
    given name.
    """
    return get_distribution(distribution_name).getSeries(series_name)

def iter_sourcepackage_translationdomain_mapping(series):
    """Return an iterator of tuples with sourcepackagename - translationdomain
    mapping.

    With the output of this method we can know the translationdomains that
    a sourcepackage has.
    """
    cur = cursor()
    cur.execute("""
        SELECT SourcePackageName.name, POTemplateName.translationdomain
        FROM
            SourcePackageName
            JOIN POTemplate ON
                POTemplate.sourcepackagename = SourcePackageName.id AND
                POTemplate.distrorelease = %s AND
                POTemplate.languagepack = TRUE
            JOIN POTemplateName ON
                POTemplate.potemplatename = POTemplateName.id
        ORDER BY SourcePackageName.name, POTemplateName.translationdomain
        """ % sqlvalues(series))

    for (sourcepackagename, translationdomain,) in cur.fetchall():
        yield (sourcepackagename, translationdomain)

def export(distribution_name, series_name, component, update, force_utf8,
    logger):
    """Return a pair containing a filehandle from which the distribution's
    translations tarball can be read and the size of the tarball i bytes.

    :distribution_name: The name of the distribution.
    :series_name: The name of the distribution series.
    :component: The component name from the given distribution series.
    :update: Whether the export should be an update from the last export.
    :force_utf8: Whether the export should have all files exported as UTF-8.
    :logger: The logger object.
    """
    series = get_series(distribution_name, series_name)
    exporter = DistroSeriesPOExporter(series)
    export_set = getUtility(IVPOExportSet)

    logger.debug("Selecting PO files for export")

    if update:
        if series.datelastlangpack is None:
            # It's the first language pack for this series so the update must
            # be the release date for the distro series.
            date = series.datereleased
        else:
            date = series.datelastlangpack
    else:
        date = series.datereleased

    pofile_count = export_set.get_distroseries_pofiles_count(
        series, date, component, languagepack=True)
    logger.info("Number of PO files to export: %d" % pofile_count)

    filehandle = tempfile.TemporaryFile()
    archive = RosettaWriteTarFile(filehandle)
    pofile_output = DistroSeriesTarballPOFileOutput(series, archive)

    index = 0
    for pofile in export_set.get_distroseries_pofiles(
        series, date, component, languagepack=True):
        logger.debug("Exporting PO file %d (%d/%d)" %
            (pofile.id, index + 1, pofile_count))

        try:
            # We don't want obsolete entries here, it makes no sense for a
            # language pack.
            contents = pofile.uncachedExport(
                included_obsolete=False, force_utf8=force_utf8)

            pofile_output(
                potemplate=pofile.potemplate,
                language=pofile.language,
                variant=pofile.variant,
                contents=contents)
        except:
            logger.exception(
                "Uncaught exception while exporting PO file %d" % pofile.id)

        index += 1

    logger.debug("Adding timestamp file")
    contents = datetime.datetime.utcnow().strftime('%Y%m%d\n')
    archive.add_file('rosetta-%s/timestamp.txt' % series.name, contents)

    logger.debug("Adding mapping file")
    mapping_text = ''
    mapping = iter_sourcepackage_translationdomain_mapping(series)
    for sourcepackagename, translationdomain in mapping:
        mapping_text += "%s %s\n" % (sourcepackagename, translationdomain)
    archive.add_file('rosetta-%s/mapping.txt' % series.name, mapping_text)

    logger.info("Done.")

    if not update:
        series.datelastlangpack = UTC_NOW

    archive.close()
    size = filehandle.tell()
    filehandle.seek(0)

    return filehandle, size

def upload(filename, filehandle, size):
    """Upload a translation tarball to the Librarian.

    Return the file alias of the uploaded file.
    """

    uploader = getUtility(ILibrarianClient)
    file_alias = uploader.addFile(
        name=filename,
        size=size,
        file=filehandle,
        contentType='application/octet-stream')

    return file_alias

def compose_mail(sender, recipients, headers, body):
    """Compose a mail text."""

    all_headers = dict(headers)
    all_headers.update({
        'To': ', '.join(recipients),
        'From': sender
        })

    header = '\n'.join([
        '%s: %s' % (key, all_headers[key])
        for key in all_headers
        ])

    return header + '\n\n' + body

def send_upload_notification(recipients, distribution_name, series_name,
        component, file_alias):
    """Send a notification of an upload to the Librarian."""

    if component is None:
        components = 'All available'
    else:
        components = component

    simple_sendmail(
        from_addr=config.rosetta.rosettaadmin.email,
        to_addrs=recipients,
        subject='Language pack export complete',
        body=
            'Distribution: %s\n'
            'Release: %s\n'
            'Component: %s\n'
            'Librarian file alias: %s\n'
            % (distribution_name, series_name, components, file_alias))

def export_language_pack(distribution_name, series_name, component, update,
        force_utf8, output_file, email_addresses, logger):

    # Export the translations to a tarball.

    try:
        filehandle, size = export(
            distribution_name, series_name, component, update, force_utf8,
            logger)
    except:
        # Bare except statements are used in order to prevent premature
        # termination of the script.
        logger.exception('Uncaught exception while exporting')
        return False

    if output_file is not None:
        # Save the tarball to a file.

        if output_file == '-':
            output_filehandle = sys.stdout
        else:
            output_filehandle = file(output_file, 'wb')

        copyfileobj(filehandle, output_filehandle)
    else:
        # Upload the tarball to the librarian.

        if component is None:
            filename = '%s-%s-translations.tar.gz' % (
                distribution_name, series_name)
        else:
            filename = '%s-%s-%s-translations.tar.gz' % (
                distribution_name, series_name, component)

        try:
            file_alias = upload(filename, filehandle, size)
        except UploadFailed, e:
            logger.error('Uploading to the Librarian failed: %s', e)
            return False
        except:
            # Bare except statements are used in order to prevent premature
            # termination of the script.
            logger.exception('Uncaught exception while uploading to the Librarian')
            return False

        logger.info('Upload complete, file alias: %d' % file_alias)

        if email_addresses:
            # Send a notification email.

            try:
                send_upload_notification(email_addresses,
                    distribution_name, series_name, component, file_alias)
            except:
                # Bare except statements are used in order to prevent
                # premature termination of the script.
                logger.exception("Sending notifications failed.")
                return False

    # Return a success code.

    return True

