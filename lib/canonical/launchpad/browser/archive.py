# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for archive."""

__metaclass__ = type

__all__ = [
    'ArchiveNavigation',
    'ArchiveFacets',
    'ArchiveOverviewMenu',
    'ArchiveView',
    ]

from canonical.launchpad.interfaces import IArchive

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Navigation, Link, LaunchpadView,
    ApplicationMenu, enabled_with_permission)


class ArchiveNavigation(Navigation):
    """Navigation methods for IArchive."""
    usedfor = IArchive

    def breadcrumb(self):
        return self.context.title

class ArchiveFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IArchive."""
    enable_only = ['overview']

    usedfor = IArchive


class ArchiveOverviewMenu(ApplicationMenu):
    """Overview Menu for IArchive."""
    usedfor = IArchive
    facet = 'overview'
    links = ['edit']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')


class ArchiveView(LaunchpadView):
    """Default Archive view class

    Implements useful actions and colect useful set for the pagetemplate.
    """
    __used_for__ = IArchive

