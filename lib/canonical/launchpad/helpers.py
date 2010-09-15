# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Various functions and classes that are useful across different parts of
launchpad.

Do not simply dump stuff in here.  Think carefully as to whether it would
be better as a method on an existing content object or IFooSet object.
"""

__metaclass__ = type

from difflib import unified_diff
import hashlib
import os
import random
import re
from StringIO import StringIO
import subprocess
import tarfile
import warnings

import gettextpo
from zope.component import getUtility
from zope.security.interfaces import ForbiddenAttribute

import canonical
from canonical.launchpad.interfaces import ILaunchBag
from lp.services.geoip.interfaces import (
    IRequestLocalLanguages,
    IRequestPreferredLanguages,
    )


def text_replaced(text, replacements, _cache={}):
    """Return a new string with text replaced according to the dict provided.

    The keys of the dict are substrings to find, the values are what to
    replace found substrings with.

    :arg text: An unicode or str to do the replacement.
    :arg replacements: A dictionary with the replacements that should be done

    >>> text_replaced('', {'a':'b'})
    ''
    >>> text_replaced('a', {'a':'c'})
    'c'
    >>> text_replaced('faa bar baz', {'a': 'A', 'aa': 'X'})
    'fX bAr bAz'
    >>> text_replaced('1 2 3 4', {'1': '2', '2': '1'})
    '2 1 3 4'

    Unicode strings work too.

    >>> text_replaced(u'1 2 3 4', {u'1': u'2', u'2': u'1'})
    u'2 1 3 4'

    The argument _cache is used as a cache of replacements that were requested
    before, so we only compute regular expressions once.

    """
    assert replacements, "The replacements dict must not be empty."
    # The ordering of keys and values in the tuple will be consistent within a
    # single Python process.
    cachekey = tuple(replacements.items())
    if cachekey not in _cache:
        L = []
        if isinstance(text, unicode):
            list_item = u'(%s)'
            join_char = u'|'
        else:
            list_item = '(%s)'
            join_char = '|'
        for find, replace in sorted(replacements.items(),
                                    key=lambda (key, value): len(key),
                                    reverse=True):
            L.append(list_item % re.escape(find))
        # Make a copy of the replacements dict, as it is mutable, but we're
        # keeping a cached reference to it.
        replacements_copy = dict(replacements)

        def matchobj_replacer(matchobj):
            return replacements_copy[matchobj.group()]

        regexsub = re.compile(join_char.join(L)).sub

        def replacer(s):
            return regexsub(matchobj_replacer, s)

        _cache[cachekey] = replacer
    return _cache[cachekey](text)


def backslashreplace(str):
    """Return a copy of the string, with non-ASCII characters rendered as
    xNN or uNNNN. Used to test data containing typographical quotes etc.
    """
    return str.decode('UTF-8').encode('ASCII', 'backslashreplace')


def join_lines(*lines):
    """Concatenate a list of strings, adding a newline at the end of each."""

    return ''.join([x + '\n' for x in lines])


def string_to_tarfile(s):
    """Convert a binary string containing a tar file into a tar file obj."""

    return tarfile.open('', 'r', StringIO(s))


def shortest(sequence):
    """Return a list with the shortest items in sequence.

    Return an empty list if the sequence is empty.
    """
    shortest_list = []
    shortest_length = None

    for item in list(sequence):
        new_length = len(item)

        if shortest_length is None:
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
    return text_replaced(invalid_name.lower(), {'_': '-', ' ': '-'})


def browserLanguages(request):
    """Return a list of Language objects based on the browser preferences."""
    return IRequestPreferredLanguages(request).getPreferredLanguages()


def simple_popen2(command, input, env=None, in_bufsize=1024, out_bufsize=128):
    """Run a command, give it input on its standard input, and capture its
    standard output.

    Returns the data from standard output.

    This function is needed to avoid certain deadlock situations. For example,
    if you popen2() a command, write its standard input, then read its
    standard output, this can deadlock due to the parent process blocking on
    writing to the child, while the child process is simultaneously blocking
    on writing to its parent. This function avoids that problem by using
    subprocess.Popen.communicate().
    """

    p = subprocess.Popen(
            command, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output, nothing) = p.communicate(input)
    return output


def emailPeople(person):
    """Return a set of people to who receive email for this Person.

    If <person> has a preferred email, the set will contain only that
    person.  If <person> doesn't have a preferred email but is a team,
    the set will contain the preferred email address of each member of
    <person>, including indirect members.

    Finally, if <person> doesn't have a preferred email and is not a team,
    the set will be empty.
    """
    pending_people = [person]
    people = set()
    seen = set()
    while len(pending_people) > 0:
        person = pending_people.pop()
        if person in seen:
            continue
        seen.add(person)
        if person.preferredemail is not None:
            people.add(person)
        elif person.isTeam():
            pending_people.extend(person.activemembers)
    return people


def get_contact_email_addresses(person):
    """Return a set of email addresses to contact this Person.

    In general, it is better to use emailPeople instead.
    """
    # Need to remove the security proxy of the email address because the
    # logged in user may not have permission to see it.
    from zope.security.proxy import removeSecurityProxy
    return set(
        str(removeSecurityProxy(mail_person.preferredemail).email)
        for mail_person in emailPeople(person))


replacements = {0: {'.': ' |dot| ',
                    '@': ' |at| '},
                1: {'.': ' ! ',
                    '@': ' {} '},
                2: {'.': ' , ',
                    '@': ' % '},
                3: {'.': ' (!) ',
                    '@': ' (at) '},
                4: {'.': ' {dot} ',
                    '@': ' {at} '},
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


def validate_translation(original, translation, flags):
    """Check with gettext if a translation is correct or not.

    If the translation has a problem, raise gettextpo.error.
    """
    msg = gettextpo.PoMessage()
    msg.set_msgid(original[0])

    if len(original) > 1:
        # It has plural forms.
        msg.set_msgid_plural(original[1])
        for form in range(len(translation)):
            msg.set_msgstr_plural(form, translation[form])
    elif len(translation):
        msg.set_msgstr(translation[0])

    for flag in flags:
        msg.set_format(flag, True)

    # Check the msg.
    msg.check_format()


class ShortListTooBigError(Exception):
    """This error is raised when the shortlist hardlimit is reached"""


def shortlist(sequence, longest_expected=15, hardlimit=None):
    """Return a listified version of sequence.

    If <sequence> has more than <longest_expected> items, a warning is issued.

    >>> shortlist([1, 2])
    [1, 2]

    >>> shortlist([1, 2, 3], 2) #doctest: +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
    ...
    UserWarning: shortlist() should not be used here. It's meant to listify
    sequences with no more than 2 items.  There were 3 items.

    >>> shortlist([1, 2, 3, 4], hardlimit=2)
    Traceback (most recent call last):
    ...
    ShortListTooBigError: Hard limit of 2 exceeded.

    >>> shortlist(
    ...     [1, 2, 3, 4], 2, hardlimit=4) #doctest: +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
    ...
    UserWarning: shortlist() should not be used here. It's meant to listify
    sequences with no more than 2 items.  There were 4 items.

    It works on iterable also which don't support the extended slice protocol.

    >>> xrange(5)[:1] #doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    TypeError: ...

    >>> shortlist(xrange(10), 5, hardlimit=8) #doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ShortListTooBigError: ...

    """
    if hardlimit is not None:
        last = hardlimit + 1
    else:
        last = None
    try:
        results = list(sequence[:last])
    except (TypeError, ForbiddenAttribute):
        results = []
        for idx, item in enumerate(sequence):
            if hardlimit and idx > hardlimit:
                break
            results.append(item)

    size = len(results)
    if hardlimit and size > hardlimit:
        raise ShortListTooBigError(
           'Hard limit of %d exceeded.' % hardlimit)
    elif size > longest_expected:
        warnings.warn(
            "shortlist() should not be used here. It's meant to listify"
            " sequences with no more than %d items.  There were %s items."
            % (longest_expected, size), stacklevel=2)
    return results


def preferred_or_request_languages(request):
    """Turn a request into a list of languages to show.

    Return Person.languages when the user has preferred languages.
    Otherwise, return the languages from the request either from the
    headers or from the IP address.
    """
    user = getUtility(ILaunchBag).user
    if user is not None and user.languages:
        return user.languages

    # If the user is not authenticated, or they are authenticated but have no
    # languages set, try looking at the HTTP headers for clues.
    languages = IRequestPreferredLanguages(request).getPreferredLanguages()
    for lang in IRequestLocalLanguages(request).getLocalLanguages():
        if lang not in languages:
            languages.append(lang)
    return languages


def is_english_variant(language):
    """Return whether the language is a variant of modern English .

    >>> class Language:
    ...     def __init__(self, code):
    ...         self.code = code
    >>> is_english_variant(Language('fr'))
    False
    >>> is_english_variant(Language('en'))
    False
    >>> is_english_variant(Language('en_CA'))
    True
    >>> is_english_variant(Language('enm'))
    False
    """
    # XXX sinzui 2007-07-12 bug=125545:
    # We would not need to use this function so often if variant languages
    # knew their parent language.
    return language.code[0:3] in ['en_']


def is_tar_filename(filename):
    '''
    Check whether a filename looks like a filename that belongs to a tar file,
    possibly one compressed somehow.
    '''

    return (filename.endswith('.tar') or
            filename.endswith('.tar.gz') or
            filename.endswith('.tgz') or
            filename.endswith('.tar.bz2'))


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
    ftmap = {".dsc": "text/plain",
             ".changes": "text/plain",
             ".deb": "application/x-debian-package",
             ".udeb": "application/x-debian-package",
             ".txt": "text/plain",
             # For the build master logs
             ".txt.gz": "text/plain",
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
            canonical.base.base(
                long(hashlib.sha1(message_id).hexdigest(), 16), 62))


def intOrZero(value):
    """Return int(value) or 0 if the conversion fails.

    >>> intOrZero('1.23')
    0
    >>> intOrZero('1.ab')
    0
    >>> intOrZero('2')
    2
    >>> intOrZero(None)
    0
    >>> intOrZero(1)
    1
    >>> intOrZero(-9)
    -9
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def positiveIntOrZero(value):
    """Return 0 if int(value) fails or if int(value) is less than 0.

    Return int(value) otherwise.

    >>> positiveIntOrZero(None)
    0
    >>> positiveIntOrZero(-9)
    0
    >>> positiveIntOrZero(1)
    1
    >>> positiveIntOrZero('-3')
    0
    >>> positiveIntOrZero('5')
    5
    >>> positiveIntOrZero(3.1415)
    3
    """
    value = intOrZero(value)
    if value < 0:
        return 0
    return value


def get_email_template(filename, app=None):
    """Returns the email template with the given file name.

    The templates are located in 'lib/canonical/launchpad/emailtemplates'.
    """
    if app is None:
        base = os.path.dirname(canonical.launchpad.__file__)
        fullpath = os.path.join(base, 'emailtemplates', filename)
    else:
        import lp
        base = os.path.dirname(lp.__file__)
        fullpath = os.path.join(base, app, 'emailtemplates', filename)
    return open(fullpath).read()


def is_ascii_only(string):
    """Ensure that the string contains only ASCII characters.

        >>> is_ascii_only(u'ascii only')
        True
        >>> is_ascii_only('ascii only')
        True
        >>> is_ascii_only('\xf4')
        False
        >>> is_ascii_only(u'\xf4')
        False
    """
    try:
        string.encode('ascii')
    except UnicodeError:
        return False
    else:
        return True


def truncate_text(text, max_length):
    """Return a version of string no longer than max_length characters.

    Tries not to cut off the text mid-word.
    """
    words = re.compile(r'\s*\S+').findall(text, 0, max_length + 1)
    truncated = words[0]
    for word in words[1:]:
        if len(truncated) + len(word) > max_length:
            break
        truncated += word
    return truncated[:max_length]


def english_list(items, conjunction='and'):
    """Return all the items concatenated into a English-style string.

    Follows the advice given in The Elements of Style, chapter I,
    section 2:

    "In a series of three or more terms with a single conjunction, use
     a comma after each term except the last."

    Beware that this is US English and is wrong for non-US.
    """
    items = list(items)
    if len(items) <= 2:
        return (' %s ' % conjunction).join(items)
    else:
        items[-1] = '%s %s' % (conjunction, items[-1])
        return ', '.join(items)
