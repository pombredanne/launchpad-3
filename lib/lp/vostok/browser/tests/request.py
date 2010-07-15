# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A VostokLayer request class for use in tests."""

__metaclass__ = type
__all__ = [
    'VostokTestRequest',
    ]

from zope.interface import implements

from canonical.launchpad.webapp.servers import LaunchpadTestRequest

from lp.vostok.publisher import VostokLayer


class VostokTestRequest(LaunchpadTestRequest):
    implements(VostokLayer)
