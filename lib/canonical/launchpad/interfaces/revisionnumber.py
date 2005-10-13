# Copyright 2005 Canonical Ltd.  All rights reserved.

"""RevisionNumber interfaces."""

__metaclass__ = type

__all__ = ['IRevisionNumber']

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Int


_ = MessageIDFactory('launchpad')


class IRevisionNumber(Interface):
    """The association between a revision and a branch."""

    rev_no = Int(
        title=_("Revision Number"), required=True,
        description=_("The index of a revision within a branch's history."))
    branch = Attribute("The branch this revision number belongs to.")
    revision = Attribute("The revision with that index in this branch.")
