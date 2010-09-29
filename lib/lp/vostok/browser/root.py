# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser code for the Vostok root."""

__metaclass__ = type
__all__ = [
    'VostokRootView',
    'VostokLayerToMainTemplateAdapter',
    ]

import os

from zope.component import (
    adapts,
    getUtility,
    )
from zope.interface import implements

from canonical.launchpad.webapp import LaunchpadView
from lp.app.browser.tales import IMainTemplateFile
from lp.registry.interfaces.distribution import IDistributionSet
from lp.vostok.publisher import VostokLayer


class VostokRootView(LaunchpadView):
    """The view for the Vostok root object."""

    page_title = 'Vostok'

    @property
    def distributions(self):
        """An iterable of all registered distributions."""
        return getUtility(IDistributionSet)


class VostokLayerToMainTemplateAdapter:
    adapts(VostokLayer)
    implements(IMainTemplateFile)

    def __init__(self, context):
        here = os.path.dirname(os.path.realpath(__file__))
        self.path = os.path.join(here, '../templates/main-template.pt')
