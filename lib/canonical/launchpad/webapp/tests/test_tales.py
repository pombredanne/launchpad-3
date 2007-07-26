# Copyright 2004 Canonical Ltd.  All rights reserved.
"""tales.py doc and unit tests."""

import re
from timeit import Timer
import unittest

from zope.testing.doctestunit import DocTestSuite

from canonical.launchpad.webapp.tales import FormattersAPI


def test_requestapi():
    """
    >>> from canonical.launchpad.webapp.tales import IRequestAPI, RequestAPI
    >>> from canonical.launchpad.interfaces import IPerson
    >>> from zope.interface.verify import verifyObject

    >>> class FakePrincipal:
    ...     def __conform__(self, protocol):
    ...         if protocol is IPerson:
    ...             return "This is a person"
    ...

    >>> class FakeApplicationRequest:
    ...    principal = FakePrincipal()
    ...

    Let's make a fake request, where request.principal is a FakePrincipal
    object.  We can use a class or an instance here.  It really doesn't
    matter.

    >>> request = FakeApplicationRequest
    >>> adapter = RequestAPI(request)

    >>> verifyObject(IRequestAPI, adapter)
    True

    >>> adapter.person
    'This is a person'

    """

def test_dbschemaapi():
    """
    >>> from canonical.launchpad.webapp.tales import DBSchemaAPI
    >>> from canonical.lp.dbschema import ManifestEntryType

    The syntax to get the title is: number/lp:DBSchemaClass

    >>> (str(DBSchemaAPI(4).traverse('ManifestEntryType', []))
    ...  == ManifestEntryType.TAR.title)
    True

    Using an inappropriate number should give a KeyError.

    >>> DBSchemaAPI(99).traverse('ManifestEntryType', [])
    Traceback (most recent call last):
    ...
    KeyError: 99

    Using a dbschema name that doesn't exist should give a TraversalError

    >>> DBSchemaAPI(99).traverse('NotADBSchema', [])
    Traceback (most recent call last):
    ...
    TraversalError: 'NotADBSchema'

    We should also test names that are in the dbschema module, but are
    not DBSchemas.

    >>> import canonical.lp.dbschema
    >>> from canonical.lp.dbschema import Item
    >>> DBSchemaAPI(1).traverse('Item', [])
    Traceback (most recent call last):
    ...
    TraversalError: 'Item'

    """

def test_split_paragraphs():
    r"""
    The split_paragraphs() method is used to split a block of text
    into paragraphs, which are separated by one or more blank lines.
    Paragraphs are yielded as a list of lines in the paragraph.

      >>> from canonical.launchpad.webapp.tales import split_paragraphs
      >>> for paragraph in split_paragraphs('\na\nb\n\nc\nd\n\n\n'):
      ...     print paragraph
      ['a', 'b']
      ['c', 'd']
    """

def test_re_substitute():
    """
    When formatting text, we want to replace portions with links.
    re.sub() works fairly well for this, but doesn't give us much
    control over the non-matched text.  The re_substitute() function
    lets us do that.

      >>> import re
      >>> from canonical.launchpad.webapp.tales import re_substitute

      >>> def match_func(match):
      ...     return '[%s]' % match.group()
      >>> def nomatch_func(text):
      ...     return '{%s}' % text

      >>> pat = re.compile('a{2,6}')
      >>> print re_substitute(pat, match_func, nomatch_func,
      ...                     'bbaaaabbbbaaaaaaa aaaaaaaab')
      {bb}[aaaa]{bbbb}[aaaaaa]{a }[aaaaaa][aa]{b}
    """

def test_add_word_breaks():
    """
    Long words can cause page layout problems, so we insert manual
    word breaks into long words.  Breaks are added at least once every
    15 characters, but will break on as little as 7 characters if
    there is a suitable non-alphanumeric character to break after.

      >>> from canonical.launchpad.webapp.tales import add_word_breaks

      >>> print add_word_breaks('abcdefghijklmnop')
      abcdefghijklmno<wbr></wbr>p

      >>> print add_word_breaks('abcdef/ghijklmnop')
      abcdef/<wbr></wbr>ghijklmnop

      >>> print add_word_breaks('ab/cdefghijklmnop')
      ab/cdefghijklmn<wbr></wbr>op

    The string can contain HTML entities, which do not get split:
    
      >>> print add_word_breaks('abcdef&anentity;hijklmnop')
      abcdef&anentity;<wbr></wbr>hijklmnop
    """

def test_break_long_words():
    """
    If we have a long HTML string, break_long_words() can be used to
    add word breaks to the long words.  It will not add breaks inside HTML
    tags.  Only words longer than 20 characters will have breaks added.

      >>> from canonical.launchpad.webapp.tales import break_long_words

      >>> print break_long_words('1234567890123456')
      1234567890123456

      >>> print break_long_words('12345678901234567890')
      123456789012345<wbr></wbr>67890

      >>> print break_long_words('<tag a12345678901234567890="foo"></tag>')
      <tag a12345678901234567890="foo"></tag>

      >>> print break_long_words('12345678901234567890 1234567890.1234567890')
      123456789012345<wbr></wbr>67890 1234567890.<wbr></wbr>1234567890

      >>> print break_long_words('1234567890&abcdefghi;123')
      1234567890&abcdefghi;123

      >>> print break_long_words('<tag>1234567890123456</tag>')
      <tag>1234567890123456</tag>
    """


class testObfuscateEmail(unittest.TestCase):
    """Show that the current re is faster than the previous re."""
    def re_time_check(self, pattern, text):
        """Return the time the re takes to complete in CPU seconds. """
        # The pattern may be a verbose multiline string. Timer cannot
        # handle multiline strings.
        lines = []
        for line in pattern.split('\n'):
            pattern_fragment = line.split('#')[0]
            lines.append(pattern_fragment.strip())
        # Timer is performing a complile on the statement and setup;
        # indentation must be correct.
        setup = (
            """import re\n"""
            """test_re = re.compile('''%s''')\n""" % ''.join(lines))
        statement = ("test_re.sub(r'<email address hidden>', '%s')" % text)
        return Timer(stmt=statement, setup=setup).timeit(1)

    def test_time(self):
        """Test that the current _re_email is faster than the original."""
        # This is string was extracted from an actual message that hung
        # the server as it waited for the re to complete its sub().
        bad_address = (
            'b "medi-cal.wei@sa-raSpinning...............................'
            '............................................................'
            '............................................................'
            '............................................................'
            '............................................................'
            '.........................................................not')
        # This version of _re_email was created in response to bad_address.
        orginal_pattern = r"""
            ([\b]|[\"']?)[-/=0-9A-Z_a-z]     # First character of localname.
            [.\"'-/=0-9A-Z_a-z+]*@           # Remainder of the localname.
            [a-zA-Z]                         # First character of hostname.
            (-?[a-zA-Z0-9])*                 # Remainder of the hosename.
            (\.[a-zA-Z](-?[a-zA-Z0-9])*)+\b  # Dot starts one or more domains.
            """
        current_pattern = FormattersAPI._re_email.pattern

        orginal_time = self.re_time_check(orginal_pattern, bad_address)
        current_time = self.re_time_check(current_pattern, bad_address)
        self.failIf(orginal_time < current_time,
                    'original_re is faster than the current email_re: '
                    '%s < %s' % (orginal_time, current_time))


def test_suite():
    """Return this module's doctest Suite. Unit tests are not run."""
    suite = DocTestSuite()
    return suite


if __name__ == '__main__':
    # Run unit tests, eg. testObfuscateEmail().
    unittest.main()
