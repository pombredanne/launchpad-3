# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Int, Datetime
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IKarma(Interface):
    """The Karma of a Person"""
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("The person which this karma is assigned to"),
                 required=True, readonly=True)
    points = Int(title=_("Number of points"), required=True)
    karmatype = Int(title=_("Type of this Karma"), required=True)
    datecreated = Datetime(title=_("Date Created"), required=True,
                           readonly=True)


class IKarmaPointsManager(Interface):
    """An utility which knows how much points to give for each karma type."""

    def getPoints(karmatype):
        """Return the number of points for this karmatype.

        Raise KeyError if the karma type is not matched.
        """

    def queryPoints(karmatype, default=None):
        """Return the number of points for this karmatype.

        Return the default value if the karma type is not matched.
        """

