# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Browser view for a sourcepackagerelease"""

__metaclass__ = type

__all__ = [
    'SourcePackageReleaseView',
    ]

import cgi
import re

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.tales import FormattersAPI


class SourcePackageReleaseView(LaunchpadView):

    @property
    def changelog(self):
        """Return a linkified changelog."""
        return self._linkify_changelog(self.context.changelog)

    @property
    def change_summary(self):
        """Return a linkified change summary."""
        return self._linkify_changelog(self.context.change_summary)

    def _obfuscate_email(self, text):
        """Obfuscate email addresses if the user is not logged in."""
        if not text:
            # If there is nothing to obfuscate, the FormattersAPI
            # will blow up, so just return.
            return text
        formatter = FormattersAPI(text)
        if self.user:
            return text
        else:
            return formatter.obfuscate_email()

    def _linkify_email(self, text):
        """Email addresses are linkified to point to the person's profile."""
        formatter = FormattersAPI(text)
        return formatter.linkify_email()

    def _linkify_bug_numbers(self, changelog):
        """Linkify to a bug if LP: #number appears in the changelog text."""
        # FormattersAPI._linkify_substitution requires a match object
        # that has named groups "bug" and "bugnum".  The matching text for
        # the "bug" group is used as the link text and "bugnum" forms part
        # of the URL for the link to the bug.
        matches = re.finditer('(?P<bug>LP:\s*#(?P<bugnum>\d+))?', changelog)
        for match in matches:
            replace_text = match.group('bug')
            if replace_text is not None:
                changelog = changelog.replace(
                    replace_text, FormattersAPI._linkify_substitution(match))
        return changelog

    def _linkify_changelog(self, changelog):
        """Linkify the changelog.

        This obfuscates email addresses to anonymous users, linkifies
        them for non-anonymous and links to the bug page for any bug
        numbers mentioned.
        """
        if changelog is None:
            return ''

        # Remove any email addresses if the user is not logged in.
        changelog = self._obfuscate_email(changelog)

        # CGI Escape the changelog here before further replacements
        # insert HTML. Email obfuscation does not insert HTML but can insert
        # characters that must be escaped.
        changelog = cgi.escape(changelog)

        # Any email addresses remaining in the changelog were not obfuscated,
        # so we linkify them here.
        changelog = self._linkify_email(changelog)

        # Ensure any bug numbers are linkified to the bug page.
        changelog = self._linkify_bug_numbers(changelog)

        return changelog

