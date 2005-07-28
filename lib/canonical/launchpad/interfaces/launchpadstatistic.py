# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Launchpad statistic storage interfaces."""

__metaclass__ = type

__all__ = ['ILaunchpadStatistic', 'ILaunchpadStatisticSet']

from zope.interface import Interface
from zope.schema import Int, TextLine
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ILaunchpadStatistic(Interface):
    """A single stored statistic or value in the Launchpad system.
    
    Each statistic is a name/value pair. Names are text, unique, and values
    are integers.
    """

    name = TextLine(title=_('Field Name'), required=True, readonly=True)
    value = Int(title=_('Value'), required=True, readonly=True)


class ILaunchpadStatisticSet(Interface):
    """The set of all ILaunchpadStatistics."""

    def update(name, value):
        """Update the field given in name to the value passed as value.
        Also, update the dateupdated to reflect the current datetime.
        """

    def dateupdated(name):
        """Return the date and time the given statistic name was last
        updated.
        """

    def value(name):
        """Return the current value of the requested statistic."""


