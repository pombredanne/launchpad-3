"""The webapp package contains infrastructure that is common across Launchpad
that is to do with aspects such as security, menus, zcml, tales and so on.

This module also has an API for use by the application.
"""

__all__ = ['Link', 'DefaultLink', 'FacetMenu', 'ExtraFacetMenu',
           'ApplicationMenu', 'ExtraApplicationMenu', 'nearest_menu',
           'canonical_url', 'nearest', 'StandardLaunchpadFacets']

from canonical.launchpad.webapp.menu import (
    Link, DefaultLink, FacetMenu, ExtraFacetMenu,
    ApplicationMenu, ExtraApplicationMenu, nearest_menu)

from canonical.launchpad.webapp.publisher import canonical_url, nearest

class StandardLaunchpadFacets(FacetMenu):
    """The standard set of facets that most faceted content objects have."""

    # provide your own 'usedfor' in subclasses.
    #   usedfor = IWhatever

    links = ['overview', 'bugs', 'bounties', 'translations', 'calendar']

    def overview(self):
        target = ''
        text = 'Overview'
        return DefaultLink(target, text)

    def translations(self):
        target = '+translations'
        text = 'Translations'
        return Link(target, text)

    def bugs(self):
        target = '+bugs'
        text = 'Bugs'
        return Link(target, text)

    def bounties(self):
        target = '+bounties'
        text = 'Bounties'
        summary = 'Bounties related to %s' % self.context.title
        return Link(target, text, summary)

    def calendar(self):
        """Disabled calendar link."""
        target = '+calendar'
        text = 'Calendar'
        return Link(target, text, linked=False)

