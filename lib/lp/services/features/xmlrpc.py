# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'IFeatureFlagApplication',
    'FeatureFlagApplication',
    ]

from zope.interface import implements

from canonical.launchpad.webapp.interfaces import ILaunchpadApplication
from lp.services.features.flags import FeatureController
from lp.services.features.rulesource import StormFeatureRuleSource
from lp.services.features.scopes import DefaultScope


class IFeatureFlagApplication(ILaunchpadApplication):
    """Mailing lists application root."""

    def getFeatureFlag(flag_name):
        """ XXX """

class FeatureFlagApplication:

    implements(IFeatureFlagApplication)

    def getFeatureFlag(self, flag_name):
        controller = FeatureController(
            DefaultScope().lookup, StormFeatureRuleSource())
        return controller.getFlag(flag_name)
