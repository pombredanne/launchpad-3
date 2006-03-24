# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Support contact interfaces."""

__metaclass__ = type

__all__ = [
    'ISupportContact',
    ]


from zope.interface import Interface, Attribute
from zope.schema import Choice

from canonical.launchpad import _


class ISupportContact(Interface):
    """A support contact."""

    person = Choice(title=_('Support Contact'), required=False,
        description=_(
            "The person getting automatically subscribed to new support"
            " request."),
        vocabulary='ValidPersonOrTeam')
    product = Choice(title=_('Product'), required=False,
        description=_(
            "The person want to get automatically subscribed to this"
            " product's support request."),
        vocabulary='Product')

    distribution = Choice(title=_('Distribution'), required=False,
        description=_(
            "The person want to get automatically subscribed to this"
            " distribution's support request."),
        vocabulary='Distribution')

    sourcepackagename = Choice(title=_('Source Package'), required=False,
        description=_(
            "The person want to get automatically subscribed to this"
            " source package's support request."),
        vocabulary='SourcePackageName')
