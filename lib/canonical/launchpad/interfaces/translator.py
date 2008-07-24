# Copyright 2005-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__metaclass__ = type

__all__ = ['ITranslator', 'ITranslatorSet']

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice

from zope.interface import Interface, Attribute

from zope.schema import Choice, Datetime, Int
from zope.app.form.browser.interfaces import IAddFormCustomization


class ITranslator(Interface):
    """A member of a `TranslationGroup`.
    
    This is not the same thing as what is called a translator in the UI.
    An `ITranslator` represents a person or team appointed within a
    translation group to be responsible for a language.  On the other
    hand, any logged-in Launchpad user can act as a translator by
    suggesting or entering translations.
    """

    id = Int(
            title=_('Translator ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Appointed'), required=True, readonly=True,
            )
    translationgroup = Choice(title=_('Translation Group'), required=True,
        vocabulary='TranslationGroup', description=_("The translation group "
        "in which the translation team or reviewer is being appointed."))
    language = Choice(title=_('Language'), required=True,
        vocabulary='Language', description=_("The language that this "
        "team or reviewer will be responsible for."))
    translator = PublicPersonChoice(
        title=_('Translator'), required=True,
        vocabulary='ValidPersonOrTeam',
        description=_("The translation team or individual reviewer who will "
            "be responsible for the language in this group."))


class ITranslatorSet(IAddFormCustomization):
    """A container for translators."""

    title = Attribute('Title')

    def new(translationgroup, language, translator):
        """Create a new translator for a group."""

