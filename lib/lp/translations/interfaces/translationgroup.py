# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces for groups of translators."""

__metaclass__ = type

__all__ = [
    'ITranslationPolicy',
    'ITranslationGroup',
    'ITranslationGroupSet',
    'TranslationPermission',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Int,
    TextLine,
    )

from canonical.launchpad import _
from canonical.launchpad.validators.name import name_validator
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import (
    PublicPersonChoice,
    Summary,
    Title,
    URIField,
    )


class TranslationPermission(DBEnumeratedType):
    """Translation Permission System

    Projects groups, products and distributions can all have content that
    needs to be translated. In this case, Launchpad Translations allows them
    to decide how open they want that translation process to be. At one
    extreme, anybody can add or edit any translation, without review. At the
    other, only the designated translator for that group in that language can
    add or edit its translation files. This schema enumerates the options.
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


class ITranslationPolicy(Interface):
    translationgroup = Choice(
        title = _("Translation group"),
        description = _("The translation group that helps review "
            " translations for this project or distribution. The group's "
            " role depends on the permissions policy selected below."),
        required=False,
        vocabulary='TranslationGroup')

    translationpermission = Choice(
        title=_("Translation permissions policy"),
        description=_("The policy this project or distribution uses to "
            " balance openness and control for their translations."),
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

    # adding and removing translators
    def remove_translator(language):
        """Remove the translator for this language from the group."""

    # used for the form machinery
    def add(content):
        """Add a new object."""

    top_projects = Attribute(
        "Most relevant projects using this translation group.")

    number_of_remaining_projects = Attribute(
        "Count of remaining projects not listed in the `top_projects`.")

    def __getitem__(language_code):
        """Retrieve the translator for the given language in this group.

        This is used for navigation through the group.
        """

    def fetchTranslatorData():
        """Fetch translators and related data.

        Prefetches display-related properties.

        :return: A result set of (`Translator`, `Language`, `Person`),
            ordered by language name in English.
        """

    def fetchProjectsForDisplay():
        """Fetch `Product`s using this group, for display purposes.

        Prefetches display-related properties.

        :return: A result set of `Product`, ordered by display name.
        """

    def fetchProjectGroupsForDisplay():
        """Fetch `Project`s using this group, for display purposes.

        Prefetches display-related properties.

        :return: A result set of `Project`, ordered by display name.
        """

    def fetchDistrosForDisplay():
        """Fetch `Distribution`s using this group, for display purposes.

        Prefetches display-related properties.

        :return: A result set of `Distribution`, ordered by display name.
        """


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
