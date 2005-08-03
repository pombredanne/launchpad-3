# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

import tempfile
from StringIO import StringIO

from zope.component import getUtility

from canonical.lp.dbschema import RosettaFileFormat
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.helpers import (
    getRawFileData, join_lines, RosettaWriteTarFile)
from canonical.launchpad.components.poexport import MOCompiler
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

        if is_potemplate(self.obj):
            return getRawFileData(self.obj)
        else:
            return self.obj.export()

    def get_librarian_url(self):
        """Return a Librarian URL from which the exported file can be
        downloaded.
        """

        if is_potemplate(self.obj):
            return self.obj.rawfile.url
        else:
            self.obj.export()
            return self.obj.exportfile.url

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
            return alias.url

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

    def __init__(self, name, url=None, successes=None, failures=None):
        if not (url or failures):
            raise ValueError(
                "An export result must have an URL or failures (or both).")

        if (url and not successes) or (not url and successes):
            raise ValueError(
                "Can't have a URL without successes (or vice versa).")

        self.name = name
        self.url = url
        self.failures = failures or []
        self.successes = successes or []

    def notify(self, person):
        """Send a notification email to the given person about the export.

        If there were failures, a copy of the email is also sent to the
        Launchpad error mailing list.
        """

        name = person.browsername
        success_count = len(self.successes)
        total_count = success_count + len(self.failures)

        if self.failures and self.url:
            failure_list = '\n'.join([
                ' * ' + failure
                for failure in self.failures])

            body = join_lines(
                '',
                'Hello %s,' % name,
                '',
                'Rosetta has finished exporting your requested files.',
                'However, problems were encountered exporting the',
                'following files:',
                '',
                failure_list,
                '',
                'The Rosetta team has been notified of this problem. Please',
                'reply to this email for further assistance. Of the %d files',
                'you requested, Rosetta successfully exported %d, which can',
                'be downloaded from the following location:',
                '',
                '    %s')
            body %= (total_count, success_count, self.url)
        elif self.failures:
            body = join_lines(
                '',
                'Hello %s,' % name,
                '',
                'Rosetta encountered problems exporting the files you',
                'requested. The Rosetta team has been notified of this',
                'problem. Please reply to this email for further assistance.')
        else:
            body = join_lines(
                '',
                'Hello %s,' % name,
                '',
                'The files you requested from Rosetta are ready for download',
                'from the following location:',
                '',
                '    %s' % self.url)

        error_address = 'launchpad-error-reports@lists.canonical.com'

        if self.failures:
            recipients = [person.preferredemail.email, error_address]
        else:
            recipients = [person.preferredemail.email]

        for recipient in recipients:
            simple_sendmail(
                from_addr='rosetta@canonical.com',
                to_addrs=[recipient],
                subject='Rosetta PO export request: %s' % self.name,
                body=body)

def process_single_object_request(obj, format, logger):
    """Process a request for a single object.

    Returns an ExportResult object. The object must be a PO template or a PO
    file.
    """

    handler = get_handler(format, obj)
    name = handler.get_name()

    try:
        url = handler.get_librarian_url()
    except:
        logger.exception("PO export failed for %s/%s" %
            (name, handler.get_filename()))
        return ExportResult(name, failures=[obj])
    else:
        return ExportResult(name, url=url, successes=[obj])

def process_multi_object_request(objects, format, logger):
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
    successes = []
    failures = []

    for obj in objects:
        handler = get_handler(format, obj)
        filename = handler.get_filename()

        try:
            contents = handler.get_contents()
        except:
            logger.exception("PO export failed for %s/%s" % (name, filename))
            failures.append(filename)
        else:
            successes.append(filename)
            archive.add_file('rosetta-%s/%s' % (name, filename), contents)

    archive.close()
    size = filehandle.tell()
    filehandle.seek(0)

    if successes:
        alias_set = getUtility(ILibraryFileAliasSet)
        alias = alias_set.create(
            name='rosetta-%s.tar.gz' % name,
            size=size,
            file=filehandle,
            contentType='application/octet-stream')
        return ExportResult(
            name, url=alias.url, successes=successes, failures=failures)
    else:
        return ExportResult(name, failures=failures)

def process_request(person, objects, format, logger):
    """Process a request for an export of Rosetta files.

    After processing the request a notification email is sent to the requester
    with the URL to retrieve the file (or the tarball, in case of a request of
    multiple files) and information about files that we failed to export (if
    any).
    """

    if len(objects) == 1:
        result = process_single_object_request(objects[0], format, logger)
    else:
        result = process_multi_object_request(objects, format, logger)

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
        logger.debug('Exporting objects for person %d, PO template %d' %
            (person.id, potemplate.id))

        process_request(person, objects, format, logger)

        # This is here in case we need to process the same file twice in the
        # same queue run. If we try to do that all in one transaction, the
        # second time we get to the file we'll get a Librarian lookup error
        # because files are not accessible in the same transaction as they're
        # created.

        transaction_manager.commit()

