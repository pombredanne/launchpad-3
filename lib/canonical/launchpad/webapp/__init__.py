# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""The webapp package contains infrastructure that is common across Launchpad
that is to do with aspects such as security, menus, zcml, tales and so on.

This module also has an API for use by the application.
"""
__metaclass__ = type

__all__ = [
    'action',
    'ApplicationMenu',
    'canonical_name',
    'canonical_url',
    'ContextMenu',
    'custom_widget',
    'enabled_with_permission',
    'expand_numbers',
    'ExportedFolder',
    'FacetMenu',
    'GeneralFormView',
    'GeneralFormViewFactory',
    'GetitemNavigation',
    'LaunchpadEditFormView',
    'LaunchpadFormView',
    'LaunchpadView',
    'LaunchpadXMLRPCView',
    'Link',
    'Navigation',
    'NavigationMenu',
    'nearest',
    'nearest_adapter',
    'nearest_context_with_adapter',
    'redirection',
    'safe_action',
    'sorted_dotted_numbers',
    'sorted_version_numbers',
    'StandardLaunchpadFacets',
    'stepthrough',
    'stepto',
    'structured',
    'UnsafeFormGetSubmissionError',
    'urlappend',
    'urlparse',
    'urlsplit',
    'Utf8PreferredCharsets',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.generalform import (
    GeneralFormView, GeneralFormViewFactory
    )
from canonical.launchpad.webapp.launchpadform import (
    LaunchpadFormView, LaunchpadEditFormView, action, custom_widget,
    safe_action)
from canonical.launchpad.webapp.menu import (
    ApplicationMenu, ContextMenu, FacetMenu, Link, NavigationMenu,
    enabled_with_permission, nearest_adapter, nearest_context_with_adapter,
    structured)
from canonical.launchpad.webapp.preferredcharsets import Utf8PreferredCharsets
from canonical.launchpad.webapp.publisher import (
    canonical_name, canonical_url, nearest, LaunchpadView, Navigation,
    stepthrough, redirection, stepto, LaunchpadXMLRPCView)
from canonical.launchpad.webapp.sorting import (
    expand_numbers, sorted_version_numbers, sorted_dotted_numbers)
from canonical.launchpad.webapp.url import urlappend, urlparse, urlsplit


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

    enable_only = ['overview', 'bugs', 'specifications', 'translations']

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
        text = 'Overview'
        return Link('', text)

    def translations(self):
        text = 'Translations'
        return Link('', text)

    def bugs(self):
        text = 'Bugs'
        return Link('', text)

    def answers(self):
        # This facet is visible but unavailable by default.
        # See the enable_only list above.
        text = 'Answers'
        summary = 'Launchpad Answer Tracker'
        return Link('', text, summary)

    def specifications(self):
        text = 'Blueprints'
        summary = 'Blueprints and specifications'
        return Link('', text, summary)

    def bounties(self):
        target = '+bounties'
        text = 'Bounties'
        summary = 'View related bounty offers'
        return Link(target, text, summary)

    def branches(self):
        # this is disabled by default, because relatively few objects have
        # branch views
        text = 'Code'
        summary = 'View related branches of code'
        return Link('', text, summary=summary)
