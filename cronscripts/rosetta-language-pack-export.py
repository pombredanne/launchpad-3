#!/usr/bin/python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Script to export a tarball of translations for a distro release."""

__metaclass__ = type

import logging
import optparse
import os
import smtplib
import sys
import tempfile

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.librarian.interfaces import ILibrarianClient, UploadFailed
from canonical.launchpad.components.poexport import DistroReleasePOExporter
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts import execute_zcml_for_scripts

def parse_options(args):
    """Parse options for exporting distribution release translations.

    Returns a 3-tuple containing an options object, a distribution name and a
    release name.
    """

    parser = optparse.OptionParser(
        usage='%prog [options] distribution release')
    parser.add_option(
        '--email',
        dest='email_adresses',
        default=[],
        action='append',
        help='An email address to send a notification to.'
        )

    options, args = parser.parse_args(args)

    if len(args) != 2:
        parser.error('Wrong number of arguments')

    return options, args[0], args[1]

def get_distribution(name):
    """Return the distribution with the given name."""
    return getUtility(IDistributionSet)[name]

def get_release(distribution_name, release_name):
    """Return the release with the given name in the distribution with the
    given name.
    """
    return get_distribution(distribution_name).getRelease(release_name)

def make_logger(loglevel=logging.WARN):
    """Return a logger object for logging with."""
    logger = logging.getLogger("rosetta-language-pack-export")
    handler = logging.StreamHandler(strm=sys.stderr)
    handler.setFormatter(
        logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(loglevel)
    return logger

def export(distribution_name, release_name):
    """Export a distribution's translations into a tarball.

    Returns a pair containing a filehandle from which the exported tarball can
    be read, and the size of the tarball in bytes.
    """

    release = get_release(distribution_name, release_name)
    exporter = DistroReleasePOExporter(release)

    filehandle = tempfile.TemporaryFile()

    if release.datereleased:
        exporter.export_tarball_to_file(filehandle, release.datereleased)
    else:
        exporter.export_tarball_to_file(filehandle)

    size = filehandle.tell()
    filehandle.seek(0)

    return filehandle, size

def logged_export(distribution_name, release_name, logger):
    """As export(), except that errors are logged."""

    try:
        filehandle, size = export(distribution_name, release_name)
    except:
        logger.exception('Uncaught exception while exporting')
        raise

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

def logged_upload(filename, filehandle, size, logger):
    """As upload(), except that errors are logged."""

    try:
        file_alias = upload(filename, filehandle, size)
    except UploadFailed, e:
        logger.error('Uploading to the Librarian failed: %s', e)
        raise
    except:
        logger.exception('Uncaught exception while uploading to the Librarian')
        raise

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

def send_mail(sender, recipients, mail):
    """Send a mail message via the local host's SMTP server."""
    client = smtplib.SMTP()
    client.connect()
    client.sendmail(sender, recipients, mail)

def logged_send_mail(sender, recipients, mail, logger):
    """As send_mail(), except that errors are logged."""

    try:
        send_mail(sender, recipients, mail)
    except smtplib.SMTPException, e:
        logger.error('Failed to send notification email: %s', e)
        raise
    except:
        logger.exception(
            'Uncaught exception while sending notification email')
        raise

def main(argv):
    initZopeless()
    execute_zcml_for_scripts()

    options, distribution_name, release_name = parse_options(argv[1:])

    logger = make_logger()
    logger.info('Exporting translations for release %s of distribution %s',
        distribution_name, release_name)

    # Bare except statements are used in order to prevent premature
    # termination of the script.

    # Export the translations to a tarball.

    try:
        filehandle, size = logged_export(
            distribution_name, release_name, logger)
    except:
        return 1

    # Upload the tarball to the librarian.

    filename = '%s-%s-translations.tar.gz' % (distribution_name, release_name)

    try:
        file_alias = logged_upload(filename, filehandle, size, logger)
    except:
        return 1

    logger.info('Upload complete, file alias: %s', file_alias)

    if options.email_adresses:
        # Send a notification email.

        sender='rosetta@canonical.com'
        mail = compose_mail(
            sender=sender,
            recipients=options.email_adresses,
            headers={'Subject': 'Language pack export completed'},
            body=
                'Distribution: %s\n'
                'Release: %s\n'
                'Librarian file alias: %s\n'
                % (distribution_name, release_name, file_alias)
            )

        try:
            logged_send_mail(sender, options.email_adresses, mail, logger)
        except:
            return 1

    # Return a success code.

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

