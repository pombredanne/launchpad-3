# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import base64
import gettextpo
import os
import popen2
import random
import re
import tarfile
import time
import warnings
import email
from StringIO import StringIO
from select import select
from math import ceil
from xml.sax.saxutils import escape as xml_escape
from difflib import unified_diff

from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import IParticipation
from zope.security.management import newInteraction, endInteraction
from zope.app.security.interfaces import IUnauthenticatedPrincipal

from canonical.database.constants import UTC_NOW
from canonical.lp.dbschema import RosettaImportStatus, TranslationPermission
from canonical.librarian.interfaces import ILibrarianClient, UploadFailed, \
    DownloadFailed
from canonical.launchpad.interfaces import ILaunchBag, IOpenLaunchBag, \
    IHasOwner, IGeoIP, IRequestPreferredLanguages, ILanguageSet, \
    IRequestLocalLanguages, \
    RawFileAttachFailed, RawFileFetchFailed
from canonical.launchpad.components.poparser import POSyntaxError, \
    POInvalidInputError, POParser
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.mail import SignedMessage
from canonical.launchpad.mail.ftests import testmails_path

CHARACTERS_PER_LINE = 50

class TranslationConstants:
    """Set of constants used inside the context of translations."""

    SINGULAR_FORM = 0
    PLURAL_FORM = 1
    SPACE_CHAR = u'<span class="po-message-special">\u2022</span>'
    NEWLINE_CHAR = u'<span class="po-message-special">\u21b5</span><br/>\n'


def is_maintainer(hasowner):
    """Return True if the logged in user is an owner of hasowner.

    Return False if he's not an owner.

    The user is an owner if it either matches hasowner.owner directly or is a
    member of the hasowner.owner team.

    Raise TypeError is hasowner does not provide IHasOwner.
    """
    if not IHasOwner.providedBy(hasowner):
        raise TypeError, "hasowner doesn't provide IHasOwner"
    launchbag = getUtility(ILaunchBag)
    if launchbag.user is not None:
        return launchbag.user.inTeam(hasowner.owner)
    else:
        return False

def tar_add_file(tf, path, contents):
    """Convenience function for adding a file to a tar file."""

    now = int(time.time())
    bits = path.split(os.path.sep)

    # Ensure that all the directories in the path are present in the
    # archive.

    for i in range(1, len(bits)):
        joined_path = os.path.join(*bits[:i])

        try:
            tf.getmember(joined_path + '/')
        except KeyError:
            tarinfo = tarfile.TarInfo(joined_path)
            tarinfo.type = tarfile.DIRTYPE
            tarinfo.mtime = now
            tf.addfile(tarinfo)

    tarinfo = tarfile.TarInfo(path)
    tarinfo.time = now
    tarinfo.size = len(contents)
    tf.addfile(tarinfo, StringIO(contents))

def make_tarball_filehandle(files):
    """Return a file handle to a tar file contaning a given set of files.

    @param files: a dictionary mapping paths to file contents
    """

    sio = StringIO()
    tarball = tarfile.open('', 'w', sio)

    sorted_files = files.keys()
    sorted_files.sort()

    for filename in sorted_files:
        tar_add_file(tarball, filename, files[filename])

    tarball.close()
    sio.seek(0)
    return sio

def make_tarball_string(files):
    """Similar to make_tarball_filehandle, but return the contents of the
    tarball as a string.
    """

    return make_tarball_filehandle(files).read()

def make_tarball(files):
    """Similar to make_tarball_filehandle, but return a tarinfo object."""

    return tarfile.open('', 'r', make_tarball_filehandle(files))

def join_lines(*lines):
    """Concatenate a list of strings, adding a newline at the end of each."""

    return ''.join([ x + '\n' for x in lines ])

def string_to_tarfile(s):
    """Convert a binary string containing a tar file into a tar file obj."""

    return tarfile.open('', 'r', StringIO(s))


def find_po_directories(tarfile):
    """Find all directories named 'po' in a tarfile."""

    return [
        member.name
        for member in tarfile.getmembers()
        if member.isdir()
        and os.path.basename(member.name.strip("/")) == 'po'
        ]

def examine_tarfile(tf):
    """Find POT and PO files within a tar file object.

    Return a tuple with the list of .pot files and the list of .po files
    found.

    Two methods of finding files are employed:

     1. Directories named 'po' are searched for in the tar file, and if there
        is exactly one non-empty such directory, it is searched for files
        ending in '.pot' and '.po'.

     2. Otherwise, files ending in '.pot' and '.po' are searched for directly.
     """

    # All files in the tarfile.

    names = tf.getnames()

    # Directories named 'po' in the tarfile.

    po_directories = find_po_directories(tf)

    if po_directories:
        # Look for interesting PO directories. (I.e. ones that contain POT or
        # PO files.)

        interesting = []

        for d in po_directories:
            for name in names:
                if name != d and name.startswith(d) and (
                    name.endswith('.pot') or name.endswith('.po')):
                    if d not in interesting:
                        interesting.append(d)

        # If there's exactly one interesting PO directory, get a list of all
        # the interesting files in it. Otherwise, use method 2.

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
    # All chars should be lower case.
    name = invalid_name.lower()
    # Underscore is not a valid char.
    name = name.replace('_', '-')
    # Spaces is not a valid char for a name.
    name = name.replace(' ', '-')

    return name

def requestCountry(request):
    """Return the Country object from where the request was done.

    If the ipaddress is unknown or the country is not in our database,
    return None.
    """
    ipaddress = request.get('HTTP_X_FORWARDED_FOR')
    if ipaddress is None:
        ipaddress = request.get('REMOTE_ADDR')
    if ipaddress is None:
        return None
    return getUtility(IGeoIP).country_by_addr(ipaddress)

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

# Note that this appears as "valid email" in the UI, because that term is
# more familiar to users, even if it is less correct.
well_formed_email_re = re.compile(
    r"^[_\.0-9a-z-+]+@([0-9a-z-]{1,}\.)*[a-z]{2,}$")

def well_formed_email(emailaddr):
    """Returns True if emailaddr is well-formed, otherwise returns False.

    >>> well_formed_email('foo.bar@baz.museum')
    True
    >>> well_formed_email('mark@hbd.com')
    True
    >>> well_formed_email('art@cat-flap.com')
    True
    >>> well_formed_email('a@b.b.tw')
    True
    >>> well_formed_email('a@b.b.b.b.tw')
    True
    >>> well_formed_email('i@tm')
    True
    >>> well_formed_email('')
    False
    >>> well_formed_email('a@b')
    False
    >>> well_formed_email('a@foo.b')
    False

    """
    return bool(well_formed_email_re.match(emailaddr))

replacements = {0: {'\.': ' |dot| ', '@': ' |at| '},
                1: {'\.': ' ! '    , '@': ' {} '  },
                2: {'\.': ' , '    , '@': ' % '   },
                3: {'\.': ' (!) '  , '@': ' (at) '},
                4: {'\.': ' {dot} ', '@': ' {at} '}}

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
        idx = random.randint(0, len(replacements.keys()) - 1)

    for original, replacement in replacements[idx].items():
        emailaddr = re.sub(r'%s' % original, r'%s' % replacement, emailaddr)

    return emailaddr

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
        file = client.getFileByAlias(raw_file_data.rawfile)
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

def canonicalise_code(code):
    '''Convert a language code to a standard xx_YY form.'''

    if '-' in code:
        language, country = code.split('-', 1)

        return "%s_%s" % (language, country.upper())
    else:
        return code

def codes_to_languages(codes):
    '''Convert a list of ISO language codes to language objects.'''

    languages = []
    all_languages = getUtility(ILanguageSet)

    for code in codes:
        try:
            languages.append(all_languages[canonicalise_code(code)])
        except KeyError:
            pass

    return languages

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

def parse_cformat_string(s):
    '''Parse a printf()-style format string into a sequence of interpolations
    and non-interpolations.'''

    # The sequence '%%' is not counted as an interpolation. Perhaps splitting
    # into 'special' and 'non-special' sequences would be better.

    # This function works on the basis that s can be one of three things: an
    # empty string, a string beginning with a sequence containing no
    # interpolations, or a string beginning with an interpolation.

    # Check for an empty string.

    if s == '':
        return ()

    # Check for a interpolation-less prefix.

    match = re.match('(%%|[^%])+', s)

    if match:
        t = match.group(0)
        return (('string', t),) + parse_cformat_string(s[len(t):])

    # Check for an interpolation sequence at the beginning.

    match = re.match('%[^diouxXeEfFgGcspn]*[diouxXeEfFgGcspn]', s)

    if match:
        t = match.group(0)
        return (('interpolation', t),) + parse_cformat_string(s[len(t):])

    # Give up.

    raise ValueError(s)

def normalize_newlines(s):
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
    return s.replace('\r\n', '\n').replace('\r', '\n')

def regex_escape(*substitutions):
    """Helper for string substitution when making regular expressions."""
    return tuple([re.escape(string) for string in substitutions])

def _tab_contraction_replacer(matchobj):
    """Function called by contract_rosetta_tabs when substituting in
    _tab_contraction_re."""
    tab_in_brackets, escaped_tab_in_brackets = matchobj.groups()
    if tab_in_brackets:
        return '\t'
    else:
        assert escaped_tab_in_brackets
        return '[tab]'

_tab_contraction_re = re.compile(
    '(%s)|(%s)' % regex_escape('[tab]', r'\[tab]'))

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

    return _tab_contraction_re.sub(_tab_contraction_replacer, text)

def _tab_expansion_replacer(matchobj):
    """Function called by expand_rosetta_tabs when substituting in
    _tab_expansion_re."""
    tab_literal, tab_in_brackets = matchobj.groups()
    if tab_literal:
        return '[tab]'
    else:
        assert tab_in_brackets
        return '\[tab]'

_tab_expansion_re = re.compile(
    '(%s)|(%s)' % regex_escape('\t', '[tab]'))

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

    return _tab_expansion_re.sub(_tab_expansion_replacer, text)

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
    '''Convert a message ID to a HTML representation.'''

    lines = []

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

    for i in range(len(lines)):
        if 'c-format' in flags:
            line = ''

            for segment in parse_cformat_string(lines[i]):
                type, content = segment

                if type == 'interpolation':
                    line += '<span class="interpolation">%s</span>' % content
                elif type == 'string':
                    line += content

            lines[i] = line

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

def check_tar(tf, pot_paths, po_paths):
    '''
    Check an uploaded tar file for problems. Returns an error message if a
    problem was detected, or None otherwise.
    '''

    # Check that at most one .pot file was found.
    if len(pot_paths) > 1:
        return (
            "More than one PO template was found in the tar file you "
            "uploaded. This is not currently supported.")

    # Check the syntax of the .pot file, if present.
    if len(pot_paths) > 0:
        pot_contents = tf.extractfile(pot_paths[0]).read()

        if not check_po_syntax(pot_contents):
            return (
                "There was a problem parsing the PO template file in the tar "
                "file you uploaded.")

    # Complain if no files at all were found.
    if len(pot_paths) == 0 and len(po_paths) == 0:
        return (
            "The tar file you uploaded could not be imported. This may be "
            "because there was more than one 'po' directory, or because the "
            "PO templates and PO files found did not share a common "
            "location.")

    return None

def import_tar(potemplate, importer, tarfile, pot_paths, po_paths):
    """Import a tar file into Rosetta.

    Extract PO templates and PO files from the paths specified.
    A status message is returned.

    Currently, it is assumed that since check_tar will have been called before
    import_tar, checking the syntax of the PO template will not be necessary
    and also, we are 100% sure there are at least one .pot file and only one.
    The syntax of PO files is checked, but errors are not fatal.
    """

    # At this point we are only getting one .pot file so this should be safe.
    # We don't support other kinds of tarballs and before calling this
    # function we did already the needed tests to be sure that pot_paths
    # follows our requirements.
    potemplate.attachRawFileData(tarfile.extractfile(pot_paths[0]).read(),
                                 True, # the "published" flag
                                 importer)
    pot_base_dir = os.path.dirname(pot_paths[0])

    # List of .pot and .po files that were not able to be imported.
    errors = []

    for path in po_paths:
        if pot_base_dir != os.path.dirname(path):
            # The po file is not inside the same directory than the pot file,
            # we ignore it.
            errors.append(path)
            continue

        contents = tarfile.extractfile(path).read()

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
            "The following files were skipped due to syntax errors or other "
            "problems: " + ', '.join(errors) + ".")

    return message


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

