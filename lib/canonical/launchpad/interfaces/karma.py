# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Int, Datetime
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__all__ = ['IKarma']

class IKarma(Interface):
    """The Karma of a Person"""
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True, readonly=True)
    points = Int(title=_("Key type"), required=True)
    karmafield = Int(title=_("Type of this Karma"), required=True)
    datecreated = Datetime(title=_("Date Created"), required=True,
                           readonly=True)

