# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for information on which languages are spoken in which
countries..
"""

__metaclass__ = type

__all__ = ['ISpokenIn']

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface
from zope.schema import Int


class ISpokenIn(Interface):
    """The SPokenIn description."""

    id = Int(
            title=_('SpokenInID'), required=True, readonly=True,
            )

    country = Int(title=_('Country'), required=True, readonly=True)

    language = Int(title=_('Language'), required=True, readonly=True)

