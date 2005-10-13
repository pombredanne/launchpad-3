"""The webapp package contains infrastructure that is common across Launchpad
that is to do with aspects such as security, menus, zcml, tales and so on.

This module also has an API for use by the application.
"""

__all__ = ['Link', 'FacetMenu', 'ApplicationMenu', 'ContextMenu',
           'nearest_menu', 'canonical_url', 'nearest', 'structured',
           'StandardLaunchpadFacets', 'enabled_with_permission',
           'LaunchpadView', 'Navigation', 'stepthrough', 'redirection',
           'stepto', 'GetitemNavigation', 'LaunchpadBrowserRequest']

from zope.component import getUtility

from canonical.launchpad.webapp.menu import (
    Link, FacetMenu, ApplicationMenu, ContextMenu, nearest_menu, structured,
    enabled_with_permission)
from canonical.launchpad.webapp.publisher import (
    canonical_url, nearest, LaunchpadView, Navigation, stepthrough,
    redirection, stepto)
from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest
from canonical.launchpad.interfaces import ILaunchBag


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
        # This facet is visible but unavailable by default. You need to define
        # a 'support' facet with the Link enabled in order to get an enabled
        # 'Support' facet tab.
        target = '+tickets'
        text = 'Support'
        summary = 'Technical Support Requests'
        return Link(target, text, summary, enabled=False)

    def specifications(self):
        target = '+specs'
        text = 'Specifications'
        summary = 'New Feature Specifications'
        return Link(target, text, summary)

    def bounties(self):
        target = '+bounties'
        text = 'Bounties'
        summary = 'Bounties related to %s' % self.context.title
        return Link(target, text, summary)

    def calendar(self):
        """Disabled calendar link."""
        target = '+calendar'
        text = 'Calendar'
        return Link(target, text, enabled=False)

