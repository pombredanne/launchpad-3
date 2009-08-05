# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [ 'MessageSharingMerge' ]


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.utilities.orderingcheck import OrderingCheck
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.interfaces.translations import TranslationConstants
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
    # Import here to avoid circular import.
    from lp.translations.interfaces.pofiletranslator import (
        IPOFileTranslatorSet)

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


def filter_clashes(clashing_current, clashing_imported, twin):
    """Filter clashes for harmless clashes with an identical message.

    Takes the three forms of clashes a message can have in a context
    it's being merged into:
     * Another message that also has the is_current flag.
     * Another message that also has the is_imported flag.
     * Another message with the same translations.

    If either of the first two clashes matches the third, that is not a
    real clash since it can be resolved by merging the message into the
    twin.

    This function returns the same tuple but with these "harmless"
    clashes eliminated.
    """
    if clashing_current == twin:
        clashing_current = None
    if clashing_imported == twin:
        clashing_imported = None
    return clashing_current, clashing_imported, twin


def sacrifice_flags(message, incumbents=None):
    """Drop current/imported flags if held by any of `incumbents`.

    :param message: a `TranslationMessage` to drop flags on.
    :param incumbents: a sequence of reference messages.  If any of
        these has either is_current or is_imported set, that same
        flag will be dropped on message (if set).
    """
    if incumbents:
        for incumbent in incumbents:
            if incumbent is not None and incumbent.is_current:
                message.is_current = False
            if incumbent is not None and incumbent.is_imported:
                message.is_imported = False


def bequeathe_flags(source_message, target_message, incumbents=None):
    """Destroy `source_message`, leaving flags to `target_message`.

    If `source_message` holds the is_current flag, and there are no
    `incumbents` that hold the same flag, then `target_message` inherits
    it.  Similar for the is_imported flag.
    """
    sacrifice_flags(source_message, incumbents)

    if source_message.is_current and not target_message.is_current:
        source_message.is_current = False
        target_message.is_current = True
    if source_message.is_imported and not target_message.is_imported:
        source_message.is_imported = False
        target_message.is_imported = True

    source_message.destroySelf()


class MessageSharingMerge(LaunchpadScript):

    templateset = None

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

    def _setUpUtilities(self):
        """Prepare a few members that several methods need.

        Calling this again later does nothing.
        """
        if self.templateset is None:
            self.templateset = getUtility(IPOTemplateSet)
            self.compare_template_precedence = (
                self.templateset.compareSharingPrecedence)

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

        self._setUpUtilities()

        subset = self.templateset.getSharingSubset(
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
                self._mergePOTMsgSets(templates)

            if self.options.merge_translationmessages:
                self._mergeTranslationMessages(templates)

            self._endTransaction()

        self.logger.info("Done.")

    def _endTransaction(self):
        if self.options.dry_run:
            self.txn.abort()
        else:
            self.txn.commit()
        self.txn.begin()

    def _mergePOTMsgSets(self, potemplates):
        """Merge POTMsgSets for given sequence of sharing templates."""
        self._setUpUtilities()

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
        order_check = OrderingCheck(cmp=self.compare_template_precedence)

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
            # Scrub the representative POTMsgSet of any duplicate
            # translation messages.  We don't need do this for subordinates
            # because the algorithm will refuse to add new duplicates to the
            # representative POTMsgSet anyway.
            self._scrubPOTMsgSetTranslations(representative)

            seen_potmsgsets = set([representative])

            # Merge each subordinate POTMsgSet into its representative.
            for subordinate in potmsgsets:
                if subordinate in seen_potmsgsets:
                    continue

                seen_potmsgsets.add(subordinate)

                for message in subordinate.getAllTranslationMessages():
                    message = removeSecurityProxy(message)

                    clashing_current, clashing_imported, twin = (
                        self._findClashes(
                            message, representative, message.potemplate))

                    if clashing_current or clashing_imported:
                        saved = self._saveByDiverging(
                            message, representative, subordinate)
                    else:
                        saved = False

                    if not saved:
                        if twin is None:
                            # This message will have to lose some flags, but
                            # then it can still move to the new potmsgset.
                            sacrifice_flags(
                                message,
                                (clashing_current, clashing_imported))
                            message.potmsgset = representative
                        else:
                            # This message is identical in contents to one
                            # that was more representative.  It'll have to
                            # die, but maybe it can bequeathe some of its
                            # status to the existing message.
                            # Since there are no clashes, there's no need to
                            # check for clashes with other current/imported
                            # messages in the target context.
                            bequeathe_flags(
                                message, twin,
                                (clashing_current, clashing_imported))

                merge_translationtemplateitems(
                    subordinate, representative,
                    representative_templates[representative])
                removeSecurityProxy(subordinate).destroySelf()

    def _mergeTranslationMessages(self, potemplates):
        """Share `TranslationMessage`s between templates where possible."""
        self._setUpUtilities()
        order_check = OrderingCheck(cmp=self.compare_template_precedence)
        for template in potemplates:
            order_check.check(template)
            for potmsgset in template.getPOTMsgSets(False):
                for message in potmsgset.getAllTranslationMessages():
                    removeSecurityProxy(message).shareIfPossible()

    def _getPOTMsgSetTranslationMessageKey(self, tm):
        """Return tuple that identifies a TranslationMessage in a POTMsgSet.

        A TranslationMessage is identified by (potemplate, potmsgset,
        language, variant, msgstr0, ...).  In this case we leave out the
        potmsgset (because we start out with one) and potemplate (because
        that's sorted out in the nested dicts).
        """
        tm = removeSecurityProxy(tm)
        msgstr_ids = [
            getattr(tm, 'msgstr%dID' % form)
            for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)
                ]
            
        return (tm.language, tm.variant) + tuple(msgstr_ids)

    def _mapExistingMessages(self, potmsgset):
        """Map out the existing TranslationMessages for `potmsgset`.

        :return: a dict mapping message keys (as returned by
        `_getPOTMsgSetTranslationMessageKey`) to further dicts, which
        map templates to TranslationMessages for that key and template.
        Each list should normally have only one message in it, but in
        the transition period this isn't always the case.
        """
        existing_tms = {}

        for tm in potmsgset.getAllTranslationMessages():
            key = self._getPOTMsgSetTranslationMessageKey(tm)
            if key not in existing_tms:
                existing_tms[key] = {}
            per_template = existing_tms[key]

            if tm.potemplate not in per_template:
                per_template[tm.potemplate] = []

            per_template[tm.potemplate].append(tm)

        return existing_tms

    def _scrubPOTMsgSetTranslations(self, potmsgset):
        """Map out translations for `potmsgset`, and eliminate duplicates.

        In the transition period for message sharing, there may be
        duplicate TranslationMessages that may upset assumptions in the
        code.  Clean those up.
        """
        # XXX JeroenVermeulen 2009-06-15
        # spec=message-sharing-prevent-duplicates: We're going to have a
        # unique index again at some point that will prevent this.  When
        # it becomes impossible to test this function, it can be
        # removed.
        translations = self._mapExistingMessages(potmsgset)

        for key, per_template in translations.iteritems():
            for template, tms in per_template.iteritems():
                assert len(tms) > 0, "Empty-list entry in translations dict."
                if len(tms) == 1:
                    continue
                self.logger.info(
                    "Cleaning up %s identical '%s' messages for: \"%s\"" % (
                    len(tms), tms[0].language.getFullCode(),
                    potmsgset.singular_text))
                for tm in tms[1:]:
                    assert tm != tms[0], "Duplicate is listed twice."
                    assert tm.potmsgset == tms[0].potmsgset, (
                        "Different potmsgsets considered identical.")
                    assert tm.potemplate == tms[0].potemplate, (
                        "Different potemplates considered identical.")

                    # Transfer any current/imported flags to the first of
                    # the identical messages, and delete the duplicates.
                    bequeathe_flags(tm, tms[0])
                    removeSecurityProxy(tm).sync()

                per_template[template] = [tms[0]]

        return translations

    def _findClashes(self, message, target_potmsgset, target_potemplate):
        """What would clash if we moved `message` to the target environment?

        A clash can be either `message` being current when the target
        environment already has a current message for that language, or
        similar for the message being imported.

        :return: a tuple of a clashing current message or None, a
            clashing imported message or None, and a message that is
            identical to the one you passed in, if present.
        """
        clashing_current = None
        if message.is_current:
            found = target_potmsgset.getCurrentTranslationMessage(
                potemplate=target_potemplate, language=message.language,
                variant=message.variant)
            if found is not None and found.potemplate == target_potemplate:
                clashing_current = found

        clashing_imported = None
        if message.is_imported:
            found = target_potmsgset.getImportedTranslationMessage(
                potemplate=target_potemplate, language=message.language,
                variant=message.variant)
            if found is not None and found.potemplate == target_potemplate:
                clashing_imported = found

        twin = message.findIdenticalMessage(
            target_potmsgset, target_potemplate)

        # Clashes with a twin message not real clashes: in such cases the
        # message can be merged into the twin without problems.
        return filter_clashes(clashing_current, clashing_imported, twin)

    def _saveByDiverging(self, message, target_potmsgset, source_potmsgset):
        """Avoid a TranslationMessage clash during POTMsgSet merge.

        The clash in this case is that we're trying to move `message`
        into a target environment (POTMsgSet and either POTemplate or
        shared status) that already has a current/imported message.

        This function tries to preserve the message for its original
        environment by making it diverged.  If successful, the message
        will become a diverged one for one POTemplate that
        source_potmsgset is linked to, preferring the one it was linked
        to first.
        """
        if message.potemplate is None:
            # This message was shared.  Maybe we can still save it for at
            # least one template by making it diverged.
            target_ttis = source_potmsgset.getAllTranslationTemplateItems()
            target_templates = [tti.potemplate for tti in target_ttis]
            target_templates.sort(self.compare_template_precedence)
            for template in target_templates:
                if self._divergeTo(message, target_potmsgset, template):
                    return True

        # No, there's no place where this message can be preserved.  It'll
        # have to go.
        return False

    def _divergeTo(self, message, target_potmsgset, target_potemplate):
        """Attempt to save `message` by diverging to `target_potemplate`.

        :param message: a TranslationMessage to save by diverging.
        :param target_potmsgset: the POTMsgSet that `message` is to be
            attached to.
        :param target_potemplate: a POTemplate that the message might be
            able to diverge to.
        :return: whether a solution was found for this message.  If
            True, you're done with `message`.  If False, you'll have to
            find another place for it.
        """
        clashing_current, clashing_imported, twin = self._findClashes(
            message, target_potmsgset, target_potemplate)

        if clashing_current is not None or clashing_imported is not None:
            return False

        if twin is None:
            # The message can diverge to this template and keep its
            # flags.
            message.potemplate = target_potemplate
            message.potmsgset = target_potmsgset
        else:
            # This template has an identical message.  All we need to do
            # is transfer the message's current/imported status to it,
            # and we can get rid of the original message.
            bequeathe_flags(message, twin)

        return True
