# Copyright 2008-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Custom language code."""

__metaclass__ = type

__all__ = [
    'ICustomLanguageCode',
    'IHasCustomLanguageCodes',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int, Object, Set, TextLine

from canonical.launchpad import _

from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.sourcepackagename import ISourcePackageName


class ICustomLanguageCode(Interface):
    """`CustomLanguageCode` interface."""

    id = Int(title=_("ID"), required=True, readonly=True)
    product = Object(
        title=_("Product"), required=False, readonly=True, schema=IProduct)
    distribution = Object(
        title=_("Distribution"), required=False, readonly=True,
        schema=IDistribution)
    sourcepackagename = Object(
        title=_("Source package name"), required=False, readonly=True,
        schema=ISourcePackageName)
    language_code = TextLine(title=_("Language code"),
        description=_("Language code to treat as special."),
        required=True, readonly=False)
    language = Choice(
        title=_("Language"), required=False, readonly=False,
        vocabulary='Language',
        description=_("Language to map this code to.  "
            "Leave empty to drop translations for this code."))


class IHasCustomLanguageCodes(Interface):
    """A context that can have custom language codes attached.

    Implemented by `Product` and `SourcePackage`.
    """
    custom_language_codes = Set(
        title=_("Custom language codes"),
        description=_("Translations for these language codes are re-routed."),
        value_type=Object(schema=ICustomLanguageCode),
        required=False, readonly=False)

    def getCustomLanguageCode(language_code):
        """Retrieve `CustomLanguageCode` for `language_code`.

        :return: a `CustomLanguageCode`, or None.
        """

    def createCustomLanguageCode(language_code, language):
        """Create `CustomLanguageCode`.

        :return: the new `CustomLanguageCode` object.
        """
