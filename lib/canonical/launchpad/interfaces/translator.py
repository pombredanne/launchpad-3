# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__metaclass__ = type

__all__ = ['ITranslator', 'ITranslatorSet']

from canonical.launchpad import _

from zope.interface import Interface, Attribute

from zope.schema import Choice, Datetime, Int
from zope.app.form.browser.interfaces import IAddFormCustomization


class ITranslator(Interface):
    """A Translator in a TranslationGroup."""

    id = Int(
            title=_('Translator ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    translationgroup = Choice(title=_('Translation Group'), required=True,
        vocabulary='TranslationGroup', description=_("The translation group "
        "in which the translator is being appointed."))
    language = Choice(title=_('Language'), required=True,
        vocabulary='Language', description=_("The language of the "
        "translator."))
    translator = Choice(title=_('Translator'), required=True,
        vocabulary='ValidPersonOrTeam',
        description=_("The translator who will be responsible for the "
                      "language in this group."))


class ITranslatorSet(IAddFormCustomization):
    """A container for translators."""

    title = Attribute('Title')

    def new(translationgroup, language, translator):
        """Create a new translator for a group."""

