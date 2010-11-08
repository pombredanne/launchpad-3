# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for objects that translation templates can belong to."""

__metaclass__ = type
__all__ = [
    'IHasTranslationTemplates',
    ]

from lazr.restful.declarations import (
    export_read_operation,
    operation_returns_collection_of,
    )
from zope.interface import Interface
from zope.schema import Bool

from canonical.launchpad import _


class IHasTranslationTemplates(Interface):
    """An entity that has translation templates attached.

    Examples include `ISourcePackage`, `IDistroSeries`, and `IProductSeries`.
    """

    has_translation_templates = Bool(
        title=_("Does this object have any translation templates?"),
        readonly=True)

    has_current_translation_templates = Bool(
        title=_("Does this object have current translation templates?"),
        readonly=True)

    has_translation_files = Bool(
        title=_("Does this object have translation files?"),
        readonly=True)

    def getTemplatesCollection():
        """Return templates as a `TranslationTemplatesCollection`.

        The collection selects all `POTemplate`s attached to the
        translation target that implements this interface.
        """

    def getCurrentTemplatesCollection():
        """Return `TranslationTemplatesCollection` of current templates.

        A translation template is considered active when both
        `IPOTemplate`.iscurrent and the `official_rosetta` flag for its
        containing `Product` or `Distribution` are set to True.
        """
        # XXX JeroenVermeulen 2010-07-16 bug=605924: Move the
        # official_rosetta distinction into browser code.

    def getCurrentTranslationTemplates(just_ids=False):
        """Return an iterator over all active translation templates.

        :param just_ids: If True, return only the `POTemplate.id` rather
            than the full `POTemplate`.  Used to save time on retrieving
            and deserializing the objects from the database.

        A translation template is considered active when both
        `IPOTemplate`.iscurrent and the `official_rosetta` flag for its
        containing `Product` or `Distribution` are set to True.
        """
        # XXX JeroenVermeulen 2010-07-16 bug=605924: Move the
        # official_rosetta distinction into browser code.

    def getCurrentTranslationFiles(just_ids=False):
        """Return an iterator over all active translation files.

        A translation file is active if it's attached to an
        active translation template.
        """

    def getObsoleteTranslationTemplates():
        """Return an iterator over its not active translation templates.

        A translation template is considered not active when any of
        `IPOTemplate`.iscurrent or `IDistribution`.official_rosetta flags
        are set to False.
        """

    @export_read_operation()
    @operation_returns_collection_of(Interface)
    def getTranslationTemplates():
        """Return an iterator over all its translation templates.

        The returned templates are either obsolete or current.

        :return: A sequence of `IPOTemplate`.
        """

    def getTranslationTemplateFormats():
        """A list of native formats for all current translation templates.
        """

    def getTemplatesAndLanguageCounts():
        """List tuples of `POTemplate` and its language count.

        A template's language count is the number of `POFile`s that
        exist for it.
        """
