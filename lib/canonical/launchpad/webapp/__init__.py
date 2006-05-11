# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""The webapp package contains infrastructure that is common across Launchpad
that is to do with aspects such as security, menus, zcml, tales and so on.

This module also has an API for use by the application.
"""
__metaclass__ = type

__all__ = ['Link', 'FacetMenu', 'ApplicationMenu', 'ContextMenu',
           'nearest_menu', 'canonical_url', 'nearest', 'structured',
           'StandardLaunchpadFacets', 'enabled_with_permission',
           'LaunchpadView', 'LaunchpadXMLRPCView',
           'Navigation', 'stepthrough', 'redirection',
           'stepto', 'GetitemNavigation', 'smartquote', 'urlparse',
           'GeneralFormView', 'GeneralFormViewFactory',
           'LaunchpadBrowserRequest', 'LaunchpadBrowserResponse']

import re
from  urlparse import (
    urljoin, urlparse as original_urlparse, urlsplit as original_urlsplit)

from zope.component import getUtility

from canonical.launchpad.webapp.generalform import (
    GeneralFormView, GeneralFormViewFactory
    )
from canonical.launchpad.webapp.menu import (
    Link, FacetMenu, ApplicationMenu, ContextMenu, nearest_menu, structured,
    enabled_with_permission
    )
from canonical.launchpad.webapp.publisher import (
    canonical_url, nearest, LaunchpadView, Navigation, stepthrough,
    redirection, stepto, LaunchpadXMLRPCView)
from canonical.launchpad.webapp.servers import (
        LaunchpadBrowserRequest, LaunchpadBrowserResponse
        )
from canonical.launchpad.interfaces import ILaunchBag


def smartquote(str):
    """Return a copy of the string provided, with smartquoting applied.

    >>> smartquote('')
    u''
    >>> smartquote('foo "bar" baz')
    u'foo \u201cbar\u201d baz'
    >>> smartquote('foo "bar baz')
    u'foo \u201cbar baz'
    >>> smartquote('foo bar" baz')
    u'foo bar\u201d baz'
    >>> smartquote('""foo " bar "" baz""')
    u'""foo " bar "" baz""'
    >>> smartquote('" foo "')
    u'" foo "'
    """
    str = unicode(str)
    str = re.compile(u'(^| )(")([^" ])').sub(u'\\1\u201c\\3', str)
    str = re.compile(u'([^ "])(")($| )').sub(u'\\1\u201d\\3', str)
    return str


def urlappend(baseurl, path):
    """Append the given path to baseurl.

    The path must not start with a slash, but a slash is added to baseurl
    (before appending the path), in case it doesn't end with a slash.

    >>> urlappend('http://foo.bar', 'spam/eggs')
    'http://foo.bar/spam/eggs'
    >>> urlappend('http://localhost:11375/foo', 'bar/baz')
    'http://localhost:11375/foo/bar/baz'
    """
    assert not path.startswith('/')
    if not baseurl.endswith('/'):
        baseurl += '/'
    return urljoin(baseurl, path)


def urlparse(url, scheme='', allow_fragments=True):
    """Convert url to a str object and call the original urlparse function.

    The url parameter should contain ASCII characters only. This
    function ensures that the original urlparse is called always with a
    str object, and never unicode.

        >>> urlparse(u'http://foo.com/bar')
        ('http', 'foo.com', '/bar', '', '', '')

        >>> urlparse('http://foo.com/bar')
        ('http', 'foo.com', '/bar', '', '', '')

        >>> original_urlparse('http://foo.com/bar')
        ('http', 'foo.com', '/bar', '', '', '')

    This is needed since external libraries might expect that the original
    urlparse returns a str object if it is given a str object. However,
    that might not be the case, since urlparse has a cache, and treats
    unicode and str as equal. (http://sourceforge.net/tracker/index.php?
    func=detail&aid=1313119&group_id=5470&atid=105470)

        >>> original_urlparse(u'http://foo.com/')
        (u'http', u'foo.com', u'/', '', '', '')
        >>> original_urlparse('http://foo.com/')
        (u'http', u'foo.com', u'/', '', '', '')

    """
    return original_urlparse(
        url.encode('ascii'), scheme=scheme, allow_fragments=allow_fragments)


def urlsplit(url, scheme='', allow_fragments=True):
    """Convert url to a str object and call the original urlsplit function.

    The url parameter should contain ASCII characters only. This
    function ensures that the original urlsplit is called always with a
    str object, and never unicode.

        >>> urlsplit(u'http://foo.com/baz')
        ('http', 'foo.com', '/baz', '', '')

        >>> urlsplit('http://foo.com/baz')
        ('http', 'foo.com', '/baz', '', '')

        >>> original_urlsplit('http://foo.com/baz')
        ('http', 'foo.com', '/baz', '', '')

    """
    return original_urlsplit(
        url.encode('ascii'), scheme=scheme, allow_fragments=allow_fragments)


class GetitemNavigation(Navigation):
    """Base class for navigation where fall-back traversal uses context[name].
    """

    def traverse(self, name):
        return self.context[name]


class StandardLaunchpadFacets(FacetMenu):
    """The standard set of facets that most faceted content objects have."""

    # provide your own 'usedfor' in subclasses.
    #   usedfor = IWhatever

    links = ['overview', 'bugs', 'support', 'bounties', 'specifications',
             'translations', 'branches', 'calendar']

    enable_only = ['overview', 'bugs', 'bounties', 'specifications',
                   'translations', 'calendar']

    defaultlink = 'overview'

    def overview(self):
        target = ''
        text = 'Overview'
        return Link(target, text)

    def translations(self):
        target = '+translations'
        text = 'Translations'
        return Link(target, text)

    def bugs(self):
        target = '+bugs'
        text = 'Bugs'
        return Link(target, text)

    def support(self):
        # This facet is visible but unavailable by default.
        # See the enable_only list above.
        target = '+tickets'
        text = 'Support'
        summary = 'Technical Support Requests'
        return Link(target, text, summary)

    def specifications(self):
        target = '+specs'
        text = 'Specifications'
        summary = 'Feature Specifications and Plans'
        return Link(target, text, summary)

    def bounties(self):
        target = '+bounties'
        text = 'Bounties'
        summary = 'View related bounty offers'
        return Link(target, text, summary)

    def calendar(self):
        """Disabled calendar link."""
        target = '+calendar'
        text = 'Calendar'
        return Link(target, text, enabled=False)

    def branches(self):
        # this is disabled by default, because relatively few objects have
        # branch views
        target = '+branches'
        text = 'Branches'
        summary = 'View related branches of code'
        return Link(target, text, summary=summary)

