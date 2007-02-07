# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

import tempfile
import textwrap
import os.path
import traceback
import psycopg

from StringIO import StringIO
from zipfile import ZipFile
from xml.parsers.xmlproc.xmldtd import load_dtd_string

from zope.component import getUtility

from canonical.config import config
from canonical.lp.dbschema import RosettaFileFormat
from canonical.launchpad import helpers
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.components.poexport import (
    MOCompiler, RosettaWriteTarFile)
from canonical.launchpad.interfaces import (
    IPOExportRequestSet, IPOTemplate, IPOFile, ILibraryFileAliasSet,
    IPOSubmission)

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



class XPIFormatHandler(Handler):
    """Export handler for Mozilla XPI format exports."""

    def get_filename(self):
        """Return a filename for the file being exported."""

        if is_potemplate(self.obj):
            return 'en-US.xpi'
        else:
            return os.path.basename(self.obj.path)

    def get_contents(self):
        """Return the contents of the exported file."""
        import sys

        if is_potemplate(self.obj):
            return self.obj.source_file.read()
        else:
            template = StringIO(self.obj.potemplate.source_file.read())
            mozexport = MozillaZipFile(template, self.obj)
            return mozexport.get_contents()

    def get_librarian_url(self):
        """Return a Librarian URL from which the exported file can be
        downloaded.
        """

        if is_potemplate(self.obj):
            return self.obj.source_file.url
        else:
            xpi_contents = self.get_contents()
            alias_set = getUtility(ILibraryFileAliasSet)
            alias = alias_set.create(
                name=self.get_filename(),
                size=len(xpi_contents),
                file=StringIO(xpi_contents),
                contentType='application/zip')
            return alias.url

class MozillaLocalizableFile:
    """Class for updating translatable messages in different files.

    It expects `_file' to be a StringIO (i.e. provide getvalue() method).
    """

    def __init__(self):
        self._file = None

    def get_contents(self):
        if self._file:
            return self._file.getvalue()
        else:
            return None

    def get_pofile_translation(self, pofile, key):
        if not key: return None
        potmsgset = pofile.potemplate.getPOTMsgSetByAlternativeMsgID(key)
        if not potmsgset:
            return None
        pomsgset = potmsgset.getPOMsgSet(
            pofile.language.code, pofile.variant)
        if pomsgset is None:
            return None
        # Prefer Rosetta/active submission
        submission = pomsgset.getActiveSubmission(0)
        if submission is None:
            # If there is no active submission, upstream/published one will do
            submission = pomsgset.getPublishedSubmission(0)
        if submission is not None and IPOSubmission.providedBy(submission):
            return submission.potranslation.translation
        else:
            return None

class MozillaZipFile (MozillaLocalizableFile):
    """Class for updating translatable messages in Mozilla XPI/JAR files.

    It expects `file' parameter to be a StringIO class.
    """

    def __init__(self, file, pofile):
        MozillaLocalizableFile.__init__(self)
        self._file = file

        # XXX (Danilo): ZIP seems to double in size with simple
        # .writestr()s.  We probably need to clear previous entries
        # in the ZIP file first: it seems to only way to do this
        # is to create entirely new ZIP file.
        zip = ZipFile(self._file, 'a')
        for filename in zip.namelist():
            if filename.endswith('.properties'):
                data = zip.read(filename)
                pf = MozillaPropertyFile(file=StringIO(data), pofile=pofile)
                zip.writestr(zip.getinfo(filename), pf.get_contents())
                pass
            elif filename.endswith('.dtd'):
                data = zip.read(filename)
                dtdf = MozillaDtdFile(file=StringIO(data), pofile=pofile)
                zip.writestr(zip.getinfo(filename), dtdf.get_contents())
            elif filename.endswith('.jar'):
                data = zip.read(filename)
                jarf = MozillaZipFile(file=StringIO(data), pofile=pofile)
                zip.writestr(zip.getinfo(filename), jarf.get_contents())
            elif filename == 'install.rdf':
                data = zip.read(filename)
                product_guid_re = re.compile("<em:id>({.*})</em:id>")
                r = product_guid_re.search(data)
                if r:
                    product_guid = r.groups()[0]

                #zip.writestr(zip.getinfo(file), "blablabla")
                # XXX (Danilo): need to implement install.rdf updater
                pass
        zip.close()

    def create_install_rdf(self, pofile, product_guid): 
       all = """<?xml version="1.0"?>
<RDF xmlns="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:em="http://www.mozilla.org/2004/em-rdf#">
  <Description about="urn:mozilla:install-manifest"
               em:id="langpack-%s@firefox.mozilla.org"
               em:name="%s (%s) Language Pack"
               em:version="2.0"
               em:type="8"
               em:creator="Rosetta">
    <em:contributor>Данило Шеган</em:contributor> 
    <em:contributor>Carlos Perelló Marín</em:contributor>

    <em:targetApplication>
      <Description>
        <em:id>{ec8030f7-c20a-464f-9b0e-13a3a9e97384}</em:id><!-- firefox -->
        <em:minVersion>2.0</em:minVersion>
        <em:maxVersion>2.0.0.*</em:maxVersion>
      </Description>
    </em:targetApplication>
  </Description>
</RDF>
"""

class MozillaDtdFile (MozillaLocalizableFile):
    """Class for updating translatable messages in a .dtd file.

    `file' should be a file-like object.
    """
    def __init__(self, file, pofile):
        # XXX (Danilo): This is not the best way, but we don't have
        # a proper DTD editing library. I'll probably go with regex
        # parsing instead.
        self._file = file
        dtd = load_dtd_string(self._file.read())
        rdata = ""
        for entity in dtd.get_general_entities():
            if entity in ['amp', 'lt', 'gt', 'apos', 'quot']:
                continue
            oldvalue = dtd.resolve_ge(entity).value
            translation = self.get_pofile_translation(pofile, entity)
            if not translation:
                translation = oldvalue

            rdata += ("""<!ENTITY %s "%s">\n""" %
                      (entity.encode('utf-8'), translation.encode('utf-8')));

        self._file = StringIO(rdata)



class MozillaPropertyFile (MozillaLocalizableFile):
    """Class for updating translatable messages in a .properties file.

    `file' should be a file-like object.
    """

    def __init__(self, file, pofile):
        """Constructs a dictionary from a .properties file.

        It expects a file-like object "file".
        "filename" is used for source code references.
        """
        self._file = file
        data = file.read()

        # .properties files are defined to be unicode-escaped, but
        # also allow direct UTF-8
        udata = data.decode('utf-8')
        rdata = ""

        lines = udata.split("\n")
        for line in lines:
            # Ignore empty and comment lines
            if not len(line.strip()) or line[0]=='#' or line[0]=='!':
                rdata += line.encode('utf-8') + "\n"
                continue
            (key, oldvalue) = line.split('=', 1)
            translation = self.get_pofile_translation(pofile, key)
            if not translation:
                translation = oldvalue
            rdata += "%s=%s\n" % (key.encode('utf-8'),
                                  translation.encode('unicode_escape'))
        self._file = StringIO(rdata)

format_handlers = {
    RosettaFileFormat.PO: POFormatHandler,
    RosettaFileFormat.MO: MOFormatHandler,
    RosettaFileFormat.XPI: XPIFormatHandler,
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


def process_single_object_request(obj, format, logger):
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
    except psycopg.Error:
        # It's a DB exception, we don't catch it either, the export
        # should be done again in a new transaction.
        raise
    except:
        # The export for the current entry failed with an unexpected error, we
        # add the entry to the list of errors.
        result.addFailure(filename)
        # And log the error.
        logger.error(
            "A unexpected exception was raised when exporting %s" % obj.title,
            exc_info=True)
        return result
    else:
        result.addSuccess(filename)
        return result

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
    result = ExportResult(name)

    for obj in objects:
        handler = get_handler(format, obj)
        filename = handler.get_filename()

        try:
            contents = handler.get_contents()
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
            result.addFailure(filename)
            # And log the error.
            logger.error(
                "A unexpected exception was raised when exporting %s" % (
                    obj.title),
                exc_info=True)
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
        logger.debug('Exporting objects for %s, related to template %s' % (
            person.displayname, potemplate.displayname))

        try:
            process_request(person, objects, format, logger)
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

