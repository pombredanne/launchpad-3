# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation class for objects that `POTemplate`s can belong to."""

__metaclass__ = type
__all__ = [
    'HasTranslationTemplatesMixin',
    ]

from storm.expr import (
    Count,
    Desc,
    )
from zope.interface import implements

from canonical.launchpad import helpers
from lp.app.enums import service_uses_launchpad
from lp.translations.interfaces.hastranslationtemplates import (
    IHasTranslationTemplates,
    )
from lp.translations.model.potemplate import POTemplate
from lp.translations.model.pofile import POFile


class HasTranslationTemplatesMixin:
    """Helper class for implementing `IHasTranslationTemplates`."""
    implements(IHasTranslationTemplates)

    def getTemplatesCollection(self):
        """See `IHasTranslationTemplates`.

        To be provided by derived classes.
        """
        raise NotImplementedError(
            "Child class must provide getTemplatesCollection.")

    def _orderTemplates(self, result):
        """Apply the conventional ordering to a result set of templates."""
        return result.order_by(Desc(POTemplate.priority), POTemplate.name)

    def getCurrentTemplatesCollection(self, current_value=True):
        """See `IHasTranslationTemplates`."""
        collection = self.getTemplatesCollection()

        # XXX JeroenVermeulen 2010-07-15 bug=605924: Move the
        # translations_usage distinction into browser code.
        pillar = collection.target_pillar
        if service_uses_launchpad(pillar.translations_usage):
            return collection.restrictCurrent(current_value)
        else:
            # Product/Distribution does not have translation enabled.
            # Treat all templates as obsolete.
            return collection.refine(not current_value)

    def getCurrentTranslationTemplates(self,
                                       just_ids=False,
                                       current_value=True):
        """See `IHasTranslationTemplates`."""
        if just_ids:
            selection = POTemplate.id
        else:
            selection = POTemplate

        collection = self.getCurrentTemplatesCollection(current_value)
        return self._orderTemplates(collection.select(selection))

    @property
    def has_translation_templates(self):
        """See `IHasTranslationTemplates`."""
        return bool(self.getTranslationTemplates().any())

    @property
    def has_current_translation_templates(self):
        """See `IHasTranslationTemplates`."""
        return bool(
            self.getCurrentTranslationTemplates(just_ids=True).any())

    def getCurrentTranslationFiles(self, just_ids=False):
        """See `IHasTranslationTemplates`."""
        if just_ids:
            selection = POFile.id
        else:
            selection = POFile

        collection = self.getCurrentTemplatesCollection()
        return collection.joinPOFile().select(selection)

    @property
    def has_translation_files(self):
        """See `IHasTranslationTemplates`."""
        return bool(
            self.getCurrentTranslationFiles(just_ids=True).any())

    def getObsoleteTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        # XXX JeroenVermeulen 2010-07-15 bug=605924: This returns a list
        # whereas the analogous method for current template returns a
        # result set.  Clean up this mess.
        return list(self.getCurrentTranslationTemplates(current_value=False))

    def getTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        return self._orderTemplates(self.getTemplatesCollection().select())

    def getTranslationTemplateFormats(self):
        """See `IHasTranslationTemplates`."""
        formats_query = self.getCurrentTranslationTemplates().order_by(
            'source_file_format').config(distinct=True)
        return helpers.shortlist(
            formats_query.values(POTemplate.source_file_format), 10)

    def getTemplatesAndLanguageCounts(self):
        """See `IHasTranslationTemplates`."""
        join = self.getTemplatesCollection().joinOuterPOFile()
        result = join.select(POTemplate, Count(POFile.id))
        return result.group_by(POTemplate)
