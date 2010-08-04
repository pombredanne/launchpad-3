# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`TranslationSideTraits` implementations."""

__metaclass__ = type
__all__ = [
    'TranslationSideTraits',
    'TranslationSideTraitsSet',
    ]

from zope.interface import implements

from lp.translations.interfaces.side import (
    ITranslationSideTraits,
    ITranslationSideTraitsSet,
    TranslationSide)


class TranslationSideTraits:
    """See `ITranslationSideTraits`."""
    implements(ITranslationSideTraits)

    def __init__(self, side, flag_name):
        self.side = side
        self.other_side = None
        self.flag_name = flag_name

    def getFlag(self, translationmessage):
        """See `ITranslationSideTraits`."""
        return getattr(translationmessage, self.flag_name)

    def getCurrentMessage(self, potmsgset, potemplate, language):
        """See `ITranslationSideTraits`."""
        if self.side == TranslationSide.UPSTREAM:
            return potmsgset.getImportedTranslationMessage(
                potemplate, language)
        else:
            return potmsgset.getCurrentTranslationMessage(
                potemplate, language)

    def setFlag(self, translationmessage, value):
        """See `ITranslationSideTraits`."""
        if self.side == TranslationSide.UPSTREAM:
            translationmessage.makeCurrentUpstream(value)
        else:
            translationmessage.makeCurrentUbuntu(value)


class TranslationSideTraitsSet:
    """See `ITranslationSideTraitsSet`."""
    implements(ITranslationSideTraitsSet)

    def __init__(self):
        upstream = TranslationSideTraits(
            TranslationSide.UPSTREAM, 'is_current_upstream')
        ubuntu = TranslationSideTraits(
            TranslationSide.UBUNTU, 'is_current_ubuntu')
        ubuntu.other_side = upstream
        upstream.other_side = ubuntu
        self.traits = dict(
            (traits.side, traits)
            for traits in [ubuntu, upstream])

    def getTraits(self, side):
        """See `ITranslationSideTraitsSet`."""
        return self.traits[side]

    def getForTemplate(self, potemplate):
        """See `ITranslationSideTraitsSet`."""
        if potemplate.productseries is not None:
            side = TranslationSide.UPSTREAM
        else:
            side = TranslationSide.UBUNTU
        return self.getTraits(side)

    def getAllTraits(self):
        """See `ITranslationSideTraitsSet`."""
        return self.traits
