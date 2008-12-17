# Copyright 2005-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__metaclass__ = type

__all__ = ['ITranslator', 'ITranslatorSet']

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice, URIField

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
        "in which the translation team (individual supervisor) is being "
        "appointed."))
    language = Choice(title=_('Language'), required=True,
        vocabulary='Language', description=_("The language that this "
        "team or person will be responsible for."))
    translator = PublicPersonChoice(
        title=_('Translator'), required=True,
        vocabulary='ValidPersonOrTeam',
        description=_("The translation team (or individual supervisor) to "
            "be responsible for the language in this group."))
    documentation_url = URIField(
        title=_('Documentation URL'), required=False,
        allowed_schemes=['http', 'https', 'ftp'],
        allow_userinfo=False,
        description=_("URL with documentation for translation work done "
                      "here: process, vocabulary standards, caveats. "
                      "Please include the http://."))


class ITranslatorSet(IAddFormCustomization):
    """A container for `ITranslator`s."""

    title = Attribute('Title')

    def new(translationgroup, language, translator, documentation_url):
        """Create a new `ITranslator` for a `TranslationGroup`."""

