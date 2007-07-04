# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

import os
import psycopg
import textwrap
import traceback
from StringIO import StringIO
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    ILibraryFileAliasSet, IPOExportRequestSet, ITranslationExporter,
    ITranslationFile)
from canonical.launchpad.mail import simple_sendmail


class ExportResult:
    """The results of a translation export request.

    This class has three main attributes:

     - name: A short identifying string for this export.
     - url: The Librarian URL for any successfully exported files.
     - failures: A list of filenames for failed exports.
    """

    def __init__(self, name):
        self.name = name
        self.url = None
        self.failures = {}
        self.successes = []

    def _getErrorLines(self):
        """Return a string with logging information about errors.

        That logging information contains error messages got while doing the
        export.
        """
        # Look for any export that is success but got any warning that we
        # should show to the user.
        return '\n'.join([
            '%s:\n%s\n\n' % (failure_key, failure_value)
            for failure_key, failure_value in self.failures.iteritems()
            ])

    def _getFailureEmailBody(self, person):
        """Send an email notification about the export failing."""
        return textwrap.dedent('''
            Hello %s,

            Rosetta encountered problems exporting the files you
            requested. The Rosetta team has been notified of this
            problem. Please reply to this email for further assistance.''' %
                person.browsername)

    def _getPartialSuccessEmailBody(self, person):
        """Send an email notification about the export working partially."""
        # Get a list of files that failed.
        failure_list = '\n'.join([
            ' * %s' % failure
            for failure in self.failures.keys()])

        success_count = len(self.successes)
        total_count = success_count + len(self.failures)

        return textwrap.dedent('''
            Hello %s,

            Rosetta has finished exporting your requested files.
            However, problems were encountered exporting the
            following files:

            %s

            The Rosetta team has been notified of this problem. Please
            reply to this email for further assistance.

            Of the %d files you requested, Rosetta successfully exported
            %d, which can be downloaded from the following location:

            \t%s''') % (
                person.browsername, failure_list, total_count, success_count,
                self.url)

    def _getSuccessEmailBody(self, person):
        """Send an email notification about the export working."""
        return textwrap.dedent('''
            Hello %s,

            The files you requested from Rosetta are ready for download
            from the following location:

            \t%s''' % (person.browsername, self.url)
            )

    def notify(self, person):
        """Send a notification email to the given person about the export.

        If there were failures, a copy of the email is also sent to the
        Launchpad error mailing list for debugging purposes.
        """
        assert self.url or self.failures, (
            'An export result must have an URL or failures (or both).')

        assert ((self.url and self.successes) or
                not (self.url or self.successes)), (
            'Can\'t have a URL without successes (or vice versa).')

        if self.failures and self.url:
            body = self._getPartialSuccessEmailBody(person)
        elif self.failures:
            body = self._getFailureEmailBody(person)
        else:
            # There are no failures, so we have a full export without
            # problems.
            body = self._getSuccessEmailBody(person)

        recipients = list(helpers.contactEmailAddresses(person))

        for recipient in [str(recipient) for recipient in recipients]:
            simple_sendmail(
                from_addr=config.rosetta.rosettaadmin.email,
                to_addrs=[recipient],
                subject='Translation download request: %s' % self.name,
                body=body)

        if len(self.failures) > 0:
            # The export process had errors that we should notify to admins.
            admins_email_body = textwrap.dedent('''
                Hello admins,

                Rosetta encountered problems exporting some files requested by
                %s. This means we have a bug in
                Launchpad that needs to be fixed to be able to proceed with
                this export. You can see the list of failed files with the
                error we got:

                %s''') % (
                    person.browsername, self._getErrorLines())

            simple_sendmail(
                from_addr=config.rosetta.rosettaadmin.email,
                to_addrs=[config.launchpad.errors_address],
                subject='Translation download errors: %s' % self.name,
                body=admins_email_body)

    def addFailure(self, name):
        """Add name as an export that failed.

        The failures are stored at self.failures dictionary using the entry
        that failed as the key and the exception that caused the error as the
        value. If there isn't any warning information, the value is the empty
        string.
        """
        # Get the trace back that produced this failure.
        exception = StringIO()
        traceback.print_exc(file=exception)
        exception.seek(0)
        # And store it.
        self.failures[name] = exception.read()

    def addSuccess(self, name):
        """Add name as an export that succeed.

        The success are stored at self.success list.
        """
        self.successes.append(name)

def process_request(potemplate, person, objects, format, logger):
    """Process a request for an export of Launchpad translation files.

    After processing the request a notification email is sent to the requester
    with the URL to retrieve the file (or the tarball, in case of a request of
    multiple files) and information about files that we failed to export (if
    any).
    """
    translation_exporter = getUtility(ITranslationExporter)
    translation_format_exporter = (
        translation_exporter.getTranslationFormatExporterByFileFormat(format))

    result = ExportResult('XXX')
    translation_file_list = []
    for obj in objects:
        translation_file_list.append(ITranslationFile(obj))

    try:
        exported_file = translation_format_exporter.exportTranslationFiles(
            translation_file_list)
    except (KeyboardInterrupt, SystemExit):
        # We should never catch KeyboardInterrupt or SystemExit.
        raise
    except psycopg.Error:
        # It's a DB exception, we don't catch it either, the export
        # should be done again in a new transaction.
        raise
    except:
        # The export for the current entry failed with an unexpected
        # error, we add the entry to the list of errors.
        result.addFailure('XXX')
        # And log the error.
        logger.error(
            "A unexpected exception was raised when exporting %s" % (
                obj.title),
            exc_info=True)
    else:
        result.addSuccess('XXX')
        #archive.add_file('rosetta-%s/%s' % (name, filename), contents)

    if result.successes:
        if exported_file.path is None:
            # The exported path is unknown, use translation domain as its
            # filename.
            assert exported_file.file_extension, (
                'File extension must have a value!.')
            exported_file.path = 'launchpad-%s.%s' % (
                potemplate.potemplatename.translationdomain,
                exported_file.file_extension)
        else:
            # We only use basename.
            exported_file.path = os.path.basename(exported_file.path)

        alias_set = getUtility(ILibraryFileAliasSet)
        alias = alias_set.create(
            name=exported_file.path,
            size=exported_file.content.len,
            file=exported_file.content,
            contentType=exported_file.content_type)
        result.url = alias.http_url

    result.notify(person)

def process_queue(transaction_manager, logger):
    """Process each request in the translation export queue.

    Each item is removed from the queue as it is processed, so the queue will
    be empty when this function returns.
    """
    request_set = getUtility(IPOExportRequestSet)

    while True:
        request = request_set.popRequest()

        if request is None:
            return

        person, potemplate, objects, format = request
        logger.debug('Exporting objects for %s, related to template %s' % (
            person.displayname, potemplate.displayname))

        try:
            process_request(potemplate, person, objects, format, logger)
        except psycopg.Error:
            # We had a DB error, we don't try to recover it here, just exit
            # from the script and next run will retry the export.
            logger.error(
                "A DB exception was raised when exporting files for %s" % (
                    person.displayname),
                exc_info=True)
            transaction_manager.abort()
            break

        # This is here in case we need to process the same file twice in the
        # same queue run. If we try to do that all in one transaction, the
        # second time we get to the file we'll get a Librarian lookup error
        # because files are not accessible in the same transaction as they're
        # created.
        transaction_manager.commit()
