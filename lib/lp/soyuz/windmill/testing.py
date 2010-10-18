# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Soyuz-specific testing infrastructure for Windmill."""

__metaclass__ = type
__all__ = [
    'SoyuzWindmillLayer',
    ]


from canonical.testing.layers import BaseWindmillLayer


class SoyuzWindmillLayer(BaseWindmillLayer):
    """Layer for Soyuz Windmill tests."""

    from canonical.testing import getRootLaunchpadUrl
    base_url = getRootLaunchpadUrl()
