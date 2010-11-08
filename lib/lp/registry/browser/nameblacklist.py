# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'NameBlacklistAddView',
    'NameBlacklistEditView',
    'NameBlacklistSetView',
    ]

import re

from zope.component import getUtility

from canonical.launchpad.webapp import action
from canonical.launchpad.webapp.launchpadform import LaunchpadFormView
from canonical.launchpad.webapp.publisher import (
    canonical_url,
    LaunchpadView,
    )

from lp.registry.browser import RegistryEditFormView
from lp.registry.interfaces.nameblacklist import (
    INameBlacklist,
    INameBlacklistSet,
    )


class NameBlacklistEditView(RegistryEditFormView):

    schema = INameBlacklist

    def validate(self, data):
        """Validate regular expression."""
        regexp = data['regexp']
        re.compile(regexp)


class NameBlacklistAddView(LaunchpadFormView):

    schema = INameBlacklist
    label = "Register a new distribution"

    '''
    @property
    def page_title(self):
        """The page title."""
        return self.label

    @property
    def cancel_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)
    '''

    @action("Save", name='save')
    def save_action(self, action, data):
        nameblacklist = getUtility(INameBlacklistSet).create(
            regexp=data['regexp'],
            displayname=data['comment'],
            )
        self.next_url = canonical_url(INameBlacklistSet)


class NameBlacklistSetView(LaunchpadView):
    """View for /+nameblacklists top level collection."""

    page_title = (
        'Blacklist for names of Launchpad pillars, persons, and teams')
    label = page_title
