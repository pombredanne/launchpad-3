# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

from lazr.restful.fields import Reference

from zope.interface import Attribute, Interface
from zope.schema import (
    Choice, TextLine)

from canonical.launchpad import _
from lp.translations.interfaces.pofile import IPOFile
from lp.translations.interfaces.rosettastats import IRosettaStats

__metaclass__ = type

__all__ = [
    'IProductSeriesLanguage',
    'IProductSeriesLanguageSet',
    ]

class IProductSeriesLanguage(IRosettaStats):
    """Per-language statistics for a product series."""

    language = Choice(
        title=_('Language to gather statistics for.'),
        vocabulary='Language', required=True, readonly=True)

    pofile = Reference(
        title=_("A POFile if there is only one POTemplate for the series."),
        schema=IPOFile, required=False, readonly=True)

    productseries = Choice(
        title=_("Series"),
        required=False,
        vocabulary="ProductSeries")

    title = TextLine(
        title=_("Title for the per-language per-series page."),
        required=False)

    pofiles = Attribute("The set of pofiles in this distroseries for this "
        "language. This includes only the real pofiles where translations "
        "exist.")

    pofiles_or_dummies = Attribute(
        "Return a full complement of po files and dummy pofiles, one for "
        "each PO Template in the series.")


class IProductSeriesLanguageSet(Interface):
    """The set of productserieslanguages."""

    def getDummy(productseries, language, variant=None):
        """Return a new DummyProductSeriesLanguage for the given
        productseries and language.
        """

    def getProductSeriesLanguage(productseries, language, variant=None):
        """Return a PSL for a productseries and a language."""
