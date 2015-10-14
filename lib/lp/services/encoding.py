# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Character encoding utilities"""

__metaclass__ = type
__all__ = [
    'escape_nonascii_uniquely',
    'guess',
    'is_ascii_only',
    ]

import codecs
import re


_boms = [
    (codecs.BOM_UTF16_BE, 'utf_16_be'),
    (codecs.BOM_UTF16_LE, 'utf_16_le'),
    (codecs.BOM_UTF32_BE, 'utf_32_be'),
    (codecs.BOM_UTF32_LE, 'utf_32_le'),
    ]


def guess(s):
    r'''
    Attempts to heuristically guess a strings encoding, returning
    a Unicode string.

    This method should only be used for importing legacy data from systems
    or files where the encoding is not known. This method will always
    succeed and normally guess the correct encoding, but it is only
    a guess and will be incorrect some of the time. Also note that
    data may be lost, as if we cannot determine the correct encoding
    we fall back to ISO-8859-1 and replace unrecognized characters with
    \ufffd characters (the Unicode unrepresentable code point).

    NB: We currently only cope with the major Western character
    sets - we need to change the algorithm to cope with asian languages.
    One way that apparently works is to convert the string into all possible
    encodings, one at a time, and if successful score them based on the
    number of meaningful characters (using the unicodedata module to
    let us know what are control characters, letters, printable characters
    etc.).


    ASCII is easy

    >>> guess('hello')
    u'hello'

    Unicode raises an exception to annoy lazy programmers. It should also
    catches bugs as if you have valid Unicode you shouldn't be going anywhere
    near this method.

    >>> guess(u'Caution \N{BIOHAZARD SIGN}')
    Traceback (most recent call last):
    ...
    TypeError: ...

    UTF-8 is our best guess

    >>> guess(u'100% Pure Beef\N{TRADE MARK SIGN}'.encode('UTF-8'))
    u'100% Pure Beef\u2122'

    But we fall back to ISO-8859-1 if UTF-8 fails

    >>> u = u'Ol\N{LATIN SMALL LETTER E WITH ACUTE}'
    >>> u.encode('UTF-8') == u.encode('ISO-8859-1')
    False
    >>> guess(u.encode('UTF-8'))
    u'Ol\xe9'
    >>> guess(u.encode('ISO-8859-1'))
    u'Ol\xe9'

    However, if the string contains ISO-8859-1 control characters, it is
    probably a CP1252 document (Windows).

    >>> u = u'Show me the \N{EURO SIGN}'
    >>> u.encode('UTF-8') == u.encode('CP1252')
    False
    >>> guess(u.encode('UTF-8'))
    u'Show me the \u20ac'
    >>> guess(u.encode('CP1252'))
    u'Show me the \u20ac'

    We also check for characters common in ISO-8859-15 that are uncommon
    in ISO-8859-1, and use ISO-8859-15 if they are found.

    >>> u = u'\N{LATIN SMALL LETTER S WITH CARON}'
    >>> guess(u.encode('iso-8859-15'))
    u'\u0161'

    Strings with a BOM are unambiguous.

    >>> guess(u'hello'.encode('UTF-16'))
    u'hello'

    However, UTF-16 strings without a BOM will be interpreted as ISO-8859-1.
    I doubt this is a problem, as we are unlikely to see this except with
    asian languages and in these cases other encodings we don't support
    at the moment like ISO-2022-jp, BIG5, SHIFT-JIS etc. will be a bigger
    problem.

    >>> guess(u'hello'.encode('UTF-16be'))
    u'\x00h\x00e\x00l\x00l\x00o'

    '''

    # Calling this method with a Unicode argument indicates a hidden bug
    # that will bite you eventually -- StuartBishop 20050709
    if isinstance(s, unicode):
        raise TypeError(
                'encoding.guess called with Unicode string %r' % (s,)
                )

    # Attempt to use an objects default Unicode conversion, for objects
    # that can encode themselves as ASCII.
    try:
        return unicode(s)
    except UnicodeDecodeError:
        pass

    # Detect BOM
    try:
        for bom, encoding in _boms:
            if s.startswith(bom):
                return unicode(s[len(bom):], encoding)
    except UnicodeDecodeError:
        pass

    # Try preferred encoding
    try:
        return unicode(s, 'UTF-8')
    except UnicodeDecodeError:
        pass

    # If we have characters in this range, it is probably CP1252
    if re.search(r"[\x80-\x9f]", s) is not None:
        try:
            return unicode(s, 'CP1252')
        except UnicodeDecodeError:
            pass

    # If we have characters in this range, it is probably ISO-8859-15
    if re.search(r"[\xa4\xa6\xa8\xb4\xb8\xbc-\xbe]", s) is not None:
        try:
            return unicode(s, 'ISO-8859-15')
        except UnicodeDecodeError:
            pass

    # Otherwise we default to ISO-8859-1
    return unicode(s, 'ISO-8859-1', 'replace')


def escape_nonascii_uniquely(bogus_string):
    """Replace non-ascii characters with a hex representation.

    This is mainly for preventing emails with invalid characters from causing
    oopses. The nonascii characters could have been removed or just converted
    to "?", but this provides some insight into what the bogus data was, and
    it prevents the message-id from two unrelated emails matching because
    all the nonascii characters have been replaced with the same ascii
    character.

    Unfortunately, all the strings below are actually part of this
    function's docstring, so python processes the backslash once before
    doctest, and then python processes it again when doctest runs the
    test. This makes it confusing, since four backslashes will get
    converted into a single ascii character.

    >>> print len('\xa9'), len('\\xa9'), len('\\\\xa9')
    1 1 4
    >>> print escape_nonascii_uniquely('hello \xa9')
    hello \\xa9
    >>> print escape_nonascii_uniquely('hello \\xa9')
    hello \\xa9

    This string only has ascii characters, so escape_nonascii_uniquely()
    actually has no effect.

    >>> print escape_nonascii_uniquely('hello \\\\xa9')
    hello \\xa9
    """
    nonascii_regex = re.compile(r'[\200-\377]')

    # By encoding the invalid ascii with a backslash, x, and then the
    # hex value, it makes it easy to decode it by pasting into a python
    # interpreter. quopri() is not used, since that could caused the
    # decoding of an email to fail.
    def quote(match):
        return '\\x%x' % ord(match.group(0))

    return nonascii_regex.sub(quote, bogus_string)


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
