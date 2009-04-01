# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces including and related to IDiff."""

__metaclass__ = type

__all__ = [
    'IDiff',
    'IPreviewDiff',
    'IStaticDiff',
    'IStaticDiffSource',
    ]

from zope.schema import Bool, Bytes, Int, Text, TextLine
from zope.interface import Interface

from lazr.restful.fields import Reference
from lazr.restful.declarations import (
    export_as_webservice_entry, exported)

from canonical.launchpad import _


class IDiff(Interface):
    """A diff that is stored in the Library."""

    text = Text(title=_('Textual contents of a diff.'), readonly=True)

    diff_text = exported(
        Bytes(title=_('Content of this diff'), required=True, readonly=True))

    diff_lines_count = exported(
        Int(title=_('The number of lines in this diff.'), readonly=True))

    diffstat = exported(
        Text(title=_('Statistics about this diff'), readonly=True))

    added_lines_count = exported(
        Int(title=_('The number of lines added in this diff.'),
            readonly=True))

    removed_lines_count = exported(
        Int(title=_('The number of lines removed in this diff.'),
            readonly=True))


class IStaticDiff(Interface):
    """A diff with a fixed value, i.e. between two revisions."""

    from_revision_id = exported(TextLine(readonly=True))

    to_revision_id = exported(TextLine(readonly=True))

    diff = exported(
        Reference(IDiff, title=_('The Diff object.'), readonly=True))

    def destroySelf():
        """Destroy this object."""


class IStaticDiffSource(Interface):
    """Component that can acquire StaticDiffs."""

    def acquire(from_revision_id, to_revision_id, repository, filename=None):
        """Get or create a StaticDiff."""

    def acquireFromText(from_revision_id, to_revision_id, text,
                        filename=None):
        """Get or create a StaticDiff from a string.

        If a StaticDiff exists for this revision_id pair, the text is ignored.
        """


class IPreviewDiff(IDiff):
    """A diff generated to show actual diff between two branches.

    This diff will be used primarily for branch merge proposals where we are
    trying to determine the effective changes of landing the source branch on
    the target branch.
    """
    export_as_webservice_entry()

    source_revision_id = exported(
        TextLine(
            title=_('The tip revision id of the source branch used to '
                    'generate the diff.'),
            readonly=True))

    target_revision_id = exported(
        TextLine(
            title=_('The tip revision id of the target branch used to '
                    'generate the diff.'),
            readonly=True))

    dependent_revision_id = exported(
        TextLine(
            title=_('The tip revision id of the dependent branch used to '
                    'generate the diff.'),
            readonly=True))

    conflicts = exported(
        Text(title=_(
                'The conflicts text describing any path or text conflicts.'),
             readonly=True))

    # The schema for the Reference gets patched in _schema_circular_imports.
    branch_merge_proposal = exported(
        Reference(
            Interface, readonly=True,
            title=_('The branch merge proposal that diff relates to.')))

    stale = exported(
        Bool(readonly=True, description=_(
                'If the preview diff is stale, it is out of date when '
                'compared to the tip revisions of the source, target, and '
                'possibly dependent branches.')))
