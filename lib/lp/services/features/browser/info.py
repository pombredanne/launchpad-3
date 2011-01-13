# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View and edit feature rules."""

__metaclass__ = type
__all__ = [
    'FeatureInfoView',
    ]


from collections import namedtuple

from canonical.launchpad.webapp.publisher import LaunchpadView
from lp.services.features.flags import (
    flag_info,
    undocumented_flags,
    )


# A type of named tuple to use when passing data to the template.
Info = namedtuple('Info', ('name', 'domain', 'description', 'default'))


class FeatureInfoView(LaunchpadView):
    """Display feature flag documentation and other info."""

    page_title = label = 'Feature flag info'

    @property
    def flag_info(self):
        """A list of flags as named tuples, ready to be rendered."""
        return map(Info._make, flag_info)

    @property
    def undocumented_flags(self):
        """Flag names referenced during process lifetime but not documented.
        """
        return ', '.join(undocumented_flags)
