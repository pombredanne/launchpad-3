# Copyright 2004, 2009 Canonical Ltd.  All rights reserved.
"""tales.py doctests."""

from textwrap import dedent
import unittest

from storm.store import Store
from zope.security.proxy import removeSecurityProxy
from zope.testing.doctestunit import DocTestSuite

from canonical.launchpad.ftests import test_tales
from canonical.launchpad.testing import login, TestCase, TestCaseWithFactory
from canonical.launchpad.testing.pages import find_tags_by_class
from canonical.launchpad.webapp.tales import FormattersAPI
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)


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
    ...    def getURL(self):
    ...        return 'http://launchpad.dev/'
    ...

    Let's make a fake request, where request.principal is a FakePrincipal
    object.  We can use a class or an instance here.  It really doesn't
    matter.

    >>> request = FakeApplicationRequest()
    >>> adapter = RequestAPI(request)

    >>> verifyObject(IRequestAPI, adapter)
    True

    >>> adapter.person
    'This is a person'

    """

def test_cookie_scope():
    """
    The 'request/lp:cookie_scope' TALES expression returns a string
    that represents the scope parameters necessary for a cookie to be
    available for the entire Launchpad site.  It takes into account
    the request URL and the cookie_domains setting in launchpad.conf.

        >>> from canonical.launchpad.webapp.tales import RequestAPI
        >>> def cookie_scope(url):
        ...     class FakeRequest:
        ...         def getURL(self):
        ...             return url
        ...     return RequestAPI(FakeRequest()).cookie_scope

    The cookie scope will use the secure attribute if the request was
    secure:

        >>> print cookie_scope('http://launchpad.net/')
        ; Path=/; Domain=.launchpad.net
        >>> print cookie_scope('https://launchpad.net/')
        ; Path=/; Secure; Domain=.launchpad.net

    The domain parameter is omitted for domains that appear to be
    separate from a Launchpad instance, such as shipit:

        >>> print cookie_scope('https://shipit.ubuntu.com/')
        ; Path=/; Secure
    """

def test_dbschemaapi():
    """
    >>> from canonical.launchpad.webapp.tales import DBSchemaAPI
    >>> from canonical.launchpad.interfaces.branch import BranchType

    The syntax to get the title is: number/lp:DBSchemaClass

    >>> (str(DBSchemaAPI(1).traverse('BranchType', []))
    ...  == BranchType.HOSTED.title)
    True

    Using an inappropriate number should give a KeyError.

    >>> DBSchemaAPI(99).traverse('BranchType', [])
    Traceback (most recent call last):
    ...
    KeyError: 99

    Using a dbschema name that doesn't exist should give a TraversalError

    >>> DBSchemaAPI(99).traverse('NotADBSchema', [])
    Traceback (most recent call last):
    ...
    TraversalError: 'NotADBSchema'

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


class TestDiffFormatter(TestCase):
    """Test the string formtter fmt:diff."""
    layer = DatabaseFunctionalLayer

    def test_emptyString(self):
        # An empty string gives an empty string.
        self.assertEqual(
            '', FormattersAPI('').format_diff())

    def test_almostEmptyString(self):
        # White space doesn't count as empty, and is formtted.
        self.assertEqual(
            '<table class="diff"><tr><td class="line-no">1</td>'
            '<td class="text"> </td></tr></table>',
            FormattersAPI(' ').format_diff())

    def test_cssClasses(self):
        # Different parts of the diff have different css classes.
        diff = dedent('''\
            === modified file 'tales.py'
            --- tales.py
            +++ tales.py
            @@ -2435,6 +2435,8 @@
                 def format_diff(self):
            -        removed this line
            +        added this line
            ########
            # A merge directive comment.
            ''')
        html = FormattersAPI(diff).format_diff()
        line_numbers = find_tags_by_class(html, 'line-no')
        self.assertEqual(
            ['1','2','3','4','5','6','7','8','9'],
            [tag.renderContents() for tag in line_numbers])
        text = find_tags_by_class(html, 'text')
        self.assertEqual(
            ['diff-file text',
             'diff-header text',
             'diff-header text',
             'diff-chunk text',
             'text',
             'diff-removed text',
             'diff-added text',
             'diff-comment text',
             'diff-comment text'],
            [str(tag['class']) for tag in text])


class TestPreviewDiffFormatter(TestCaseWithFactory):
    """Test the PreviewDiffFormatterAPI class."""

    layer = LaunchpadFunctionalLayer

    def _createPreviewDiff(self, line_count=0, added=None, removed=None,
                           conflicts=None):
        # Login an admin to avoid the launchpad.Edit requirements.
        login('admin@canonical.com')
        # Create a dummy preview diff, and make sure the branches have the
        # correct last scanned ids to ensure that the new diff is not stale.
        bmp = self.factory.makeBranchMergeProposal()
        if line_count:
            content = 'random content'
        else:
            content = None
        preview = bmp.updatePreviewDiff(
            content, u'diff stat', u'rev-a', u'rev-b', conflicts=conflicts)
        bmp.source_branch.last_scanned_id = preview.source_revision_id
        bmp.target_branch.last_scanned_id = preview.target_revision_id
        # Update the values directly sidestepping the security.
        naked_diff = removeSecurityProxy(preview)
        naked_diff.diff_lines_count = line_count
        naked_diff.added_lines_count = added
        naked_diff.removed_lines_count = removed
        # In order to get the canonical url of the librarian file, we need to commit.
        # transaction.commit()
        # Make sure that the preview diff is in the db for the test.
        # Storm bug: 324724
        Store.of(bmp).flush()
        return preview

    def _createStalePreviewDiff(self, line_count=0, added=None, removed=None,
                                conflicts=None):
        preview = self._createPreviewDiff(
            line_count, added, removed, conflicts)
        preview.branch_merge_proposal.source_branch.last_scanned_id = 'other'
        return preview

    def test_creation_method(self):
        # Just confirm that our helpers do what they say.
        preview = self._createPreviewDiff(12, 45, 23)
        self.assertEqual(12, preview.diff_lines_count)
        self.assertEqual(45, preview.added_lines_count)
        self.assertEqual(23, preview.removed_lines_count)
        self.assertEqual(False, preview.stale)
        self.assertEqual(True, self._createStalePreviewDiff().stale)

    def test_fmt_no_diff(self):
        # If there is no diff, there is no link.
        preview = self._createPreviewDiff(0)
        self.assertEqual(
            '<span title="" class="clean-diff">0 lines</span>',
            test_tales('preview/fmt:link', preview=preview))

    def test_fmt_lines_no_add_or_remove(self):
        # If there is no diff, there is no link.
        preview = self._createPreviewDiff(10, 0, 0)
        self.assertEqual(
            '<a href="%s" title="" class="clean-diff">'
            '<img src="/@@/download"/>&nbsp;10 lines</a>'
            % preview.diff_text.getURL(),
            test_tales('preview/fmt:link', preview=preview))

    def test_fmt_lines_some_added_no_removed(self):
        # If there is no diff, there is no link.
        preview = self._createPreviewDiff(10, 4, 0)
        self.assertEqual(
            '<a href="%s" title="4 added" class="clean-diff">'
            '<img src="/@@/download"/>&nbsp;10 lines</a>'
            % preview.diff_text.getURL(),
            test_tales('preview/fmt:link', preview=preview))

    def test_fmt_lines_no_added_some_removed(self):
        # If there is no diff, there is no link.
        preview = self._createPreviewDiff(10, 0, 4)
        self.assertEqual(
            '<a href="%s" title="4 removed" class="clean-diff">'
            '<img src="/@@/download"/>&nbsp;10 lines</a>'
            % preview.diff_text.getURL(),
            test_tales('preview/fmt:link', preview=preview))

    def test_fmt_lines_added_and_removed(self):
        # If there is no diff, there is no link.
        preview = self._createPreviewDiff(10, 6, 4)
        self.assertEqual(
            '<a href="%s" title="6 added, 4 removed" class="clean-diff">'
            '<img src="/@@/download"/>&nbsp;10 lines</a>'
            % preview.diff_text.getURL(),
            test_tales('preview/fmt:link', preview=preview))

    def test_fmt_simple_conflicts(self):
        # If there is no diff, there is no link.
        preview = self._createPreviewDiff(10, 2, 3, u'conflicts')
        self.assertEqual(
            '<a href="%s" title="CONFLICTS, 2 added, 3 removed" '
            'class="conflicts-diff">'
            '<img src="/@@/download"/>&nbsp;10 lines</a>'
            % preview.diff_text.getURL(),
            test_tales('preview/fmt:link', preview=preview))

    def test_fmt_stale_empty_diff(self):
        # If there is no diff, there is no link.
        preview = self._createStalePreviewDiff(0)
        self.assertEqual(
            '<span title="Stale" class="stale-diff">0 lines</span>',
            test_tales('preview/fmt:link', preview=preview))

    def test_fmt_stale_non_empty_diff(self):
        # If there is no diff, there is no link.
        preview = self._createStalePreviewDiff(500, 89, 340)
        self.assertEqual(
            '<a href="%s" title="Stale, 89 added, 340 removed" '
            'class="stale-diff"><img src="/@@/download"/>&nbsp;500 lines</a>'
            % preview.diff_text.getURL(),
            test_tales('preview/fmt:link', preview=preview))

    def test_fmt_stale_non_empty_diff_with_conflicts(self):
        # If there is no diff, there is no link.
        preview = self._createStalePreviewDiff(500, 89, 340, u'conflicts')
        self.assertEqual(
            '<a href="%s" title="CONFLICTS, Stale, 89 added, 340 removed" '
            'class="stale-diff"><img src="/@@/download"/>&nbsp;500 lines</a>'
            % preview.diff_text.getURL(),
            test_tales('preview/fmt:link', preview=preview))


def test_suite():
    """Return this module's doctest Suite. Unit tests are also run."""
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite())
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite


if __name__ == '__main__':
    unittest.main()
