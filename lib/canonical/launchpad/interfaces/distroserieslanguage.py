# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.interface import Interface, Attribute

from canonical.launchpad.interfaces.rosettastats import IRosettaStats

__metaclass__ = type

__all__ = [
    'IDistroSeriesLanguage',
    'IDistroSeriesLanguageSet',
    ]

class IDistroSeriesLanguage(IRosettaStats):
    """A placeholder for the statistics in the translation of a
    distroseries into a language, for example, Ubuntu Hoary into French.
    This exists to cache stats, and be a useful object for traversal in
    Rosetta."""

    id = Attribute("A unique ID")

    language = Attribute("The language.")

    distroseries = Attribute("The distro series which has been "
        "translated.")

    dateupdated = Attribute("The date these statistics were last updated.")

    title = Attribute("The title.")

    pofiles = Attribute("The set of pofiles in this distroseries for this "
        "language. This includes only the real pofiles where translations "
        "exist.")

    po_files_or_dummies = Attribute(
        "Return a full complement of po files and dummy pofiles, one for "
        "each PO Template in the series.")

    translator_count = Attribute("The number of registered translators "
        "for this language in the distribution.")

    contributor_count = Attribute("The number of contributors in total "
        "for this language in the distribution.")


class IDistroSeriesLanguageSet(Interface):
    """The set of distroserieslanguages."""

    def getDummy(distroseries, language):
        """Return a new DummyDistroSeriesLanguage for the given
        distroseries and language.
        """

