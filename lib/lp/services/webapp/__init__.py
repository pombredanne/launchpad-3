# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The webapp package contains infrastructure that is common across Launchpad
that is to do with aspects such as security, menus, zcml, tales and so on.

This module also has an API for use by the application.
"""
__metaclass__ = type

__all__ = [
    'ApplicationMenu',
    'canonical_name',
    'canonical_url',
    'ContextMenu',
    'available_with_permission',
    'enabled_with_permission',
    'expand_numbers',
    'FacetMenu',
    'GetitemNavigation',
    'LaunchpadView',
    'LaunchpadXMLRPCView',
    'Link',
    'Navigation',
    'NavigationMenu',
    'nearest',
    'redirection',
    'sorted_dotted_numbers',
    'sorted_version_numbers',
    'StandardLaunchpadFacets',
    'stepthrough',
    'stepto',
    'structured',
    'urlappend',
    'urlparse',
    'urlsplit',
    'Utf8PreferredCharsets',
    ]

from lp.services.features import getFeatureFlag
from lp.services.webapp.escaping import structured
from lp.services.webapp.menu import (
    ApplicationMenu,
    ContextMenu,
    enabled_with_permission,
    FacetMenu,
    Link,
    NavigationMenu,
    )
from lp.services.webapp.preferredcharsets import Utf8PreferredCharsets
from lp.services.webapp.publisher import (
    canonical_name,
    canonical_url,
    LaunchpadView,
    LaunchpadXMLRPCView,
    Navigation,
    nearest,
    redirection,
    stepthrough,
    stepto,
    )
from lp.services.webapp.sorting import (
    expand_numbers,
    sorted_dotted_numbers,
    sorted_version_numbers,
    )
from lp.services.webapp.url import (
    urlappend,
    urlparse,
    urlsplit,
    )


class GetitemNavigation(Navigation):
    """Base class for navigation where fall-back traversal uses context[name].
    """

    def traverse(self, name):
        return self.context[name]


class StandardLaunchpadFacets(FacetMenu):
    """The standard set of facets that most faceted content objects have."""

    # provide your own 'usedfor' in subclasses.
    #   usedfor = IWhatever

    links = [
        'overview',
        'branches',
        'bugs',
        'specifications',
        'translations',
        'answers',
        ]

    defaultlink = 'overview'

    @property
    def mainsite_only(self):
        return getFeatureFlag('app.mainsite_only.canonical_url')

    def overview(self):
        text = 'Overview'
        return Link('', text, site='mainsite')

    def branches(self):
        text = 'Code'
        target = '+branches' if self.mainsite_only else ''
        site = 'mainsite' if self.mainsite_only else 'code'
        return Link(target, text, site=site)

    def bugs(self):
        text = 'Bugs'
        target = '+bugs' if self.mainsite_only else ''
        site = 'mainsite' if self.mainsite_only else 'bugs'
        return Link(target, text, site=site)

    def specifications(self):
        text = 'Blueprints'
        target = '+specs' if self.mainsite_only else ''
        site = 'mainsite' if self.mainsite_only else 'blueprints'
        return Link(target, text, site=site)

    def translations(self):
        text = 'Translations'
        target = '+translations' if self.mainsite_only else ''
        site = 'mainsite' if self.mainsite_only else 'translations'
        return Link(target, text, site=site)

    def answers(self):
        text = 'Answers'
        target = '+questions' if self.mainsite_only else ''
        site = 'mainsite' if self.mainsite_only else 'answers'
        return Link(target, text, site=site)
