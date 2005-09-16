# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for builds."""

__metaclass__ = type
__all__ = ['BuiltItemUrl']

import zope.security.interfaces
from zope.component import getUtility

from canonical.lp import dbschema

from canonical.launchpad.interfaces import (
    IPerson, IBuilderSet, IBuilder
    )


class BuildView:
    __used_for__ = IBuild

    def BuiltItemUrl(self):
        """Return the URL of the thing being built."""
        url = '/distros/'
        url += self.distrorelease
        return url
