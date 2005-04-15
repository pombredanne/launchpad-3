# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface

__metaclass__ = type

__all__ = ('IRosettaStats', )

class IRosettaStats(Interface):
    """Rosetta-related statistics."""

    def messageCount():
        """Returns the number of Current IPOMessageSets in all templates
        inside this object."""

    def currentCount(language=None):
        """Returns the number of msgsets matched to a potemplate for this
        object that have a non-fuzzy translation in its PO file for this
        language when we last parsed it."""

    def currentPercentage(language=None):
        """Returns the percentage of current msgsets inside this object."""

    def updatesCount(language=None):
        """Returns the number of msgsets for this object where we have a
        newer translation in rosetta than the one in the PO file for this
        language, when we last parsed it."""

    def updatesPercentage(language=None):
        """Returns the percentage of updated msgsets inside this object."""

    def rosettaCount(language=None):
        """Returns the number of msgsets where we have a translation in rosetta
        but there was no translation in the PO file for this language when we
        last parsed it."""

    def rosettaPercentage(language=None):
        """Returns the percentage of msgsets translated with Rosetta inside
        this object."""

    def translatedCount(language=None):
        """Returns the number of msgsets that are translated."""

    def translatedPercentage(language=None):
        """Returns the percentage of msgsets translated for this object."""

    def untranslatedCount(language=None):
        """Returns the number of msgsets that are untranslated."""

    def untranslatedPercentage(language=None):
        """Returns the percentage of msgsets untranslated for this object."""

    def nonUpdatesCount(language=None):
        """Returns the number of msgsets that are translated and don't have an
        update from Rosetta."""

    def nonUpdatesPercentage(language=None):
        """Returns the percentage of msgsets for this object that are 
        translated and don't have an update from Rosetta."""
