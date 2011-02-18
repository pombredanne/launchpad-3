# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for source package builds."""

__metaclass__ = type

__all__ = [
    'SourcePackageChangelogView',
    'SourcePackageCopyrightView',
    ]

from canonical.lazr.utils import smartquote


class SourcePackageChangelogView:
    """View class for source package change logs."""

    page_title = "Change log"

    @property
    def label(self):
        """<h1> for the change log page."""
        return smartquote("Change logs for " + self.context.title)


class SourcePackageCopyrightView:
    """A view to display a source package's copyright information."""

    page_title = "Copyright"

    @property
    def label(self):
        """Page heading."""
        return smartquote("Copyright for " + self.context.title)
