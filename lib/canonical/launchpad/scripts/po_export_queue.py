# Copyright 2005 Canonical Ltd. All rights reserved.

import tarfile
import tempfile

from zope.component import getUtility

from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.helpers import tar_add_file, getRawFileData, \
    join_lines
from canonical.launchpad.interfaces import IPOExportRequestSet, \
    IPOTemplate, IPOFile, ILibraryFileAliasSet, ZeroLengthPOExportError

def get_object_name_and_url(person, potemplate, object):
    """Return the name and URL of the given object.

    This object must be either a PO template or a PO file.
    """

    if IPOTemplate.providedBy(object):
        alias = object.rawfile
    elif IPOFile.providedBy(object):
        object.export()
        alias = object.exportfile
    else:
        raise TypeError("Can't export object", object)

    return (potemplate.potemplatename.name, alias.url)

def pofile_filename(pofile):
    """Return a filename for a PO file."""

    if pofile.variant is not None:
        return '%s@%s.po' % (
            pofile.language.code, pofile.variant.encode('UTF-8'))
    else:
        return '%s.po' % pofile.language.code

def process_multi_object_request(person, potemplate, objects):
    """Process an export request for many objects.

    This function creates a tarball with all the objects requested, puts it in
    the Librarian, and returns a tuple containing a name for the tarball and
    its Librarian URL. Each of the objects must be either a PO template or a
    PO file.
    """

    name = potemplate.potemplatename.name
    filehandle = tempfile.TemporaryFile()
    archive = tarfile.open('', 'w:gz', filehandle)

    for object in objects:
        if IPOTemplate.providedBy(object):
            filename = name + '.pot'
            contents = getRawFileData(object)
        elif IPOFile.providedBy(object):
            filename = pofile_filename(object)
            contents = object.export()
        else:
            raise TypeError("Can't export object", object)

        tar_add_file(archive, 'rosetta-%s/%s' % (name, filename), contents)

    archive.close()
    size = filehandle.tell()
    filehandle.seek(0)

    alias_set = getUtility(ILibraryFileAliasSet)
    alias = alias_set.create(
        name='rosetta-%s.tar.gz' % name,
        size=size,
        file=filehandle,
        contentType='application/octet-stream')
    return (name, alias.url)

def process_request(person, potemplate, objects):
    """Process a request for an export of Rosetta files."""

    if len(objects) == 1:
        name, url = get_object_name_and_url(
            person, potemplate, objects[0])
    else:
        name, url = process_multi_object_request(person, potemplate, objects)

    simple_sendmail(
        from_addr='rosetta@canonical.com',
        to_addrs=[person.preferredemail.email],
        subject='Rosetta PO export request: %s' % name,
        body=join_lines(
            '',
            'Hello %s,' % person.displayname,
            '',
            'The files you requested from Rosetta are ready for download',
            'from the following location:',
            '',
            '    %s' % url,
            ''))

def process_queue(transaction_manager):
    """Process each request in the PO export queue.

    Each item is removed from the queue as it is processed, so the queue will
    be empty when this function returns.
    """

    request_set = getUtility(IPOExportRequestSet)

    while True:
        request = request_set.popRequest()

        if request is None:
            return

        person, potemplate, objects = request

        try:
            process_request(person, potemplate, objects)
        except ZeroLengthPOExportError:
            # XXX
            # This is a temporary workaround for a problem where the export
            # code sometimes generates a zero-length PO file, which the
            # Librarian will refuse to accept.
            # -- Dafydd Harries, 2005/06/16
            pass

        # This is here in case we need to process the same file twice in the
        # same queue run. If we try to do that all in one transaction, the
        # second time we get to the file we'll get a Librarian lookup error
        # because files are not accessible in the same transaction as they're
        # created.

        transaction_manager.commit()

