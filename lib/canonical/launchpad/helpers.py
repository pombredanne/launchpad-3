# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Various functions and classes that are useful across different parts of
launchpad.

Do not simply dump stuff in here.  Think carefully as to whether it would
be better as a method on an existing content object or IFooSet object.
"""

__metaclass__ = type

import base64
import email
import gettextpo
import os
import random
import re
import sha
import tarfile
import time
import warnings
from StringIO import StringIO
from select import select
from math import ceil
from xml.sax.saxutils import escape as xml_escape
from difflib import unified_diff

from zope.component import getUtility
from zope.interface import implements, providedBy, directlyProvides
from zope.interface.interfaces import IInterface
from zope.security.interfaces import IParticipation
from zope.security.management import (
    newInteraction, endInteraction, checkPermission as zcheckPermission)
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.app.security.permission import (
    checkPermission as check_permission_is_registered)

import canonical.base
from canonical.database.constants import UTC_NOW
from canonical.lp.dbschema import (RosettaImportStatus, TranslationPermission,
                                   SourcePackageFileType, BinaryPackageFormat,
                                   BinaryPackageFileType)
from canonical.librarian.interfaces import (
    ILibrarianClient, UploadFailed, DownloadFailed
    )
from canonical.launchpad.interfaces import (
    ILaunchBag, IOpenLaunchBag, IHasOwner, IGeoIP, IRequestPreferredLanguages,
    ILanguageSet, IRequestLocalLanguages, RawFileAttachFailed, ITeam,
    RawFileFetchFailed, ILoginTokenSet
    )
from canonical.launchpad.components.poparser import (
    POSyntaxError, POInvalidInputError, POParser
    )
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.mail import SignedMessage
from canonical.launchpad.mail.ftests import testmails_path

from canonical.launchpad.validators.gpg import valid_fingerprint


def text_replaced(text, replacements, _cache={}):
    """Return a new string with text replaced according to the dict provided.

    The keys of the dict are substrings to find, the values are what to replace
    found substrings with.

    >>> text_replaced('', {'a':'b'})
    ''
    >>> text_replaced('a', {'a':'c'})
    'c'
    >>> text_replaced('faa bar baz', {'a': 'A', 'aa': 'X'})
    'fX bAr bAz'
    >>> text_replaced('1 2 3 4', {'1': '2', '2': '1'})
    '2 1 3 4'

    The argument _cache is used as a cache of replacements that were requested
    before, so we only compute regular expressions once.

    """
    assert replacements, "The replacements dict must not be empty."
    # The ordering of keys and values in the tuple will be consistent within a
    # single Python process.
    cachekey = tuple(replacements.items())
    if cachekey not in _cache:
        L = []
        for find, replace in sorted(replacements.items(),
                                    key=lambda (key, value): len(key),
                                    reverse=True):
            L.append('(%s)' % re.escape(find))
        # Make a copy of the replacements dict, as it is mutable, but we're
        # keeping a cached reference to it.
        replacements_copy = dict(replacements)
        def matchobj_replacer(matchobj):
            return replacements_copy[matchobj.group()]
        regexsub = re.compile('|'.join(L)).sub
        def replacer(s):
            return regexsub(matchobj_replacer, s)
        _cache[cachekey] = replacer

    return _cache[cachekey](text)

CHARACTERS_PER_LINE = 50

class TranslationConstants:
    """Set of constants used inside the context of translations."""

    SINGULAR_FORM = 0
    PLURAL_FORM = 1
    SPACE_CHAR = u'<span class="po-message-special">\u2022</span>'
    NEWLINE_CHAR = u'<span class="po-message-special">\u21b5</span><br/>\n'


class RosettaReadTarFile:
    """Wrapper around the tarfile module.

    This class provides implements a variety tar file processing used by
    Rosetta. As opposed to RosettaWriteTarFile, which creates new archives,
    this class only reads existing ones.
    """

    def __init__(self, stream=None, data=None, archive=None):
        if len([thing for thing in (stream, data, archive) if thing]) != 1:
            raise TypeError(
                "Must provide either a stream or a data string or a tarfile.")

        if stream:
            self.tarfile = tarfile.open('', 'r', stream)
        elif data:
            self.tarfile = tarfile.open('', 'r', StringIO(data))
        elif archive:
            self.tarfile = archive

    def find_po_directories(self):
        """Find all directories named 'po' in a tarfile."""

        return [
            member.name
            for member in self.tarfile.getmembers()
            if member.isdir()
            and os.path.basename(member.name.strip("/")) == 'po'
            ]

    def examine(self):
        """Find POT and PO files within a tar file object.

        Return a tuple with the list of .pot files and the list of .po files
        found.

        Two methods of finding files are employed:

         1. Directories named 'po' are searched for in the tar file, and if
            there is exactly one non-empty such directory, it is searched for
            files ending in '.pot' and '.po'.

         2. Otherwise, files ending in '.pot' and '.po' are searched for
            directly.
        """

        # All files in the tarfile.

        names = self.tarfile.getnames()

        # Directories named 'po' in the tarfile.

        po_directories = self.find_po_directories()

        if po_directories:
            # Look for interesting PO directories. (I.e. ones that contain POT
            # or PO files.)

            interesting = []

            for directory in po_directories:
                for name in names:
                    if name != directory and name.startswith(directory) and (
                        name.endswith('.pot') or name.endswith('.po')):
                        if directory not in interesting:
                            interesting.append(directory)

            # If there's exactly one interesting PO directory, get a list of
            # all the interesting files in it. Otherwise, use method 2.

            if len(interesting) == 1:
                directory = interesting[0]
                pot_files, po_files = [], []

                for name in names:
                    if name.startswith(directory):
                        if name.endswith('.pot'):
                            pot_files.append(name)
                        elif name.endswith('.po'):
                            po_files.append(name)

                return (tuple(pot_files), tuple(po_files))

        # All files which look interesting.

        pot_files = [name for name in names if name.endswith('.pot')]

        po_files =  [name for name in names if name.endswith('.po')]

        return (tuple(pot_files), tuple(po_files))

    def check_for_import(self, pot_paths, po_paths):
        """Check whether this tar file is suitable for importing into Rosetta.

        Returns an error message if a problem was detected, or None otherwise.
        """

        # Check that at most one .pot file was found.
        if len(pot_paths) > 1:
            return (
                "More than one PO template was found in the tar file you "
                "uploaded. This is not currently supported.")

        # Check the syntax of the .pot file, if present.
        if len(pot_paths) > 0:
            pot_contents = self.tarfile.extractfile(pot_paths[0]).read()

            if not check_po_syntax(pot_contents):
                return (
                    "There was a problem parsing the PO template file in the "
                    "tar file you uploaded.")

        # Complain if no files at all were found.
        if len(pot_paths) == 0 and len(po_paths) == 0:
            return (
                "The tar file you uploaded could not be imported. This may be "
                "because there was more than one 'po' directory, or because "
                "the PO templates and PO files found did not share a common "
                "location.")

        return None

    def do_import(self, potemplate, importer, pot_paths, po_paths):
        """Import a tar file into Rosetta.

        Extract PO templates and PO files from the paths specified.
        A status message is returned.

        Currently, it is assumed that since check_for_import() will have been
        called before import(), checking the syntax of the PO template will
        not be necessary and also, we are 100% sure there is one .pot file and
        only one. The syntax of PO files is checked, but errors are not fatal.
        """

        # At this point we are only getting one .pot file so this should be
        # safe. # We don't support other kinds of tarballs and before calling
        # this function we did already the needed tests to be sure that
        # pot_paths follows our requirements.
        potemplate.attachRawFileData(
            contents=self.tarfile.extractfile(pot_paths[0]).read(),
            published=True,
            importer=importer)
        pot_base_dir = os.path.dirname(pot_paths[0])

        # List of .pot and .po files that were not able to be imported.
        errors = []

        for path in po_paths:
            if pot_base_dir != os.path.dirname(path):
                # The po file is not inside the same directory than the pot
                # file, we ignore it.
                errors.append(path)
                continue

            contents = self.tarfile.extractfile(path).read()

            basename = os.path.basename(path)
            root, extension = os.path.splitext(basename)

            if '@' in root:
                # PO files with variants are not currently supported. If they
                # were, we would use some code like this:
                #
                #   code, variant = [ unicode(x) for x in root.split('@', 1) ]

                continue
            else:
                code, variant = root, None

            pofile = potemplate.getOrCreatePOFile(code, variant, importer)

            try:
                # we are assming that a tarball import is ALWAYS of a
                # "published" potemplate and "published" pofiles
                pofile.attachRawFileData(contents, True, importer)
            except (POSyntaxError, POInvalidInputError):
                errors.append(path)
                continue

        message = ("%d files were queued for import from the tar file you "
            "uploaded." % (len(pot_paths + po_paths) - len(errors)))

        if errors != []:
            message += (
                "The following files were skipped due to syntax errors or "
                "other problems: " + ', '.join(errors) + ".")

        return message

class SnapshotCreationError(Exception):
    """Something went wrong while creating a snapshot."""

class Snapshot:
    """Provides a simple snapshot of the given object.

    The snapshot will have the attributes given in attributenames. It
    will also provide the same interfaces as the original object. 
    """
    def __init__(self, ob, names=None, providing=None):
        if names is None and providing is None:
            raise SnapshotCreationError(
                "You have to specify either 'names' or 'providing'.")
        if IInterface.providedBy(providing):
            providing = [providing]
        if names is None:
            names = set()
            for iface in providing:
                names.update(iface.names(all=True))

        for name in names:
            #XXX: Need to check if the attribute exists, since
            #     Person doesn't provides all attributes in
            #     IPerson. -- Bjorn Tillenius, 2005-04-20
            if hasattr(ob, name):
                setattr(self, name, getattr(ob, name))
        if providing is not None:
            directlyProvides(self, providing)


def get_attribute_names(ob):
    """Gets all the attribute names ob provides.

    It loops through all the interfaces that ob provides, and returns all the
    attribute names specified in the interfaces.

        >>> from zope.interface import Interface, implements, Attribute
        >>> class IFoo(Interface):
        ...     foo = Attribute('Foo') 
        ...     baz = Attribute('Baz')
        >>> class IBar(Interface):
        ...     bar = Attribute('Bar')
        ...     baz = Attribute('Baz')
        >>> class FooBar:
        ...     implements(IFoo, IBar)
        >>> attribute_names = get_attribute_names(FooBar())
        >>> attribute_names.sort()
        >>> attribute_names
        ['bar', 'baz', 'foo']
    """
    ifaces = providedBy(ob)
    names = set()
    for iface in ifaces:
        names.update(iface.names(all=True))
    return list(names)

class RosettaWriteTarFile:
    """Convenience wrapper around the tarfile module.

    This class makes it convenient to generate tar files in various ways.
    """

    def __init__(self, stream):
        self.tarfile = tarfile.open('', 'w:gz', stream)
        self.closed = False

    @classmethod
    def files_to_stream(cls, files):
        """Turn a dictionary of files into a data stream."""
        buffer = StringIO()
        archive = cls(buffer)
        archive.add_files(files)
        archive.close()
        buffer.seek(0)
        return buffer

    @classmethod
    def files_to_string(cls, files):
        """Turn a dictionary of files into a data string."""
        return cls.files_to_stream(files).read()

    @classmethod
    def files_to_tarfile(cls, files):
        """Turn a dictionary of files into a tarfile object."""
        return tarfile.open('', 'r', cls.files_to_stream(files))

    def close(self):
        """Close the archive.

        After the archive is closed, the data written to the filehandle will
        be complete. The archive may not be appended to after it has been
        closed.
        """

        self.tarfile.close()
        self.closed = True

    def add_file(self, path, contents):
        """Add a file to the archive."""

        if self.closed:
            raise RuntimeError("Can't add a file to a closed archive")

        now = int(time.time())
        path_bits = path.split(os.path.sep)

        # Ensure that all the directories in the path are present in the
        # archive.

        for i in range(1, len(path_bits)):
            joined_path = os.path.join(*path_bits[:i])

            try:
                self.tarfile.getmember(joined_path + os.path.sep)
            except KeyError:
                tarinfo = tarfile.TarInfo(joined_path)
                tarinfo.type = tarfile.DIRTYPE
                tarinfo.mtime = now
                self.tarfile.addfile(tarinfo)

        tarinfo = tarfile.TarInfo(path)
        tarinfo.time = now
        tarinfo.mtime = now
        tarinfo.size = len(contents)
        self.tarfile.addfile(tarinfo, StringIO(contents))

    def add_files(self, files):
        """Add a number of files to the archive.

        :files: A dictionary mapping file names to file contents.
        """

        for filename in sorted(files.keys()):
            self.add_file(filename, files[filename])


def is_maintainer(owned_object):
    """Is the logged in user the maintainer of this thing?

    owned_object provides IHasOwner.
    """
    if not IHasOwner.providedBy(owned_object):
        raise TypeError, "Object %s doesn't provide IHasOwner" % repr(owned_object)
    launchbag = getUtility(ILaunchBag)
    if launchbag.user is not None:
        return launchbag.user.inTeam(owned_object.owner)
    else:
        return False

def join_lines(*lines):
    """Concatenate a list of strings, adding a newline at the end of each."""

    return ''.join([ x + '\n' for x in lines ])

def string_to_tarfile(s):
    """Convert a binary string containing a tar file into a tar file obj."""

    return tarfile.open('', 'r', StringIO(s))


def shortest(sequence):
    """Return a list with the shortest items in sequence.

    Return an empty list if the sequence is empty.
    """
    shortest_list = []

    for item in list(sequence):
        new_length = len(item)

        if not shortest_list:
            # First item.
            shortest_list.append(item)
            shortest_length = new_length
        elif new_length == shortest_length:
            # Same length than shortest item found, we append it to the list.
            shortest_list.append(item)
        elif min(new_length, shortest_length) != shortest_length:
            # Shorter than our shortest length found, discard old values.
            shortest_list = [item]
            shortest_length = new_length

    return shortest_list

def getRosettaBestBinaryPackageName(sequence):
    """Return the best binary package name from a list.

    It follows the Rosetta policy:

    We don't need a concrete value from binary package name, we use shortest
    function as a kind of heuristic to choose the shortest binary package
    name that we suppose will be the more descriptive one for our needs with
    PO templates. That's why we get always the first element.
    """
    return shortest(sequence)[0]

def getRosettaBestDomainPath(sequence):
    """Return the best path for a concrete .pot file from a list of paths.

    It follows the Rosetta policy for this path:

    We don't need a concrete value from domain_paths list, we use shortest
    function as a kind of heuristic to choose the shortest path if we have
    more than one, usually, we will have only one element.
    """
    return shortest(sequence)[0]

def getValidNameFromString(invalid_name):
    """Return a valid name based on a string.

    A name in launchpad has a set of restrictions that not all strings follow.
    This function converts any string in another one that follows our name
    restriction rules.

    To know more about all restrictions, please, look at valid_name function
    in the database.
    """
    # All chars should be lower case, underscores and spaces become dashes.
    return text_replaced(invalid_name.lower(), {'_': '-', ' ':'-'})

def browserLanguages(request):
    """Return a list of Language objects based on the browser preferences."""
    return IRequestPreferredLanguages(request).getPreferredLanguages()

def simple_popen2(command, input, in_bufsize=1024, out_bufsize=128):
    """Run a command, give it input on its standard input, and capture its
    standard output.

    Returns the data from standard output.

    This function is needed to avoid certain deadlock situations. For example,
    if you popen2() a command, write its standard input, then read its
    standard output, this can deadlock due to the parent process blocking on
    writing to the child, while the child process is simultaneously blocking
    on writing to its parent. This function avoids that problem by writing and
    reading incrementally.

    When we make Python 2.4 a requirement, this function can probably be
    replaced with something using subprocess.Popen.communicate().
    """

    # Strategy:
    #  - write until there's no more input
    #  - when there's no more input, close the input filehandle
    #  - stop when we receive EOF on the output

    offset = 0
    output = ''
    child_stdin, child_stdout = os.popen2(command)

    while True:
        # We can't select on the input file handle after it has been
        # closed.
        if child_stdin.closed:
            test_writable = []
        else:
            test_writable = [child_stdin]

        readable, writable, erroneous = select(
            [child_stdout], test_writable, [])

        if readable:
            s = child_stdout.read(out_bufsize)
            if s:
                output += s
            else:
                break

        if writable:
            if offset <= len(input):
                child_stdin.write(
                    input[offset:offset+in_bufsize])
                offset += in_bufsize
            else:
                # End of input.
                child_stdin.close()

    return output

def contactEmailAddresses(person):
    """Return a Set of email addresses to contact this Person.

    If <person> has a preferred email, the Set will contain only that
    preferred email. 

    If <person> doesn't have a preferred email but implements ITeam, the 
    Set will contain the preferred email address of each member of <person>.

    Finally, if <person> doesn't have a preferred email neither implement
    ITeam, the Set will be empty.
    """
    emails = set()
    if person.preferredemail is not None:
        emails.add(person.preferredemail.email)
        return emails

    if ITeam.providedBy(person):
        for member in person.activemembers:
            contactAddresses = contactEmailAddresses(member)
            if contactAddresses:
                emails = emails.union(contactAddresses)

    return emails

replacements = {0: {'.': ' |dot| ',
                    '@': ' |at| '},
                1: {'.': ' ! ',
                    '@': ' {} '},
                2: {'.': ' , ',
                    '@': ' % '},
                3: {'.': ' (!) ',
                    '@': ' (at) '},
                4: {'.': ' {dot} ',
                    '@': ' {at} '}
                }

def obfuscateEmail(emailaddr, idx=None):
    """Return an obfuscated version of the provided email address.

    Randomly chose a set of replacements for some email address characters and
    replace them. This will make harder for email harvesters to fetch email
    address from launchpad.

    >>> obfuscateEmail('foo@bar.com', 0)
    'foo |at| bar |dot| com'
    >>> obfuscateEmail('foo.bar@xyz.com.br', 1)
    'foo ! bar {} xyz ! com ! br'
    """
    if idx is None:
        idx = random.randint(0, len(replacements) - 1)
    return text_replaced(emailaddr, replacements[idx])

def convertToHtmlCode(text):
    """Return the given text converted to HTML codes, like &#103;.

    This is usefull to avoid email harvesting, while keeping the email address
    in a form that a 'normal' person can read.
    """
    return ''.join(map(lambda c: "&#%s;" % ord(c), text))

def validate_translation(original, translation, flags):
    """Check with gettext if a translation is correct or not.

    If the translation has a problem, raise gettextpo.error.
    """
    msg = gettextpo.PoMessage()
    msg.set_msgid(original[0])

    if len(original) > 1:
        # It has plural forms.
        msg.set_msgid_plural(original[1])
        for i in range(len(translation)):
            msg.set_msgstr_plural(i, translation[i])
    elif len(translation):
        msg.set_msgstr(translation[0])

    for flag in flags:
        msg.set_format(flag, True)

    # Check the msg.
    msg.check_format()

def shortlist(sequence, longest_expected=15):
    """Return a listified version of sequence.

    If <sequence> has more than <longest_expected> items, a warning is issued.

    >>> shortlist([1, 2])
    [1, 2]

    XXX: Must add a test here for the warning this method can issue.
    """
    L = list(sequence)
    if len(L) > longest_expected:
        warnings.warn("shortlist() should not be used here. It's meant to "
              "listify sequences with no more than %d items." %
              longest_expected)
    return L

def uploadRosettaFile(filename, contents):
    client = getUtility(ILibrarianClient)

    try:
        size = len(contents)
        file = StringIO(contents)

        alias = client.addFile(
            name=filename,
            size=size,
            file=file,
            contentType='application/x-po')
    except UploadFailed, e:
        raise RawFileAttachFailed(str(e))

    return alias

def attachRawFileData(raw_file_data, filename, contents, importer):
    """Attach the contents of a file to a raw file data object."""
    raw_file_data.rawfile = uploadRosettaFile(filename, contents)
    raw_file_data.daterawimport = UTC_NOW
    raw_file_data.rawimporter = importer
    raw_file_data.rawimportstatus = RosettaImportStatus.PENDING

def getRawFileData(raw_file_data):
    client = getUtility(ILibrarianClient)

    try:
        file = client.getFileByAlias(raw_file_data.rawfile.id)
    except DownloadFailed, e:
        raise RawFileFetchFailed(str(e))

    return file.read()

def count_lines(text):
    '''Count the number of physical lines in a string. This is always at least
    as large as the number of logical lines in a string.
    '''

    count = 0

    for line in text.split('\n'):
        if len(line) == 0:
            count += 1
        else:
            count += int(ceil(float(len(line)) / CHARACTERS_PER_LINE))

    return count

def request_languages(request):
    '''Turn a request into a list of languages to show.'''

    user = getUtility(ILaunchBag).user

    # If the user is authenticated, try seeing if they have any languages set.
    if user is not None:
        languages = user.languages
        if languages:
            return languages

    # If the user is not authenticated, or they are authenticated but have no
    # languages set, try looking at the HTTP headers for clues.
    languages = IRequestPreferredLanguages(request).getPreferredLanguages()
    for lang in IRequestLocalLanguages(request).getLocalLanguages():
        if lang not in languages:
            languages.append(lang)
    return languages

class UnrecognisedCFormatString(ValueError):
    """Exception raised when a string containing C format sequences can't be
    parsed."""

def parse_cformat_string(string):
    """Parse a printf()-style format string into a sequence of interpolations
    and non-interpolations."""

    # The sequence '%%' is not counted as an interpolation. Perhaps splitting
    # into 'special' and 'non-special' sequences would be better.

    # This function works on the basis that s can be one of three things: an
    # empty string, a string beginning with a sequence containing no
    # interpolations, or a string beginning with an interpolation.

    segments = []
    end = string
    plain_re = re.compile('(%%|[^%])+')
    interpolation_re = re.compile('%[^diouxXeEfFgGcspmn]*[diouxXeEfFgGcspmn]')

    while end:
        # Check for a interpolation-less prefix.

        match = plain_re.match(end)

        if match:
            segment = match.group(0)
            segments.append(('string', segment))
            end = end[len(segment):]
            continue

        # Check for an interpolation sequence at the beginning.

        match = interpolation_re.match(end)

        if match:
            segment = match.group(0)
            segments.append(('interpolation', segment))
            end = end[len(segment):]
            continue

        # Give up.

        raise UnrecognisedCFormatString(string)

    return segments

def normalize_newlines(text):
    r"""Convert newlines to Unix form.

    >>> normalize_newlines('foo')
    'foo'
    >>> normalize_newlines('foo\n')
    'foo\n'
    >>> normalize_newlines('foo\r')
    'foo\n'
    >>> normalize_newlines('foo\r\n')
    'foo\n'
    >>> normalize_newlines('foo\r\nbar\r\n\r\nbaz')
    'foo\nbar\n\nbaz'
    """
    return text_replaced(text, {'\r\n': '\n', '\r': '\n'})

def unix2windows_newlines(text):
    r"""Convert Unix form new lines to Windows ones.

    Raise ValueError if 'text' is already using Windows newlines format.

    >>> unix2windows_newlines('foo')
    'foo'
    >>> unix2windows_newlines('foo\n')
    'foo\r\n'
    >>> unix2windows_newlines('foo\nbar\n\nbaz')
    'foo\r\nbar\r\n\r\nbaz'
    >>> unix2windows_newlines('foo\r\nbar')
    Traceback (most recent call last):
    ...
    ValueError: ''foo\r\nbar'' is already converted
    """
    if text is None:
        return None
    elif '\r\n' in text:
        raise ValueError('\'%r\' is already converted' % text)

    return text_replaced(text, {'\n': '\r\n'})

def contract_rosetta_tabs(text):
    r"""Replace Rosetta representation of tab characters with their native form.

    Normal strings get passed through unmolested.

    >>> contract_rosetta_tabs('foo')
    'foo'
    >>> contract_rosetta_tabs('foo\\nbar')
    'foo\\nbar'

    The string '[tab]' gets gonveted to a tab character.

    >>> contract_rosetta_tabs('foo[tab]bar')
    'foo\tbar'

    The string '\[tab]' gets converted to a literal '[tab]'.

    >>> contract_rosetta_tabs('foo\\[tab]bar')
    'foo[tab]bar'

    The string '\\[tab]' gets converted to a literal '\[tab]'.

    >>> contract_rosetta_tabs('foo\\\\[tab]bar')
    'foo\\[tab]bar'

    And so on...

    >>> contract_rosetta_tabs('foo\\\\\\[tab]bar')
    'foo\\\\[tab]bar'
    """
    return text_replaced(text, {'[tab]': '\t', r'\[tab]': '[tab]'})

def expand_rosetta_tabs(text):
    r"""Replace tabs with their Rosetta representation.

    Normal strings get passed through unmolested.

    >>> expand_rosetta_tabs('foo')
    'foo'
    >>> expand_rosetta_tabs('foo\\nbar')
    'foo\\nbar'

    Tabs get converted to '[tab]'.

    >>> expand_rosetta_tabs('foo\tbar')
    'foo[tab]bar'

    Literal ocurrences of '[tab]' get escaped.

    >>> expand_rosetta_tabs('foo[tab]bar')
    'foo\\[tab]bar'

    Escaped ocurrences themselves get escaped.

    >>> expand_rosetta_tabs('foo\\[tab]bar')
    'foo\\\\[tab]bar'

    And so on...

    >>> expand_rosetta_tabs('foo\\\\[tab]bar')
    'foo\\\\\\[tab]bar'
    """
    return text_replaced(text, {'\t': '[tab]', '[tab]': r'\[tab]'})

def parse_translation_form(form):
    """Parse a form submitted to the translation widget.

    Returns a dictionary keyed on the sequence number of the message set,
    where each value is a structure of the form

        {
            'msgid': '...',
            'translations': ['...', '...'],
            'fuzzy': False,
        }
    """

    messageSets = {}

    # Extract message IDs.

    for key in form:
        match = re.match('set_(\d+)_msgid$', key)

        if match:
            id = int(match.group(1))
            messageSets[id] = {}
            messageSets[id]['msgid'] = id
            messageSets[id]['translations'] = {}
            messageSets[id]['fuzzy'] = False

    # Extract translations.
    for key in form:
        match = re.match(r'set_(\d+)_translation_([a-z]+(?:_[A-Z]+)?)_(\d+)$',
            key)

        if match:
            id = int(match.group(1))
            pluralform = int(match.group(3))

            if not id in messageSets:
                raise AssertionError("Orphaned translation in form.")

            messageSets[id]['translations'][pluralform] = (
                contract_rosetta_tabs(normalize_newlines(form[key])))

    # Extract fuzzy statuses.
    for key in form:
        match = re.match(r'set_(\d+)_fuzzy_([a-z]+)$', key)

        if match:
            id = int(match.group(1))
            messageSets[id]['fuzzy'] = True

    return messageSets

def msgid_html(text, flags, space=TranslationConstants.SPACE_CHAR,
               newline=TranslationConstants.NEWLINE_CHAR):
    """Convert a message ID to a HTML representation."""

    lines = []

    # Replace leading and trailing spaces on each line with special markup.

    for line in xml_escape(text).split('\n'):
        # Pattern:
        # - group 1: zero or more spaces: leading whitespace
        # - group 2: zero or more groups of (zero or
        #   more spaces followed by one or more non-spaces): maximal string
        #   which doesn't begin or end with whitespace
        # - group 3: zero or more spaces: trailing whitespace
        match = re.match('^( *)((?: *[^ ]+)*)( *)$', line)

        if match:
            lines.append(
                space * len(match.group(1)) +
                match.group(2) +
                space * len(match.group(3)))
        else:
            raise AssertionError(
                "A regular expression that should always match didn't.")

    if 'c-format' in flags:
        # Replace c-format sequences with marked-up versions. If there is a
        # problem parsing the c-format sequences on a particular line, that
        # line is left unformatted.

        for i in range(len(lines)):
            formatted_line = ''

            try:
                segments = parse_cformat_string(lines[i])
            except UnrecognisedCFormatString:
                continue

            for segment in segments:
                type, content = segment

                if type == 'interpolation':
                    formatted_line += ('<span class="interpolation">%s</span>'
                        % content)
                elif type == 'string':
                    formatted_line += content

            lines[i] = formatted_line

    # Replace newlines and tabs with their respective representations.

    return expand_rosetta_tabs(newline.join(lines))

def check_po_syntax(s):
    parser = POParser()

    try:
        parser.write(s)
        parser.finish()
    except:
        return False

    return True

def is_tar_filename(filename):
    '''
    Check whether a filename looks like a filename that belongs to a tar file,
    possibly one compressed somehow.
    '''

    return (filename.endswith('.tar') or
            filename.endswith('.tar.gz') or
            filename.endswith('.tar.bz2'))


class DummyPOFile(RosettaStats):
    """
    Represents a POFile where we do not yet actually HAVE a POFile for that
    language for this template.
    """
    def __init__(self, potemplate, language):
        self.potemplate = potemplate
        self.language = language
        self.header = ''
        self.latest_submission = None
        self.messageCount = len(potemplate)

    @property
    def translators(self):
        tgroups = self.potemplate.translationgroups
        ret = []
        for group in tgroups:
            translator = group.query_translator(self.language)
            if translator is not None:
                ret.append(translator)
        return ret

    def canEditTranslations(self, person):

        tperm = self.potemplate.translationpermission
        if tperm == TranslationPermission.OPEN:
            # if the translation policy is "open", then yes
            return True
        elif tperm == TranslationPermission.CLOSED:
            if person is not None:
                # if the translation policy is "closed", then check if the
                # person is in the set of translators XXX sabdfl 25/05/05 this
                # code could be improved when we have implemented CrowdControl
                translators = [t.translator for t in self.translators]
                for translator in translators:
                    if person.inTeam(translator):
                        return True
        else:
            raise NotImplementedError, 'Unknown permission %s', tperm.name

        # At this point you either got an OPEN (true) or you are not in the
        # designated translation group, so you can't edit them
        return False

    def currentCount(self):
        return 0

    def rosettaCount(self):
        return 0

    def updatesCount(self):
        return 0

    def nonUpdatesCount(self):
        return 0

    def translatedCount(self):
        return 0

    def untranslatedCount(self):
        return self.messageCount

    def currentPercentage(self):
        return 0.0

    def rosettaPercentage(self):
        return 0.0

    def updatesPercentage(self):
        return 0.0

    def nonUpdatesPercentage(self):
        return 0.0

    def translatedPercentage(self):
        return 0.0

    def untranslatedPercentage(self):
        return 100.0


def test_diff(lines_a, lines_b):
    """Generate a string indicating the difference between expected and actual
    values in a test.
    """

    return '\n'.join(list(unified_diff(
        a=lines_a,
        b=lines_b,
        fromfile='expected',
        tofile='actual',
        lineterm='',
        )))

def sanitiseFingerprint(fpr):
    """Returns sanitised fingerprint if fpr is well-formed,
    otherwise returns False.

    >>> sanitiseFingerprint('C858 2652 1A6E F6A6 037B  B3F7 9FF2 583E 681B 6469')
    'C85826521A6EF6A6037BB3F79FF2583E681B6469'
    >>> sanitiseFingerprint('681B 6469')
    False
    
    >>> sanitiseFingerprint('abnckjdiue')
    False
    
    """ 
    # replace the white spaces
    fpr = fpr.replace(' ', '')

    if not valid_fingerprint(fpr):
        return False
    
    return fpr

class Participation:
    implements(IParticipation) 

    interaction = None
    principal = None


def setupInteraction(principal, login=None, participation=None):
    """Sets up a new interaction with the given principal.

    The login gets added to the launch bag.
    
    You can optionally pass in a participation to be used.  If no
    participation is given, a Participation is used.
    """
    if participation is None:
        participation = Participation()

    # First end any running interaction, and start a new one
    endInteraction()
    newInteraction(participation)

    launchbag = getUtility(IOpenLaunchBag)
    if IUnauthenticatedPrincipal.providedBy(principal):
        launchbag.setLogin(None)
    else:
        launchbag.setLogin(login)

    participation.principal = principal


def read_test_message(filename):
    """Reads a test message and returns it as ISignedMessage.

    The test messages are located in canonical/launchpad/mail/ftests/emails
    """
    return email.message_from_file(
        open(testmails_path + filename), _class=SignedMessage)


def check_permission(permission_name, context):
    """Like zope.security.management.checkPermission, but also ensures that
    permission_name is real permission.

    Raises ValueError if the permission doesn't exist.
    """
    # This will raise ValueError if the permission doesn't exist.
    check_permission_is_registered(context, permission_name)
    
    # Now call Zope's checkPermission.
    return zcheckPermission(permission_name, context)


def filenameToContentType(fname):
    """ Return the a ContentType-like entry for arbitrary filenames 

    deb files

    >>> filenameToContentType('test.deb')
    'application/x-debian-package'

    text files

    >>> filenameToContentType('test.txt')
    'text/plain'

    Not recognized format
    
    >>> filenameToContentType('test.tgz')
    'application/octet-stream'
    """
    ftmap = {".dsc":      "text/plain",
             ".changes":  "text/plain",
             ".deb":      "application/x-debian-package",
             ".udeb":     "application/x-debian-package",
             ".txt":      "text/plain",
             }
    for ending in ftmap:
        if fname.endswith(ending):
            return ftmap[ending]
    return "application/octet-stream"


def get_filename_from_message_id(message_id):
    """Returns a librarian filename based on the email message_id.
    
    It generates a file name that's not easily guessable.  
    """
    return '%s.msg' % (
            canonical.base.base(long(sha.new(message_id).hexdigest(), 16), 62))

def getFileType(fname):
    if fname.endswith(".deb"):
        return BinaryPackageFileType.DEB
    if fname.endswith(".udeb"):
        return BinaryPackageFileType.DEB
    if fname.endswith(".dsc"):
        return SourcePackageFileType.DSC
    if fname.endswith(".diff.gz"):
        return SourcePackageFileType.DIFF
    if fname.endswith(".orig.tar.gz"):
        return SourcePackageFileType.ORIG
    if fname.endswith(".tar.gz"):
        return SourcePackageFileType.TARBALL

def getBinaryPackageFormat(fname):
    if fname.endswith(".deb"):
        return BinaryPackageFormat.DEB
    if fname.endswith(".udeb"):
        return BinaryPackageFormat.UDEB
    if fname.endswith(".rpm"):
        return BinaryPackageFormat.RPM
