# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces for information on which languages are spoken in which
countries..
"""

__metaclass__ = type

__all__ = ['ISpokenIn']

from zope.interface import Interface
from zope.schema import Int

from canonical.launchpad import _


class ISpokenIn(Interface):
    """The SpokenIn description."""

    id = Int(
            title=_('SpokenInID'), required=True, readonly=True,
            )

    country = Int(title=_('Country'), required=True, readonly=True)

    language = Int(title=_('Language'), required=True, readonly=True)

