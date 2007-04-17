# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Browser view for a sourcepackagerelease"""

__metaclass__ = type

__all__ = [
    'SourcePackageReleaseView',
    ]

# Python standard library imports
import cgi
import re

# Canonical imports
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.browser import linkify_changelog


class SourcePackageReleaseView(LaunchpadView):

    def changelog(self):
        return linkify_changelog(
            self.context.changelog, self.context.name)
