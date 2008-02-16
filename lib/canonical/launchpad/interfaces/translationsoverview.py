# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to bugs."""

__metaclass__ = type

__all__ = [
    'ITranslationsOverview',
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Bytes, Choice, Datetime, Int, List, Object, Text, TextLine)

from canonical.launchpad import _
from canonical.launchpad.fields import (
    ContentNameField, Title, DuplicateBug, Tag)
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.launchpad import NotFoundError
from canonical.launchpad.interfaces.messagetarget import IMessageTarget
from canonical.launchpad.interfaces.mentoringoffer import ICanBeMentored
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.validators.bugattachment import (
    bug_attachment_size_constraint)

class ITranslationsOverview(Interface):
    """Overview of Launchpad Translations component."""

    MINIMUM_SIZE = Int(
        title=_('Minimum relative weight for a product'),
        required=True, readonly=False)

    MAXIMUM_SIZE = Int(
        title=_('Maximum relative weight for a product'),
        required=True, readonly=False)

    def getMostTranslatedPillars(limit=50):
        """Get a list of products and distributions with most translations.

        :limit: A number of 'top' products to get.

        It returns a list of pairs (pillar, size), where `pillar` is
        either a product or a distribution, and size is the relative
        amount of contribution a pillar has received.
        """
