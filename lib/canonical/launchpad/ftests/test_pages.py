
# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Run all of the pagetests, in priority order.

Set up the test data in the database first.
"""
__metaclass__ = type

import doctest
import os
import re
import unittest

from BeautifulSoup import (BeautifulSoup, Comment, Declaration,
    NavigableString, PageElement, ProcessingInstruction, SoupStrainer, Tag)
from urlparse import urljoin

from zope.app.testing.functional import HTTPCaller, SimpleCookie
from zope.testbrowser.testing import Browser

from canonical.functional import PageTestDocFileSuite, SpecialOutputChecker
from canonical.testing import PageTestLayer


here = os.path.dirname(os.path.realpath(__file__))


class UnstickyCookieHTTPCaller(HTTPCaller):
    """HTTPCaller subclass that do not carry cookies across requests.

    HTTPCaller propogates cookies between subsequent requests.
    This is a nice feature, except it triggers a bug in Launchpad where
    sending both Basic Auth and cookie credentials raises an exception
    (Bug 39881).
    """
    def __init__(self, *args, **kw):
        if kw.get('debug'):
            self._debug = True
            del kw['debug']
        else:
            self._debug = False
        HTTPCaller.__init__(self, *args, **kw)
    def __call__(self, *args, **kw):
        if self._debug:
            import pdb; pdb.set_trace()
        try:
            return HTTPCaller.__call__(self, *args, **kw)
        finally:
            self.resetCookies()

    def resetCookies(self):
        self.cookies = SimpleCookie()


class DuplicateIdError(Exception):
    """Raised by find_tag_by_id if more than one element has the given id."""


def find_tag_by_id(content, id):
    """Find and return the tag with the given ID"""
    elements_with_id = [tag for tag in BeautifulSoup(
        content, parseOnlyThese=SoupStrainer(id=id))]
    if len(elements_with_id) == 0:
        return None
    elif len(elements_with_id) == 1:
        return elements_with_id[0]
    else:
        raise DuplicateIdError(
            'Found %d elements with id %r' % (len(elements_with_id), id))


def first_tag_by_class(content, class_):
    """Find and return the first tag matching the given class(es)"""
    return find_tags_by_class(content, class_, True)


def find_tags_by_class(content, class_, only_first=False):
    """Find and return one or more tags matching the given class(es)"""
    match_classes = set(class_.split())
    def class_matcher(value):
        if value is None: return False
        classes = set(value.split())
        return match_classes.issubset(classes)
    soup = BeautifulSoup(
        content, parseOnlyThese=SoupStrainer(attrs={'class': class_matcher}))
    if only_first:
        find=BeautifulSoup.find
    else:
        find=BeautifulSoup.findAll
    return find(soup, attrs={'class': class_matcher})


def find_portlet(content, name):
    """Find and return the portlet with the given title. Sequences of
    whitespace are considered equivalent to one space, and beginning and
    ending whitespace is also ignored, as are non-text elements such as
    images.
    """
    whitespace_re = re.compile('\s+')
    name = whitespace_re.sub(' ', name.strip())
    for portlet in find_tags_by_class(content, 'portlet'):
        if portlet.find('h2'):
            portlet_title = extract_text(portlet.find('h2'))
            if name == whitespace_re.sub(' ', portlet_title.strip()):
                return portlet
    return None


def find_main_content(content):
    """Find and return the main content area of the page"""
    return find_tag_by_id(content, 'maincontent')


def get_feedback_messages(content):
    """Find and return the feedback messages of the page."""
    message_classes = [
        'message', 'informational message', 'error message', 'warning message']
    soup = BeautifulSoup(
        content,
        parseOnlyThese=SoupStrainer(['div', 'p'], {'class': message_classes}))
    return [extract_text(tag) for tag in soup]


IGNORED_ELEMENTS = [Comment, Declaration, ProcessingInstruction]
ELEMENTS_INTRODUCING_NEWLINE = [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'pre', 'dl',
    'div', 'noscript', 'blockquote', 'form', 'hr', 'table', 'fieldset',
    'address', 'li', 'dt', 'dd', 'th', 'td', 'caption', 'br']


NEWLINES_RE = re.compile(u'\n+')
LEADING_AND_TRAILING_SPACES_RE = re.compile(u'(^[ \t]+)|([ \t]$)', re.MULTILINE)
TABS_AND_SPACES_RE = re.compile(u'[ \t]+')
NBSP_RE = re.compile(u'&nbsp;|&#160;')


def extract_link_from_tag(tag, base=None):
    """Return a link from <a> `tag`, optionally considered relative to `base`.

    A `tag` should contain a 'href' attribute, and `base` will commonly
    be extracted from browser.url.
    """
    if not isinstance(tag, PageElement):
        link = BeautifulSoup(tag)
    else:
        link = tag

    href = dict(link.attrs).get('href')
    if base is None:
        return href
    else:
        return urljoin(base, href)

def extract_text(content):
    """Return the text stripped of all tags.

    All runs of tabs and spaces are replaced by a single space and runs of
    newlines are replaced by a single newline. Leading and trailing white
    spaces is stripped.
    """
    if not isinstance(content, PageElement):
        soup = BeautifulSoup(content)
    else:
        soup = content

    result = []
    nodes = list(soup)
    while nodes:
        node = nodes.pop(0)
        if type(node) in IGNORED_ELEMENTS:
            continue
        elif isinstance(node, NavigableString):
            result.append(unicode(node))
        else:
            if isinstance(node, Tag):
                if node.name.lower() in ELEMENTS_INTRODUCING_NEWLINE:
                    result.append(u'\n')
            # Process this node's children next.
            nodes[0:0] = list(node)

    text = u''.join(result)
    text = NBSP_RE.sub(' ', text)
    text = TABS_AND_SPACES_RE.sub(' ', text)
    text = LEADING_AND_TRAILING_SPACES_RE.sub('', text)
    text = NEWLINES_RE.sub('\n', text)

    # Remove possible newlines at beginning and end.
    return text.strip()


# XXX cprov 2007-02-07: This function seems to be more specific to a
# particular product (soyuz) than the rest. Maybe it belongs to
# somewhere else.
def parse_relationship_section(content):
    """Parser package relationship section.

    See package-relationship-pages.txt and related.
    """
    soup = BeautifulSoup(content)
    section = soup.find('ul')
    whitespace_re = re.compile('\s+')
    for li in section.findAll('li'):
        if li.a:
            link = li.a
            content = whitespace_re.sub(' ', link.string.strip())
            url = link['href']
            print 'LINK: "%s" -> %s' % (content, url)
        else:
            content = whitespace_re.sub(' ', li.string.strip())
            print 'TEXT: "%s"' % content


def print_tab_links(content):
    """Print tabs url or 'Unavailable' if there isn't one."""
    chooser = find_tag_by_id(content, 'applicationchooser')
    tabs = chooser.findAll('li')
    for tab in tabs:
        if 'current' in tab['class']:
            print '%s: %s' % (tab.a.string, tab.a['href'])
        else:
            print '%s: Unavailable' % (tab.string,)


def print_action_links(content):
    """Print action menu urls."""
    actions = find_portlet(content, 'Actions')
    entries = actions.findAll('li')
    for entry in entries:
        if entry.a:
            print '%s: %s' % (entry.a.string, entry.a['href'])
        elif entry.strong:
            print entry.strong.string

def print_comments(page):
    """Print the comments on a BugTask index page."""
    main_content = find_main_content(page)
    for comment in main_content('div', 'boardCommentBody'):
        for li_tag in comment('li'):
            print "Attachment: %s" % li_tag.a.renderContents()
        print comment.div.renderContents()
        print "-"*40


def setupBrowser(auth=None):
    """Create a testbrowser object for use in pagetests.

    :param auth: HTTP authentication string. None for the anonymous user, or a
        string of the form 'Basic email:password' for an authenticated user.
    :return: A `Browser` object.
    """
    # Set up our Browser objects with handleErrors set to False, since
    # that gives a tracebacks instead of unhelpful error messages.
    browser = Browser()
    browser.handleErrors = False
    if auth is not None:
        browser.addHeader("Authorization", auth)
    return browser


def setUpGlobs(test):
    # Our tests report being on a different port.
    test.globs['http'] = UnstickyCookieHTTPCaller(port=9000)
    test.globs['setupBrowser'] = setupBrowser
    test.globs['browser'] = setupBrowser()
    test.globs['anon_browser'] = setupBrowser()
    test.globs['user_browser'] = setupBrowser(
        auth="Basic no-priv@canonical.com:test")
    test.globs['admin_browser'] = setupBrowser(
        auth="Basic foo.bar@canonical.com:test")

    test.globs['find_tag_by_id'] = find_tag_by_id
    test.globs['first_tag_by_class'] = first_tag_by_class
    test.globs['find_tags_by_class'] = find_tags_by_class
    test.globs['find_portlet'] = find_portlet
    test.globs['find_main_content'] = find_main_content
    test.globs['get_feedback_messages'] = get_feedback_messages
    test.globs['extract_link_from_tag'] = extract_link_from_tag
    test.globs['extract_text'] = extract_text
    test.globs['parse_relationship_section'] = parse_relationship_section
    test.globs['print_tab_links'] = print_tab_links
    test.globs['print_action_links'] = print_action_links
    test.globs['print_comments'] = print_comments


class PageStoryTestCase(unittest.TestCase):
    """A test case that represents a pagetest story

    This is achieved by holding a testsuite for the story, and
    delegating responsiblity for most methods to it.
    We want this to be a TestCase instance and not a TestSuite
    instance to be compatible with various test runners that
    filter tests - they generally ignore test suites and may
    select individual tests - but stories cannot be split up.
    """

    layer = PageTestLayer

    def __init__(self, name, storysuite):
        """Create a PageTest story from the given suite.

        :param name: an identifier for the story, such as the directory
            containing the tests.
        :param storysuite: a test suite containing the tests to be run
            as a story.
        """
        # we do not run the super __init__ because we are not using any of
        # the base classes functionality, and we'd just have to give it a
        # meaningless method.
        self._description = name
        self._suite = storysuite

    def countTestCases(self):
        return self._suite.countTestCases()

    def shortDescription(self):
        return "pagetest: %s" % self._description

    def id(self):
        return self.shortDescription()

    def __str__(self):
        return self.shortDescription()

    def __repr__(self):
        return "<%s name=%s>" % (self.__class__.__name__, self._description)

    def run(self, result=None):
        if result is None:
            result = self.defaultTestResult()
        PageTestLayer.startStory()
        try:
            # TODO RBC 20060117 we can hook in pre and post story actions
            # here much more tidily (and in self.debug too)
            # - probably via self.setUp and self.tearDown
            self._suite.run(result)
        finally:
            PageTestLayer.endStory()

    def debug(self):
        self._suite.debug()


# This function name doesn't follow our standard naming conventions,
# but does follow the convention of the other doctest related *Suite()
# functions.

def PageTestSuite(storydir, package=None, setUp=setUpGlobs):
    """Create a suite of page tests for files found in storydir.

    :param storydir: the directory containing the page tests.
    :param package: the package to resolve storydir relative to.  Defaults
        to the caller's package.

    The unnumbered page tests will be added to the suite individually,
    while the numbered tests will be run together as a story.
    """
    # we need to normalise the package name here, because it
    # involves checking the parent stack frame.  Otherwise the
    # files would be looked up relative to this module.
    package = doctest._normalize_module(package)
    abs_storydir = doctest._module_relative_path(package, storydir)

    filenames = set(filename
                    for filename in os.listdir(abs_storydir)
                    if filename.lower().endswith('.txt'))
    numberedfilenames = set(filename for filename in filenames
                            if len(filename) > 4
                            and filename[:2].isdigit()
                            and filename[2] == '-')
    unnumberedfilenames = filenames - numberedfilenames

    # A predictable order is important, even if it remains officially
    # undefined for un-numbered filenames.
    numberedfilenames = sorted(numberedfilenames)
    unnumberedfilenames = sorted(unnumberedfilenames)

    # Add unnumbered tests to the suite individually.
    checker = SpecialOutputChecker()
    suite = PageTestDocFileSuite(
        package=package, checker=checker,
        layer=PageTestLayer, setUp=setUp,
        *[os.path.join(storydir, filename)
          for filename in unnumberedfilenames])

    # Add numbered tests to the suite as a single story.
    storysuite = PageTestDocFileSuite(
        package=package, checker=checker,
        layer=PageTestLayer, setUp=setUp,
        *[os.path.join(storydir, filename)
          for filename in numberedfilenames])
    suite.addTest(PageStoryTestCase(abs_storydir, storysuite))

    return suite


def test_suite():
    pagetestsdir = os.path.join('..', 'pagetests')
    abs_pagetestsdir = os.path.abspath(
        os.path.normpath(os.path.join(here, pagetestsdir)))

    stories = [
        os.path.join(pagetestsdir, d)
        for d in os.listdir(abs_pagetestsdir)
        if not d.startswith('.') and
           os.path.isdir(os.path.join(abs_pagetestsdir, d))
        ]
    stories.sort()

    suite = unittest.TestSuite()

    for storydir in stories:
        suite.addTest(PageTestSuite(storydir))
    return suite
