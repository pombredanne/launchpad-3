# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for groups of translators."""

__metaclass__ = type

__all__ = [
    'IHasTranslationGroup',
    'ITranslationGroup',
    'ITranslationGroupSet',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Int, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad import _
from canonical.launchpad.fields import Summary, Title
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces.launchpad import IHasOwner


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
        description=_("The permissions this group requires for translators."
            " If 'Open', then anybody can edit translations in any language."
            " If 'Structured', only designated translators are able to edit"
            " or confirm translations for those languages, other people can"
            " only add suggestions for that languages and edit or confirm"
            " translations for the other languages. If 'Restricted', then"
            " anybody can make suggestions but only the designated"
            " translators can edit or confirm translations. And if 'Closed'"
            " then only the designated translation group will be able to"
            " touch the translation files at all."),
        required=True,
        vocabulary='TranslationPermission')


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
            description=_("""The title of the Translation Group.
            This title is displayed at the top of the Translation Group page
            and in lists or reports of translation groups."""),
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
    owner = Choice(title=_('Owner'), required=True, vocabulary='ValidOwner',
            description=_("The owner's IPerson"))
    # joins
    translators = Attribute('The set of translators for this group.')
    projects = Attribute('The projects for which this group translates.')
    products = Attribute('The projects to which this group is directly '
        'appointed as a translator. There may be other projects that are '
        'part of project groups for which the group also translates.')
    distributions = Attribute('The distros for which this group translates.')

    # accessing the translator list
    def query_translator(language):
        """Retrieve a translator, or None, based on a Language"""

    def __getitem__(languagecode):
        """Retrieve the translator for the given language in this group."""

    def __iter__():
        """Return an iterator over the translators in the group."""

    # adding and removing translators
    def remove_translator(language):
        """Remove the translator for this language from the group."""

    # used for the form machinery
    def add(content):
        """Add a new object."""


class ITranslationGroupSet(IAddFormCustomization):
    """A container for translation groups."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get a translation group by name."""

    def __iter__():
        """Iterate through the translation groups in this set."""

    def new(name, title, summary, owner):
        """Create a new translation group."""

    def getByPerson(person):
        """Return the translation groups which that person is a member of."""

    def getGroupsCount():
        """Return the amount of translation groups available."""
