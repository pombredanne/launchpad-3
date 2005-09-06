# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Revision interfaces."""

__metaclass__ = type
__all__ = ['IRevision', 'IRevisionAuthor']

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, Choice, Text, TextLine, Float

from canonical.launchpad.interfaces import IHasOwner


_ = MessageIDFactory('launchpad')


class IRevision(IHasOwner):
    """Bazaar revision."""

    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    branch = Attribute("The branch this revision belongs to.")
    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)
    log_body = Attribute("The revision log message.")
    revision_author = Attribute("The revision author string.")
    gpgkey = Attribute("The GPG key used to sign the revision.")
    revision_id = Attribute("The unique revision identifier.")
    revision_date = Datetime(
        title=_("The date the revision was committed."),
        required=True, readonly=True)
    diff_adds = Attribute("Number of lines added by the revision.")
    diff_deletes = Attribute("Number of lines removed by the revision.")


class IRevisionAuthor(Interface):
    """Bazaar revision author """

    # FIXME: The sole purpose of this table is apparently to improve the
    # database normalisation. Therefore the name column should be UNIQUE.
    # -- David Allouche 2005-09-06

    # id = Int(title=_("RevisionAuthor ID"), required=True, readonly=True)
    name = TextLine(title=_("Revision Author Name"), required=True)
