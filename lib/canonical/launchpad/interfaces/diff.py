# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to IDiff."""

__metaclass__ = type

__all__ = [
    'IDiff',
    'IStaticDiffReference'
    ]

from zope.schema import (
    Object, Choice, Int, Text, TextLine)
from zope.interface import (
    Interface, Attribute)

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias


class IDiff(Interface):
    """A diff that is stored in the Library."""

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


class IStaticDiffJob(Interface):
    """A job to create a static diff."""
