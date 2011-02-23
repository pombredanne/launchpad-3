# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from storm.locals import ClassAlias, Store

from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )


class TranslationSplitter:
    """Split translations for a productseries, sourcepackage pair.

    If a productseries and sourcepackage were linked in error, and then
    unlinked, they may still share some translations.  This class breaks those
    associations.
    """

    def __init__(self, productseries, sourcepackage):
        """Constructor.

        :param productseries: The `ProductSeries` to split from.
        :param sourcepackage: The `SourcePackage` to split from.
        """
        self.productseries = productseries
        self.sourcepackage = sourcepackage

    def findShared(self):
        """Provide tuples of upstream, ubuntu for each shared POTMsgSet."""
        store = Store.of(self.productseries)
        UpstreamItem = ClassAlias(TranslationTemplateItem, 'UpstreamItem')
        UpstreamTemplate = ClassAlias(POTemplate, 'UpstreamTemplate')
        UbuntuItem = ClassAlias(TranslationTemplateItem, 'UbuntuItem')
        UbuntuTemplate = ClassAlias(POTemplate, 'UbuntuTemplate')
        return store.find(
            (UpstreamItem, UbuntuItem),
            UpstreamItem.potmsgsetID == UbuntuItem.potmsgsetID,
            UbuntuItem.potemplateID == UbuntuTemplate.id,
            UbuntuTemplate.sourcepackagenameID ==
                self.sourcepackage.sourcepackagename.id,
            UbuntuTemplate.distroseriesID ==
                self.sourcepackage.distroseries.id,
            UpstreamItem.potemplateID == UpstreamTemplate.id,
            UpstreamTemplate.productseriesID == self.productseries.id,
        )

    @staticmethod
    def splitPOTMsgSet(ubuntu_item):
        """Split the POTMsgSet for TranslationTemplateItem.

        The specified `TranslationTemplateItem` will have a new `POTMsgSet`
        that is a clone of the old one.  All other TranslationTemplateItems
        will continue to use the old POTMsgSet.

        :param ubuntu_item: The `TranslationTemplateItem` to use.
        """
        new_potmsgset = ubuntu_item.potmsgset.clone()
        ubuntu_item.potmsgset = new_potmsgset
        return new_potmsgset

    @staticmethod
    def migrateTranslations(upstream_msgset, ubuntu_item):
        """Migrate the translations between potemplates.

        :param upstream_msgset: The `POTMsgSet` to copy or move translations
            from.
        :param ubuntu_item: The target `TranslationTemplateItem`.
            ubuntu_item.potmsgset is the msgset to attach translations to and
            ubuntu_item.potemplate is used to determine whether to move a
            diverged translation.
        """
        for message in upstream_msgset.getAllTranslationMessages():
            if message.potemplate == ubuntu_item.potemplate:
                message.potmsgset = ubuntu_item.potmsgset
            elif not message.is_diverged:
                message.clone(ubuntu_item.potmsgset)

    def split(self):
        """Split the translations for the ProductSeries and SourcePackage."""
        for upstream_item, ubuntu_item in self.findShared():
            self.splitPOTMsgSet(ubuntu_item)
            self.migrateTranslations(upstream_item.potmsgset, ubuntu_item)
