# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Custom language code."""

__metaclass__ = type

__all__ = [
    'ICustomLanguageCode',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Int, TextLine

from canonical.launchpad import _


class ICustomLanguageCode(Interface):
    """`CustomLanguageCode` interface."""

    id = Int(title=_(u"ID"), required=True, readonly=True)
    product = Attribute(_(u"Product"))
    distribution = Attribute(_(u"Distribution"))
    sourcepackagename = Attribute(_(u"Source package name"))
    language_code = TextLine(title=_(u"Language code"), required=True,
        description=_("Language code to treat as special."))
    language = Attribute(_(u"Language"))

