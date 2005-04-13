# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import random
import re
import tarfile
from StringIO import StringIO
from select import select

from zope.component import getUtility

import gettextpo

from canonical.launchpad.interfaces import ILaunchBag, IHasOwner, IGeoIP, \
    IRequestPreferredLanguages

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


def tar_add_file(tf, name, contents):
    """
    Convenience method for adding a file to a tar file.
    """

    tarinfo = tarfile.TarInfo(name)
    tarinfo.size = len(contents)

    tf.addfile(tarinfo, StringIO(contents))

def tar_add_files(tf, prefix, files):
    """Add a tree of files, represented by a dictionary, to a tar file."""

    # Keys are sorted in order to make test cases easier to write.

    names = files.keys()
    names.sort()

    for name in names:
        if isinstance(files[name], basestring):
            # Looks like a file.

            tar_add_file(tf, prefix + name, files[name])
        else:
            # Should be a directory.

            tarinfo = tarfile.TarInfo(prefix + name)
            tarinfo.type = tarfile.DIRTYPE
            tf.addfile(tarinfo)

            tar_add_files(tf, prefix + name + '/', files[name])

def make_tarfile(files):
    """Return a tar file as string from a dictionary."""

    sio = StringIO()

    tf = tarfile.open('', 'w', sio)

    tar_add_files(tf, '', files)

    tf.close()

    return sio.getvalue()

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
    """Checks with gettext if a translation is correct or not.

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

