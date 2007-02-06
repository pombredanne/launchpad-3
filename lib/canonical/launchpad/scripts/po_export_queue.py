# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

import tempfile
import textwrap
import traceback
from StringIO import StringIO

from psycopg import ProgrammingError
from zope.component import getUtility

from canonical.config import config
from canonical.lp.dbschema import RosettaFileFormat
from canonical.launchpad import helpers
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.components.poexport import (
    MOCompiler, RosettaWriteTarFile)
from canonical.launchpad.interfaces import (
    IPOExportRequestSet, IPOTemplate, IPOFile, ILibraryFileAliasSet)

def is_potemplate(obj):
    """Return True if the object is a PO template."""
    return IPOTemplate.providedBy(obj)

def is_pofile(obj):
    """Return True if the object is a PO file."""
    return IPOFile.providedBy(obj)

def pofile_filename(pofile):
    """Return a filename for a PO file."""

    if pofile.variant is not None:
        return '%s@%s.po' % (
            pofile.language.code, pofile.variant.encode('UTF-8'))
    else:
        return '%s.po' % pofile.language.code

class Handler:
    """Base export handler class."""

    def __init__(self, obj):
        self.obj = obj

    def get_name(self):
        """Return a name for the export being handled."""

        if is_potemplate(self.obj):
            return self.obj.potemplatename.name
        else:
            return self.obj.potemplate.potemplatename.name

class POFormatHandler(Handler):
    """Export handler for PO format exports."""

    def get_filename(self):
        """Return a filename for the file being exported."""

        if is_potemplate(self.obj):
            return self.obj.potemplatename.name + '.pot'
        else:
            return pofile_filename(self.obj)

    def get_contents(self):
        """Return the contents of the exported file."""
        return self.obj.export()

    def get_librarian_url(self):
        """Return a Librarian URL from which the exported file can be
        downloaded.
        """

        if is_potemplate(self.obj):
            potemplate_content = self.obj.export()
            alias_set = getUtility(ILibraryFileAliasSet)
            alias = alias_set.create(
                name='%s.pot' % self.obj.potemplatename.name,
                size=len(potemplate_content),
                file=StringIO(potemplate_content),
                contentType='application/x-po')
            return alias.http_url
        else:
            self.obj.export()
            return self.obj.exportfile.http_url

class MOFormatHandler(Handler):
    """Export handler for MO format exports."""

    def get_filename(self):
        """Return a filename for the file being exported."""

        if is_potemplate(self.obj):
            return POFormatHandler(self.obj).get_filename()
        else:
            po_filename = POFormatHandler(self.obj).get_filename()
            return po_filename[:-3] + '.mo'

    def get_contents(self):
        """Return the contents of the exported file."""

        if is_potemplate(self.obj):
            return POFormatHandler(self.obj).get_contents()
        else:
            po_contents = POFormatHandler(self.obj).get_contents()
            compiler = MOCompiler()
            return compiler.compile(po_contents)

    def get_librarian_url(self):
        """Return a Librarian URL from which the exported file can be
        downloaded.
        """

        if is_potemplate(self.obj):
            return POFormatHandler(self.obj).get_librarian_url()
        else:
            mo_contents = self.get_contents()
            alias_set = getUtility(ILibraryFileAliasSet)
            alias = alias_set.create(
                name=self.get_filename(),
                size=len(mo_contents),
                file=StringIO(mo_contents),
                contentType='application/octet-stream')
            return alias.http_url

format_handlers = {
    RosettaFileFormat.PO: POFormatHandler,
    RosettaFileFormat.MO: MOFormatHandler,
}

class UnsupportedExportObject(Exception):
    pass

class UnsupportedExportFormat(Exception):
    pass

def get_handler(format, obj):
    """Get an export handler for the given format and object."""

    if not (is_potemplate(obj) or is_pofile(obj)):
        raise UnsupportedExportObject

    if format not in format_handlers:
        raise UnsupportedExportFormat

    return format_handlers[format](obj)

class ExportResult:
    """The results of a PO export request.

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
                from_addr='Rosetta SWAT Team <%s>' % (
                    config.rosetta.rosettaadmin.email),
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
                from_addr='Rosetta SWAT Team <%s>' % (
                    config.rosetta.rosettaadmin.email),
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


def process_single_object_request(obj, format):
    """Process a request for a single object.

    Returns an ExportResult object. The object must be a PO template or a PO
    file.
    """

    handler = get_handler(format, obj)
    name = handler.get_name()
    filename = handler.get_filename()
    result = ExportResult(name)

    try:
        result.url = handler.get_librarian_url()
    except (KeyboardInterrupt, SystemExit):
        # We should never catch KeyboardInterrupt or SystemExit.
        raise
    except ProgrammingError:
        # It's a DB exception, we don't catch it either, the export
        # should be done again in a new transaction.
        raise
    except:
        # The export for the current entry failed with an unexpected error, we
        # add the entry to the list of errors.
        result.addFailure(filename)
        return result
    else:
        result.addSuccess(filename)
        return result

def process_multi_object_request(objects, format):
    """Process an export request for many objects.

    This function creates a tarball containing all of the objects requested,
    puts it in the Librarian, and returns an ExportResult object with the
    Librarian URL of the tarball. Each of the objects must be either a PO
    template or a PO file.
    """

    assert len(objects) > 1

    name = get_handler(format, objects[0]).get_name()
    filehandle = tempfile.TemporaryFile()
    archive = RosettaWriteTarFile(filehandle)
    result = ExportResult(name)

    for obj in objects:
        handler = get_handler(format, obj)
        filename = handler.get_filename()

        try:
            contents = handler.get_contents()
        except (KeyboardInterrupt, SystemExit):
            # We should never catch KeyboardInterrupt or SystemExit.
            raise
        except ProgrammingError:
            # It's a DB exception, we don't catch it either, the export
            # should be done again in a new transaction.
            raise
        except:
            # The export for the current entry failed with an unexpected error, we
            # add the entry to the list of errors.
            result.addFailure(filename)
        else:
            result.addSuccess(filename)
            archive.add_file('rosetta-%s/%s' % (name, filename), contents)

    archive.close()
    size = filehandle.tell()
    filehandle.seek(0)

    if result.successes:
        alias_set = getUtility(ILibraryFileAliasSet)
        alias = alias_set.create(
            name='rosetta-%s.tar.gz' % name,
            size=size,
            file=filehandle,
            contentType='application/octet-stream')
        result.url = alias.http_url

    return result

def process_request(person, objects, format):
    """Process a request for an export of Rosetta files.

    After processing the request a notification email is sent to the requester
    with the URL to retrieve the file (or the tarball, in case of a request of
    multiple files) and information about files that we failed to export (if
    any).
    """

    if len(objects) == 1:
        result = process_single_object_request(objects[0], format)
    else:
        result = process_multi_object_request(objects, format)

    result.notify(person)

def process_queue(transaction_manager, logger):
    """Process each request in the PO export queue.

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
            process_request(person, objects, format)
        except ProgrammingError:
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

