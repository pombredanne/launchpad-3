# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Interfaces for Script activity records"""

__metaclass__ = type

__all__ = [
    'IScriptActivity',
    'IScriptActivitySet',
    ]

from zope.component import getUtility
from zope.interface import Interface
from zope.schema import Datetime, TextLine

from canonical.launchpad import _


class IScriptActivity(Interface):
    """A record of an invocation of a script."""

    name = TextLine(
        title=_('Script name'), required=True,
        description=_('The name of the script that was run'))
    hostname = TextLine(
        title=_('Host name'), required=True,
        description=_('The host on which the script was run'))
    date_started = Datetime(
        title=_('Date started'), required=True,
        description=_('The date at which the script started'))
    date_completed = Datetime(
        title=_('Date completed'), required=True,
        description=_('The date at which the script completed'))


class IScriptActivitySet(Interface):

    def recordSuccess(name, date_started, date_completed):
        """Record a successful script run."""

    def getLastActivity(name):
        """Get the last activity record for the given script name."""
