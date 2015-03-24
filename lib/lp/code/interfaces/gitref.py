# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git reference ("ref") interfaces."""

__metaclass__ = type

__all__ = [
    'IGitRef',
    'IGitRefBatchNavigator',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Text,
    TextLine,
    )

from lp import _
from lp.code.enums import GitObjectType
from lp.services.webapp.interfaces import ITableBatchNavigator


class IGitRef(Interface):
    """A reference in a Git repository."""

    repository = Attribute("The Git repository containing this reference.")

    path = TextLine(
        title=_("Path"), required=True, readonly=True,
        description=_(
            "The full path of this reference, e.g. refs/heads/master."))

    commit_sha1 = TextLine(
        title=_("Commit SHA-1"), required=True, readonly=True,
        description=_(
            "The full SHA-1 object name of the commit object referenced by "
            "this reference."))

    object_type = Choice(
        title=_("Object type"), required=True, readonly=True,
        vocabulary=GitObjectType)

    author = Attribute(
        "The author of the commit pointed to by this reference.")
    author_date = Datetime(
        title=_("The author date of the commit pointed to by this reference."),
        required=False, readonly=True)

    committer = Attribute(
        "The committer of the commit pointed to by this reference.")
    committer_date = Datetime(
        title=_(
            "The committer date of the commit pointed to by this reference."),
        required=False, readonly=True)

    commit_message = Text(
        title=_(
            "The commit message of the commit pointed to by this reference."),
        required=False, readonly=True)

    display_name = TextLine(
        title=_("Display name"), required=True, readonly=True,
        description=_("Display name of the reference."))

    commit_message_first_line = TextLine(
        title=_("The first line of the commit message."),
        required=True, readonly=True)


class IGitRefBatchNavigator(ITableBatchNavigator):
    pass
