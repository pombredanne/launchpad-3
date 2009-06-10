# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'MessageSharingMerge',
    'merge_potmsgsets',
    'merge_translationmessages',
    ]


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.pofiletranslator import (
    IPOFileTranslatorSet)
from canonical.launchpad.interfaces.potemplate import IPOTemplateSet
from canonical.launchpad.utilities.orderingcheck import OrderingCheck
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.services.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)


def get_potmsgset_key(potmsgset):
    """Get the tuple of identifying properties of a POTMsgSet.

    A POTMsgSet is identified by its msgid, optional plural msgid, and
    optional context identifier.
    """
    return (
        potmsgset.msgid_singular, potmsgset.msgid_plural, potmsgset.context)


def merge_pofiletranslators(from_potmsgset, to_template):
    """Merge POFileTranslator entries from one template into another.
    """
    pofiletranslatorset = getUtility(IPOFileTranslatorSet)
    affected_rows = pofiletranslatorset.getForPOTMsgSet(from_potmsgset)
    for pofiletranslator in affected_rows:
        person = pofiletranslator.person
        from_pofile = pofiletranslator.pofile
        to_pofile = to_template.getPOFileByLang(
            from_pofile.language.code, variant=from_pofile.variant)

        pofiletranslator = removeSecurityProxy(pofiletranslator)
        if to_pofile is None:
            # There's no POFile to move this to.  We could create one,
            # but it's probably not worth the trouble.
            pofiletranslator.destroySelf()
        else:
            existing_row = pofiletranslatorset.getForPersonPOFile(
                person, to_pofile)
            date_last_touched = pofiletranslator.date_last_touched
            if existing_row is None:
                # Move POFileTranslator over to representative POFile.
                pofiletranslator.pofile = to_pofile
            elif existing_row.date_last_touched < date_last_touched:
                removeSecurityProxy(existing_row).destroySelf()
            else:
                pofiletranslator.destroySelf()


def merge_translationtemplateitems(subordinate, representative,
                                   representative_template):
    """Merge subordinate POTMsgSet into its representative POTMsgSet.

    This adds all of the subordinate's TranslationTemplateItems to the
    representative's set of TranslationTemplateItems.
    
    Any duplicates are deleted, so after this, the subordinate will no
    longer have any TranslationTemplateItems.
    """
    source = subordinate.getAllTranslationTemplateItems()
    targets = representative.getAllTranslationTemplateItems()
    templates = set(item.potemplate for item in targets)

    for item in source:
        item = removeSecurityProxy(item)
        if item.potemplate in templates:
            # The representative POTMsgSet is already in this template.
            item.destroySelf()
        else:
            # Transfer linking-table entry to representative POTMsgSet.
            item.potmsgset = representative
            templates.add(item.potemplate)

        merge_pofiletranslators(item.potmsgset, representative_template)


def merge_potmsgsets(potemplates):
    """Merge POTMsgSets for given sequence of sharing templates."""

    # Map each POTMsgSet key (context, msgid, plural) to its
    # representative POTMsgSet.
    representatives = {}

    # Map each representative POTMsgSet to a list of subordinate
    # POTMsgSets it represents.
    subordinates = {}

    # Map each representative POTMsgSet to its representative
    # POTemplate.
    representative_templates = {}

    # Figure out representative potmsgsets and their subordinates.  Go
    # through the templates, starting at the most representative and
    # moving towards the least representative.  For any unique potmsgset
    # key we find, the first POTMsgSet is the representative one.
    order_check = OrderingCheck(
        cmp=getUtility(IPOTemplateSet).compareSharingPrecedence)
    for template in potemplates:
        order_check.check(template)
        for potmsgset in template.getPOTMsgSets(False):
            key = get_potmsgset_key(potmsgset)
            if key not in representatives:
                representatives[key] = potmsgset
                representative_templates[potmsgset] = template
            representative = representatives[key]
            if representative in subordinates:
                subordinates[representative].append(potmsgset)
            else:
                subordinates[representative] = []

    for representative, potmsgsets in subordinates.iteritems():
        # Merge each subordinate POTMsgSet into its representative.
        for subordinate in potmsgsets:
            assert subordinate != representative, (
                "A POTMsgSet was found subordinate to itself.")

            original_template = None

            for message in subordinate.getAllTranslationMessages():
                message = removeSecurityProxy(message)
                if message.potemplate is None:
                    # Guard against multiple shared current or imported
                    # messages.
                    if message.is_current:
                        clashing_shared_current = (
                            representative.getCurrentTranslationMessage(
                                potemplate=None, language=message.language,
                                variant=message.variant))
                    else:
                        clashing_shared_current = None

                    if message.is_imported:
                        clashing_shared_imported = (
                            representative.getImportedTranslationMessage(
                                potemplate=None, language=message.language,
                                variant=message.variant))
                    else:
                        clashing_shared_imported = None

                    if clashing_shared_current or clashing_shared_imported:
                        # This shared message can't cohabitate with one
                        # that was more representative.  Make it diverged.
                        if original_template is None:
                            # Look up subordinate's original template if
                            # we haven't already.  We can't just get its
                            # potemplate field because that field is
                            # being phased out and might not be set.
                            links = (
                                subordinate.getAllTranslationTemplateItems())
                            original_template = links[0].potemplate

                        message.potemplate = original_template

                message.potmsgset = representative

            merge_translationtemplateitems(
                subordinate, representative,
                representative_templates[representative])

            removeSecurityProxy(subordinate).destroySelf()


def merge_translationmessages(potemplates):
    """Share `TranslationMessage`s between `potemplates` where possible."""
    order_check = OrderingCheck(
        cmp=getUtility(IPOTemplateSet).compareSharingPrecedence)
    for template in potemplates:
        order_check.check(template)
        for potmsgset in template.getPOTMsgSets(False):
            for message in potmsgset.getAllTranslationMessages():
                removeSecurityProxy(message).shareIfPossible()


class MessageSharingMerge(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option('-d', '--distribution', dest='distribution',
            help="Distribution to merge messages for.")
        self.parser.add_option('-p', '--product', dest='product',
            help="Product to merge messages for.")
        self.parser.add_option('-P', '--merge-potmsgsets',
            action='store_true', dest='merge_potmsgsets',
            help="Merge POTMsgSets.")
        self.parser.add_option('-s', '--source-package', dest='sourcepackage',
            help="Source package name within a distribution.")
        self.parser.add_option('-t', '--template-names',
            dest='template_names',
            help="Merge for templates with name matching this regex pattern.")
        self.parser.add_option('-T', '--merge-translationmessages',
            action='store_true', dest='merge_translationmessages',
            help="Merge TranslationMessages.")
        self.parser.add_option('-x', '--dry-run', dest='dry_run',
            action='store_true',
            help="Dry run, don't really make any changes.")

    def main(self):
        actions = (
            self.options.merge_potmsgsets or
            self.options.merge_translationmessages)

        if not actions:
            raise LaunchpadScriptFailure(
                "Select at least one action: merge POTMsgSets, "
                "TranslationMessages, or both.")

        if self.options.product and self.options.distribution:
            raise LaunchpadScriptFailure(
                "Merge a product or a distribution, but not both.")

        if not (self.options.product or self.options.distribution):
            raise LaunchpadScriptFailure(
                "Specify a product or distribution to merge.")

        if self.options.sourcepackage and not self.options.distribution:
            raise LaunchpadScriptFailure(
                "Selecting a package only makes sense for distributions.")

        if self.options.product:
            product = getUtility(IProductSet).getByName(self.options.product)
            distribution = None
            if product is None:
                raise LaunchpadScriptFailure(
                    "Unknown product: '%s'" % self.options.product)
        else:
            product = None
            # import here to avoid circular import.
            from lp.registry.interfaces.distribution import IDistributionSet
            distribution = getUtility(IDistributionSet).getByName(
                self.options.distribution)
            if distribution is None:
                raise LaunchpadScriptFailure(
                    "Unknown distribution: '%s'" % self.options.distribution)

        if self.options.sourcepackage is None:
            sourcepackagename = None
        else:
            sourcepackagename = getUtility(ISourcePackageNameSet).queryByName(
                self.options.sourcepackage)
            if sourcepackagename is None:
                raise LaunchpadScriptFailure(
                    "Unknown source package name: '%s'" %
                        self.options.sourcepackage)

        subset = getUtility(IPOTemplateSet).getSharingSubset(
                product=product, distribution=distribution,
                sourcepackagename=sourcepackagename)
        equivalence_classes = subset.groupEquivalentPOTemplates(
                                                self.options.template_names)

        class_count = len(equivalence_classes)
        self.logger.info(
            "Merging %d template equivalence classes." % class_count)

        for number, name in enumerate(sorted(equivalence_classes.iterkeys())):
            templates = equivalence_classes[name]
            self.logger.info(
                "Merging equivalence class '%s': %d template(s) (%d / %d)" % (
                    name, len(templates) + 1, number, class_count))
            self.logger.debug("Templates: %s" % str(templates))

            if self.options.merge_potmsgsets:
                merge_potmsgsets(templates)

            if self.options.merge_translationmessages:
                merge_translationmessages(templates)

            self._endTransaction()

    def _endTransaction(self):
        if self.options.dry_run:
            self.txn.abort()
        else:
            self.txn.commit()
        self.txn.begin()
