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
           'stepto', 'GetitemNavigation', 'smartquote',
           'urlappend', 'urlparse', 'urlsplit',
           'GeneralFormView', 'GeneralFormViewFactory',
           'Utf8PreferredCharsets', 'LaunchpadFormView',
           'LaunchpadEditFormView', 'action', 'custom_widget',
           'expand_numbers','sorted_version_numbers',
           'sorted_dotted_numbers']

import re

from zope.component import getUtility

from canonical.launchpad.webapp.url import urlappend, urlparse, urlsplit
from canonical.launchpad.webapp.generalform import (
    GeneralFormView, GeneralFormViewFactory
    )
from canonical.launchpad.webapp.launchpadform import (
    LaunchpadFormView, LaunchpadEditFormView, action, custom_widget)
from canonical.launchpad.webapp.menu import (
    Link, FacetMenu, ApplicationMenu, ContextMenu, nearest_menu, structured,
    enabled_with_permission
    )
from canonical.launchpad.webapp.preferredcharsets import Utf8PreferredCharsets
from canonical.launchpad.webapp.publisher import (
    canonical_url, nearest, LaunchpadView, Navigation, stepthrough,
    redirection, stepto, LaunchpadXMLRPCView)
from canonical.launchpad.webapp.sorting import (
    expand_numbers, sorted_version_numbers, sorted_dotted_numbers)

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


class GetitemNavigation(Navigation):
    """Base class for navigation where fall-back traversal uses context[name].
    """

    def traverse(self, name):
        return self.context[name]


class StandardLaunchpadFacets(FacetMenu):
    """The standard set of facets that most faceted content objects have."""

    # provide your own 'usedfor' in subclasses.
    #   usedfor = IWhatever

    links = ['overview', 'branches', 'bugs', 'specifications', 'translations',
        'answers']

    enable_only = ['overview', 'bugs', 'specifications',
                   'translations', 'calendar']

    defaultlink = 'overview'

    def _filterLink(self, name, link):
        if link.site is None:
            if name == 'specifications':
                link.site = 'blueprints'
            elif name == 'branches':
                link.site = 'code'
            elif name == 'translations':
                link.site = 'translations'
            elif name == 'answers':
                link.site = 'answers'
            elif name == 'bugs':
                link.site = 'bugs'
            else:
                link.site = 'mainsite'
        return link

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

    def answers(self):
        # This facet is visible but unavailable by default.
        # See the enable_only list above.
        target = '+tickets'
        text = 'Answers'
        summary = 'Launchpad Answer Tracker'
        return Link(target, text, summary)

    def specifications(self):
        target = '+specs'
        text = 'Blueprints'
        summary = 'Blueprints and specifications'
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
        text = 'Code'
        summary = 'View related branches of code'
        return Link(target, text, summary=summary)

