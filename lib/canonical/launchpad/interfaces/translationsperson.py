# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'ITranslationsPerson',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Bool

from canonical.launchpad import _


class ITranslationsPerson(Interface):
    """Translation-related properties of a person."""

    translatable_languages = Attribute(
        _('Languages this person knows, apart from English'))

    translation_history = Attribute(
        "The set of POFileTranslator objects that represent work done "
        "by this translator.")

    translation_groups = Attribute(
        "The set of TranslationGroup objects this person is a member of.")

    translators = Attribute(
        "The set of Translator objects this person is a member of.")

    translations_relicensing_agreement = Bool(
        title=_("Whether person agrees to relicense their translations"),
        readonly=False)
