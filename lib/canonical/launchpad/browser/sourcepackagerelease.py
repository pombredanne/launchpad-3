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


def linkify_changelog(changelog, sourcepkgnametxt):
    if changelog is None:
        return changelog
    changelog = cgi.escape(changelog)
    # XXX cprov 20060207: use re.match and fmt:url instead of this nasty
    # url builder. Also we need an specification describing the syntax for
    # changelog linkification and processing (mostly bug interface),
    # bug # 30817
    changelog = re.sub(r'%s \(([^)]+)\)' % re.escape(sourcepkgnametxt),
                       r'%s (<a href="\1">\1</a>)' % sourcepkgnametxt,
                       changelog)
    return changelog


class SourcePackageReleaseView(LaunchpadView):

    def changelog(self):
        return linkify_changelog(
            self.context.changelog, self.context.name)
