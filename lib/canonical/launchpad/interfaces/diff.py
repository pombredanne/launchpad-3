# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to IDiff."""

__metaclass__ = type

__all__ = [
    'IDiff',
    'IStaticDiff',
    'IStaticDiffSource',
    ]

from zope.schema import Object, Int, Text, TextLine
from zope.interface import Interface

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias


class IDiff(Interface):
    """A diff that is stored in the Library."""

    text = Text(title=_('Textual contents of a diff.'))

    diff_text = Object(
        title=_('Content of this diff'), required=True,
        schema=ILibraryFileAlias)

    diff_lines_count = Int(
        title=_('The number of lines in this diff.'))

    diffstat = Text(title=_('Statistics about this diff'))

    added_lines_count = Int(
        title=_('The number of lines added in this diff.'))

    removed_lines_count = Int(
        title=_('The number of lines removed in this diff.'))


class IStaticDiff(Interface):
    """A diff with a fixed value, i.e. between two revisions."""

    from_revision_id = TextLine()

    to_revision_id = TextLine()

    diff = Object(title=_('The Diff object.'), schema=IDiff)

    def destroySelf():
        """Destroy this object."""


class IStaticDiffSource(Interface):
    """Component that can acquire StaticDiffs."""

    def acquire(from_revision_id, to_revision_id, repository):
        """Get or create a StaticDiff."""

    def acquireFromText(from_revision_id, to_revision_id, text):
        """Get or create a StaticDiff from a string.

        If a StaticDiff exists for this revision_id pair, the text is ignored.
        """
