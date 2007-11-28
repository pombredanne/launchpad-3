# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Revision interfaces."""

__metaclass__ = type
__all__ = [
    'IRevision', 'IRevisionAuthor', 'IRevisionParent', 'IRevisionProperty',
    'IRevisionSet']

from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, Choice, Text, TextLine

from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad import _


class IRevision(IHasOwner):
    """Bazaar revision."""

    id = Int(title=_('The database revision ID'))

    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)
    log_body = Attribute("The revision log message.")
    revision_author = Attribute("The revision author identifier.")
    gpgkey = Attribute("The OpenPGP key used to sign the revision.")
    revision_id = Attribute("The globally unique revision identifier.")
    revision_date = Datetime(
        title=_("The date the revision was committed."),
        required=True, readonly=True)
    parents = Attribute("The RevisionParents for this revision.")
    parent_ids = Attribute("The revision_ids of the parent Revisions.")
    properties = Attribute("The `RevisionProperty`s for this revision.")

    def getProperties():
        """Return the revision properties as a dict."""


class IRevisionAuthor(Interface):
    """Committer of a Bazaar revision."""

    name = TextLine(title=_("Revision Author Name"), required=True)
    name_without_email = Attribute("Revision author name without email address")


class IRevisionParent(Interface):
    """The association between a revision and its parent revisions."""

    revision = Attribute("The child revision.")
    sequence = Attribute("The order of the parent of that revision.")
    parent_id = Attribute("The revision_id of the parent revision.")


class IRevisionProperty(Interface):
    """A property on a Bazaar revision."""

    revision = Attribute("The revision which has this property.")
    name = TextLine(title=_("The name of the property."), required=True)
    value = Text(title=_("The value of the property."), required=True)


class IRevisionSet(Interface):
    """The set of all revisions."""

    def getByRevisionId(revision_id):
        """Find a revision by revision_id. None if the revision is not known.
        """

    def new(revision_id, log_body, revision_date, revision_author, owner,
            parent_ids, properties):
        """Create a new Revision with the given revision ID."""
