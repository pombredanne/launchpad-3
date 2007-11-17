# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for information on which languages are spoken in which
countries..
"""

__metaclass__ = type

__all__ = ['ISpokenIn']

from canonical.launchpad import _

from zope.interface import Interface
from zope.schema import Int


class ISpokenIn(Interface):
    """The SPokenIn description."""

    id = Int(
            title=_('SpokenInID'), required=True, readonly=True,
            )

    country = Int(title=_('Country'), required=True, readonly=True)

    language = Int(title=_('Language'), required=True, readonly=True)

