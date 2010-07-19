# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0213

from lazr.restful.fields import Reference

from zope.interface import Attribute, Interface
from zope.schema import (
    Choice, Datetime, TextLine)

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


    last_changed_date = Datetime(
        title=_('When this file was last changed.'))


    def getPOFilesFor(potemplates):
        """Return `POFiles` for each of `potemplates`, in the same order.

        For any `POTemplate` that does not have a translation to the
        required language, a `DummyPOFile` is provided.
        """

    def setCounts(total, imported, changed, new, unreviewed, last_changed):
        """Set aggregated message counts for ProductSeriesLanguage."""

    def recalculateCounts(total, imported, changed, new, unreviewed):
        """Recalculate message counts for this ProductSeriesLanguage."""


class IProductSeriesLanguageSet(Interface):
    """The set of productserieslanguages."""

    def getProductSeriesLanguage(productseries, language, variant=None,
                                 pofile=None):
        """Return a PSL for a productseries and a language."""
