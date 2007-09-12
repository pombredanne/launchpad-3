# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Browser view for a sourcepackagerelease"""

__metaclass__ = type

__all__ = [
    'SourcePackageReleaseView',
    ]

import cgi
import re

from zope.component import getUtility

from canonical.launchpad.webapp import LaunchpadView, canonical_url
from canonical.launchpad.interfaces import IBugSet, NotFoundError


class SourcePackageReleaseView(LaunchpadView):

    def changelog(self):
        return self._linkify_changelog(
            self.context.changelog, self.context.name)

    def _linkify_changelog(self, changelog, sourcepkgnametxt):
        if changelog is None:
            return ''
        changelog = cgi.escape(changelog)

        # Linkify the package name.
        escaped_name = re.escape(sourcepkgnametxt)
        matches = re.findall(r'%s (\(([^)]+)\) (\w+));' % escaped_name,
            changelog)
        for match_text, version, distroseries in matches:
            # Rather ugly to construct this URL, but it avoids the need to
            # look up database objects for each matching line of text here.
            url = '../../../%s/+source/%s/%s' % (
                distroseries, sourcepkgnametxt, version)
            changelog = changelog.replace(match_text,
                '(<a href="%s">%s</a>) %s' % (url, version, distroseries))

        # Linkify bug numbers of the format "LP: #<number>"
        matches = re.findall(r'(LP: #(\d+))', changelog)
        bug_set = getUtility(IBugSet)
        for match_text, bug_id in matches:
            try:
                bug = bug_set.get(bug_id)
            except NotFoundError:
                pass
            else:
                bug_url = canonical_url(bug)
                changelog = changelog.replace(
                    match_text, '<a title="%s" href="%s">%s</a>' % (
                        bug.description, bug_url, match_text))

        return changelog


