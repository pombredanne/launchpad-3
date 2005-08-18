#!/usr/bin/python
# Copyright 2005 Canonical Ltd. All rights reserved.

"""Functions for language pack creation script."""

__metaclass__ = type

import datetime
import sys
import tarfile
import tempfile
import time
from StringIO import StringIO
from shutil import copyfileobj

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (flush_database_updates, sqlvalues,
    cursor)
from canonical.librarian.interfaces import ILibrarianClient, UploadFailed
from canonical.launchpad.components.poexport import (DistroReleasePOExporter,
    DistroReleaseTarballPOFileOutput)
from canonical.launchpad.interfaces import IDistributionSet, IVPOExportSet
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad import helpers

def get_distribution(name):
    """Return the distribution with the given name."""
    return getUtility(IDistributionSet)[name]

def get_release(distribution_name, release_name):
    """Return the release with the given name in the distribution with the
    given name.
    """
    return get_distribution(distribution_name).getRelease(release_name)

def iter_sourcepackage_translationdomain_mapping(release):
    """Return an iterator of tuples with sourcepackagename - translationdomain
    mapping.

    With the output of this method we can know the translationdomains that
    a sourcepackage has.
    """
    cur = cursor()
    cur.execute("""
        SELECT DISTINCT SourcePackageName.name, POExport.translationdomain
        FROM POExport, SourcePackageName
        WHERE
            SourcePackageName.id = POExport.sourcepackagename AND
            POExport.languagepack = TRUE AND
            POExport.distrorelease = %s
        ORDER BY SourcePackageName.name, POExport.translationdomain
        """ % sqlvalues(release.id))

    for (sourcepackagename, translationdomain,) in cur.fetchall():
        yield (sourcepackagename, translationdomain)



def export(distribution_name, release_name, component, update, logger):
    """Export a distribution's translations into a tarball.

    Returns a pair containing a filehandle from which the exported tarball can
    be read, and the size of the tarball in bytes.
    """

    release = get_release(distribution_name, release_name)
    exporter = DistroReleasePOExporter(release)
    export_set = getUtility(IVPOExportSet)

    logger.debug("Selecting PO files for export")

    if update:
        if release.datelastlangpack is None:
            raise ValueError(
                "Can't create an update language pack without a base date.")
        else:
            date = release.datelastlangpack
    else:
        date = release.datereleased

    pofiles = export_set.get_distrorelease_pofiles(release, date, component,
        languagepack=True)
    # pofile_count = len(pofiles)
    pofile_count = export_set.get_distrorelease_pofiles_count(
        release, date, component, languagepack=True)
    logger.info("Number of PO files to export: %d" % pofile_count)

    filehandle = tempfile.TemporaryFile()
    archive = helpers.RosettaWriteTarFile(filehandle)
    pofile_output = DistroReleaseTarballPOFileOutput(release, archive)

    for index, pofile in enumerate(pofiles):
        logger.debug("Exporting PO file %d (%d/%d)" %
            (pofile.id, index + 1, pofile_count))

        try:
            pofile_output(
                potemplate=pofile.potemplate,
                language=pofile.language,
                variant=pofile.variant,
                contents=pofile.export())
        except:
            logger.exception(
                "Uncaught exception while exporting PO file %d" % pofile.id)

        # Flush database updates so that the export cache will be saved even
        # if the export process is interrupted.
        flush_database_updates()

    logger.debug("Adding timestamp file")
    contents = datetime.datetime.utcnow().strftime('%Y%m%d\n')
    archive.add_file('rosetta-%s/timestamp.txt' % release.name, contents)

    logger.debug("Adding mapping file")
    mapping_text = ''
    mapping = iter_sourcepackage_translationdomain_mapping(release)
    for sourcepackagename, translationdomain in mapping:
        mapping_text += "%s %s\n" % (sourcepackagename, translationdomain)
    archive.add_file('rosetta-%s/mapping.txt' % release.name, mapping_text)

    logger.info("Done.")

    if not update:
        release.datelastlangpack = UTC_NOW

    archive.close()
    size = filehandle.tell()
    filehandle.seek(0)

    return filehandle, size

def upload(filename, filehandle, size):
    """Upload a translation tarball to the Librarian.

    Returns the file alias of the uploaded file.
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

def send_upload_notification(recipients, distribution_name, release_name,
        component, file_alias):
    """Send a notification of an upload to the Librarian."""

    if component is None:
        components = 'All available'
    else:
        components = component

    simple_sendmail(
        from_addr='rosetta@canonical.com',
        to_addrs=recipients,
        subject='Language pack export complete',
        body=
            'Distribution: %s\n'
            'Release: %s\n'
            'Component: %s\n'
            'Librarian file alias: %s\n'
            % (distribution_name, release_name, components, file_alias))

def export_language_pack(distribution_name, release_name, component, update,
        output_file, email_addresses, logger):

    # Export the translations to a tarball.

    try:
        filehandle, size = export(
            distribution_name, release_name, component, update, logger)
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
                distribution_name, release_name)
        else:
            filename = '%s-%s-%s-translations.tar.gz' % (
                distribution_name, release_name, component)

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
                    distribution_name, release_name, component, file_alias)
            except:
                # Bare except statements are used in order to prevent
                # premature termination of the script.
                logger.exception("Sending notifications failed.")
                return False

    # Return a success code.

    return True

