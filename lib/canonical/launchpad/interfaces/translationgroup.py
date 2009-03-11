# Copyright 2005-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for groups of translators."""

__metaclass__ = type

__all__ = [
    'IHasTranslationGroup',
    'ITranslationGroup',
    'ITranslationGroupSet',
    'TranslationPermission',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Int, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import (
    PublicPersonChoice, Summary, Title, URIField)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces.launchpad import IHasOwner
from lazr.enum import DBEnumeratedType, DBItem


class TranslationPermission(DBEnumeratedType):
    """Translation Permission System

    Projects, products and distributions can all have content that needs to
    be translated. In this case, Launchpad Translations allows them to decide
    how open they want that translation process to be. At one extreme, anybody
    can add or edit any translation, without review. At the other, only the
    designated translator for that group in that language can add or edit its
    translation files. This schema enumerates the options.
    """

    OPEN = DBItem(1, """
        Open

        This group allows totally open access to its translations. Any
        logged-in user can add or edit translations in any language, without
        any review.""")

    STRUCTURED = DBItem(20, """
        Structured

        This group has designated translators for certain languages. In
        those languages, people who are not designated translators can only
        make suggestions. However, in languages which do not yet have a
        designated translator, anybody can edit the translations directly,
        with no further review.""")

    RESTRICTED = DBItem(100, """
        Restricted

        This group allows only designated translators to edit the
        translations of its files. You can become a designated translator
        either by joining an existing language translation team for this
        project, or by getting permission to start a new team for a new
        language. People who are not designated translators can still make
        suggestions for new translations, but those suggestions need to be
        reviewed before being accepted by the designated translator.""")

    CLOSED = DBItem(200, """
        Closed

        This group allows only designated translators to edit or add
        translations. You can become a designated translator either by
        joining an existing language translation team for this
        project, or by getting permission to start a new team for a new
        language. People who are not designated translators will not be able
        to add suggestions.""")


class IHasTranslationGroup(Interface):
    translationgroup = Choice(
        title = _("Translation group"),
        description = _("The translation group associated with this object."
            " This group is made up of a set of translators for all the"
            " languages approved by the group manager. These translators then"
            " have permission to edit the groups translation files, based on"
            " the permission system selected below."),
        required=False,
        vocabulary='TranslationGroup')

    translationpermission = Choice(
        title=_("Translation Permission System"),
        description=_("The permissions this group requires for translators.  "
            "If 'Open', anybody can edit translations in any language.  "
            "If 'Structured', members of the translation group can edit "
            "translations for their languages, and others can make "
            "suggestions; translations for which the translation group "
            "assigns no reviewer or translation team are completely open.  "
            "If 'Restricted', translation group members can edit "
            "translations and any user can make suggestions for those "
            "translations, but translations to languages that aren't "
            "covered by the translation group are closed and accept no "
            "suggestions.  Finally, if 'Closed', only translation group "
            "members can enter any translations at all."),
        required=True,
        vocabulary=TranslationPermission)


class ITranslationGroup(IHasOwner):
    """A TranslationGroup."""

    id = Int(
            title=_('Translation Group ID'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Name'), required=True,
            description=_("""Keep this name very short, unique, and
            descriptive, because it will be used in URLs. Examples:
            gnome-translation-project, ubuntu-translators."""),
            constraint=name_validator,
            )
    title = Title(
            title=_('Title'), required=True,
            description=_("""Title of this Translation Group.
            This title is displayed at the top of the Translation Group
            page and in lists or reports of translation groups.  Do not
            add "translation group" to this title, or it will be shown
            double.
            """),
            )
    summary = Summary(
            title=_('Summary'), required=True,
            description=_("""A single-paragraph description of the
            group. This will also be displayed in most
            translation group listings."""),
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    owner = PublicPersonChoice(
            title=_('Owner'), required=True, vocabulary='ValidOwner',
            description=_("The owner's IPerson"))
    # joins
    translators = Attribute('The set of translators for this group.')
    projects = Attribute('The projects for which this group translates.')
    products = Attribute('The projects to which this group is directly '
        'appointed as a translator. There may be other projects that are '
        'part of project groups for which the group also translates.')
    distributions = Attribute('The distros for which this group translates.')

    translation_guide_url = URIField(
        title=_('Translation instructions'), required=False,
        allowed_schemes=['http', 'https', 'ftp'],
        allow_userinfo=False,
        description=_("The URL of the generic translation instructions "
                      "followed by this particular translation group. "
                      "This should include team policies and "
                      "recommendations, specific instructions for "
                      "any non-standard behaviour and other documentation."
                      "Can be any of http://, https://, or ftp://."))

    # accessing the translator list
    def query_translator(language):
        """Retrieve a translator, or None, based on a Language"""

    def __getitem__(languagecode):
        """Retrieve the translator for the given language in this group."""

    # adding and removing translators
    def remove_translator(language):
        """Remove the translator for this language from the group."""

    # used for the form machinery
    def add(content):
        """Add a new object."""


class ITranslationGroupSet(Interface):
    """A container for translation groups."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get a translation group by name."""

    def __iter__():
        """Iterate through the translation groups in this set."""

    def new(name, title, summary, translation_guide_url, owner):
        """Create a new translation group."""

    def getByPerson(person):
        """Return the translation groups which that person is a member of."""

    def getGroupsCount():
        """Return the amount of translation groups available."""
