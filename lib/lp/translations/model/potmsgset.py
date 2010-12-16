# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'credits_message_str',
    'POTMsgSet',
    ]


import logging
import re

from sqlobject import (
    ForeignKey,
    IntCol,
    SQLObjectNotFound,
    StringCol,
    )
from storm.expr import (
    Coalesce,
    Desc,
    Or,
    SQL,
    )
from storm.store import (
    EmptyResultSet,
    Store,
    )
from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from canonical.database.sqlbase import (
    cursor,
    quote,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import ISlaveStore
from canonical.launchpad.readonly import is_read_only
from lp.app.errors import UnexpectedFormData
from lp.translations.interfaces.potmsgset import (
    BrokenTextError,
    IPOTMsgSet,
    POTMsgSetInIncompatibleTemplatesError,
    TranslationCreditsType,
    )
from lp.translations.interfaces.side import (
    ITranslationSideTraitsSet,
    TranslationSide,
    )
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat,
    )
from lp.translations.interfaces.translationimporter import (
    ITranslationImporter,
    )
from lp.translations.interfaces.translationmessage import (
    RosettaTranslationOrigin,
    TranslationConflict,
    TranslationValidationStatus,
    )
from lp.translations.interfaces.translations import TranslationConstants
from lp.translations.model.pomsgid import POMsgID
from lp.translations.model.potranslation import POTranslation
from lp.translations.model.translationmessage import (
    DummyTranslationMessage,
    make_plurals_sql_fragment,
    TranslationMessage,
    )
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )
from lp.translations.utilities.validate import (
    GettextValidationError,
    validate_translation,
    )

# Msgids that indicate translation credit messages, and their
# contexts and type.
credits_message_info = {
    # Regular gettext credits messages.
    u'translation-credits': (None, TranslationCreditsType.GNOME),
    u'translator-credits': (None, TranslationCreditsType.GNOME),
    u'translator_credits': (None, TranslationCreditsType.GNOME),

    # KDE credits messages.
    u'Your emails':
        (u'EMAIL OF TRANSLATORS', TranslationCreditsType.KDE_EMAILS),
    u'Your names':
        (u'NAME OF TRANSLATORS', TranslationCreditsType.KDE_NAMES),

    # Old KDE credits messages.
    u'_: EMAIL OF TRANSLATORS\nYour emails':
        (None, TranslationCreditsType.KDE_EMAILS),
    u'_: NAME OF TRANSLATORS\nYour names':
        (None, TranslationCreditsType.KDE_NAMES),
    }

# String to be used as msgstr for translation credits messages.
credits_message_str = (u'This is a dummy translation so that the '
                       u'credits are counted as translated.')


# Marker for "no incumbent message found yet."
incumbent_unknown = object()


def dictify_translations(translations):
    """Represent `translations` as a normalized dict.

    :param translations: a dict or sequence of `POTranslation`s or
        translation strings per plural form.
    :return: a dict mapping each translated plural form to an item in
        the original list.  Untranslated forms are omitted.
    """
    if not isinstance(translations, dict):
        # Turn a sequence into a dict.
        translations = dict(enumerate(translations))
    # Filter out None values.
    return dict(
        (form, translation)
        for form, translation in translations.iteritems()
        if translation is not None)


class POTMsgSet(SQLBase):
    implements(IPOTMsgSet)

    _table = 'POTMsgSet'

    context = StringCol(dbName='context', notNull=False)
    msgid_singular = ForeignKey(foreignKey='POMsgID', dbName='msgid_singular',
        notNull=True)
    msgid_plural = ForeignKey(foreignKey='POMsgID', dbName='msgid_plural',
        notNull=False, default=DEFAULT)
    sequence = IntCol(dbName='sequence')
    commenttext = StringCol(dbName='commenttext', notNull=False)
    filereferences = StringCol(dbName='filereferences', notNull=False)
    sourcecomment = StringCol(dbName='sourcecomment', notNull=False)
    flagscomment = StringCol(dbName='flagscomment', notNull=False)

    _cached_singular_text = None

    _cached_uses_english_msgids = None

    credits_message_ids = credits_message_info.keys()

    def __storm_invalidated__(self):
        super(POTMsgSet, self).__storm_invalidated__()
        self._cached_singular_text = None
        self._cached_uses_english_msgids = None

    def _conflictsExistingSourceFileFormats(self, source_file_format=None):
        """Return whether `source_file_format` conflicts with existing ones
        for this `POTMsgSet`.

        If `source_file_format` is None, just check the overall consistency
        of all the source_file_format values.  Otherwise, it should be
        a `TranslationFileFormat` value.
        """

        translation_importer = getUtility(ITranslationImporter)

        if source_file_format is not None:
            format = translation_importer.getTranslationFormatImporter(
                source_file_format)
            uses_english_msgids = not format.uses_source_string_msgids
        else:
            uses_english_msgids = None

        # Now let's find all the source_file_formats for all the
        # POTemplates this POTMsgSet is part of.
        query = """
           SELECT DISTINCT POTemplate.source_file_format
             FROM TranslationTemplateItem
                  JOIN POTemplate
                    ON POTemplate.id = TranslationTemplateItem.potemplate
             WHERE TranslationTemplateItem.potmsgset = %s""" % (
            sqlvalues(self))
        cur = cursor()
        cur.execute(query)
        source_file_formats = cur.fetchall()
        for source_file_format, in source_file_formats:
            format = translation_importer.getTranslationFormatImporter(
                TranslationFileFormat.items[source_file_format])
            format_uses_english_msgids = not format.uses_source_string_msgids

            if uses_english_msgids is None:
                uses_english_msgids = format_uses_english_msgids
            else:
                if uses_english_msgids != format_uses_english_msgids:
                    # There are conflicting source_file_formats for this
                    # POTMsgSet.
                    return (True, None)
                else:
                    uses_english_msgids = format_uses_english_msgids

        # No conflicting POTemplate entries were found.
        return (False, uses_english_msgids)

    @property
    def uses_english_msgids(self):
        """See `IPOTMsgSet`."""
        # TODO: convert to cachedproperty, it will be simpler.
        if self._cached_uses_english_msgids is not None:
            return self._cached_uses_english_msgids

        conflicts, uses_english_msgids = (
            self._conflictsExistingSourceFileFormats())

        if conflicts:
            raise POTMsgSetInIncompatibleTemplatesError(
                "This POTMsgSet participates in two POTemplates which "
                "have conflicting values for uses_english_msgids.")
        else:
            if uses_english_msgids is None:
                # Default is to use English in msgids, as opposed
                # to using unique identifiers (like XPI files do) and
                # having a separate English translation.
                # However, we are not caching anything when there's
                # no value to cache.
                return True
            self._cached_uses_english_msgids = uses_english_msgids
        return self._cached_uses_english_msgids

    @property
    def singular_text(self):
        """See `IPOTMsgSet`."""
        # TODO: convert to cachedproperty, it will be simpler.
        if self._cached_singular_text is not None:
            return self._cached_singular_text

        if self.uses_english_msgids:
            self._cached_singular_text = self.msgid_singular.msgid
            return self._cached_singular_text

        # Singular text is stored as an "English translation." Search on
        # both sides.
        # XXX henninge 2010-12-14, bug=690196 This may still need some
        # re-thinking. Maybe even add "getAnyCurrentTranslation".
        translation_message = self.getCurrentTranslation(
            None, getUtility(ILaunchpadCelebrities).english,
            TranslationSide.UBUNTU)
        if translation_message is None:
            translation_message = self.getCurrentTranslation(
                None, getUtility(ILaunchpadCelebrities).english,
                TranslationSide.UPSTREAM)
        if translation_message is not None:
            msgstr0 = translation_message.msgstr0
            if msgstr0 is not None:
                self._cached_singular_text = msgstr0.translation
                return self._cached_singular_text

        # There is no "English translation," at least not yet.  Return
        # symbolic msgid, but do not cache--an English text may still be
        # imported.
        return self.msgid_singular.msgid

    def clearCachedSingularText(self):
        """Clear cached result for `singular_text`, if any."""
        self._cached_singular_text = None

    @property
    def plural_text(self):
        """See `IPOTMsgSet`."""
        if self.msgid_plural is None:
            return None
        else:
            return self.msgid_plural.msgid

    def getCurrentTranslationMessageOrDummy(self, pofile):
        """See `IPOTMsgSet`."""
        template = pofile.potemplate
        current = self.getCurrentTranslation(
            template, pofile.language, template.translation_side)
        if current is None:
            dummy = DummyTranslationMessage(pofile, self)
            side = pofile.potemplate.translation_side
            traits = getUtility(ITranslationSideTraitsSet).getTraits(side)
            traits.setFlag(dummy, True)
            return dummy
        else:
            current.setPOFile(pofile)
            return current

    def _getUsedTranslationMessage(self, potemplate, language, current=True):
        """Get a translation message which is either used in
        Launchpad (current=True) or in an import (current=False).

        Prefers a diverged message if present.
        """
        # Change 'is_current IS TRUE' and 'is_imported IS TRUE' conditions
        # carefully: they need to match condition specified in indexes,
        # or Postgres may not pick them up (in complicated queries,
        # Postgres query optimizer sometimes does text-matching of indexes).
        
        if current:
            used_clause = 'is_current_ubuntu IS TRUE'
        else:
            used_clause = 'is_current_upstream IS TRUE'
        if potemplate is None:
            template_clause = 'TranslationMessage.potemplate IS NULL'
        else:
            template_clause = (
                '(TranslationMessage.potemplate IS NULL OR '
                ' TranslationMessage.potemplate=%s)' % sqlvalues(potemplate))
        clauses = [
            'potmsgset = %s' % sqlvalues(self),
            used_clause,
            template_clause,
            'TranslationMessage.language = %s' % sqlvalues(language)]

        order_by = '-COALESCE(potemplate, -1)'

        # This should find at most two messages: zero or one shared
        # message, and zero or one diverged one.
        return TranslationMessage.selectFirst(
            ' AND '.join(clauses), orderBy=[order_by])

    def getCurrentTranslationMessage(self, potemplate, language):
        """See `IPOTMsgSet`."""
        return self._getUsedTranslationMessage(
            potemplate, language, current=True)

    def getImportedTranslationMessage(self, potemplate, language):
        """See `IPOTMsgSet`."""
        return self._getUsedTranslationMessage(
            potemplate, language, current=False)

    def getSharedTranslationMessage(self, language):
        """See `IPOTMsgSet`."""
        return self._getUsedTranslationMessage(
            None, language, current=True)

    def getOtherTranslation(self, language, side):
        """See `IPOTMsgSet`."""
        traits = getUtility(
            ITranslationSideTraitsSet).getTraits(side)
        return self.getCurrentTranslation(
            None, language, traits.other_side_traits.side)

    def getSharedTranslation(self, language, side):
        """See `IPOTMsgSet`."""
        return self.getCurrentTranslation(
            None, language, side)

    def getCurrentTranslation(self, potemplate, language, side):
        """See `IPOTMsgSet`."""
        assert side is not None, "Translation side must be specified."
        traits = getUtility(ITranslationSideTraitsSet).getTraits(side)
        flag = removeSecurityProxy(traits.getFlag(TranslationMessage))

        clauses = [
            flag == True,
            TranslationMessage.potmsgsetID == self.id,
            TranslationMessage.languageID == language.id,
            ]

        if potemplate is None:
            # Look only for a shared translation.
            clauses.append(TranslationMessage.potemplate == None)
        else:
            clauses.append(Or(
                TranslationMessage.potemplate == None,
                TranslationMessage.potemplateID == potemplate.id))

        # Return a diverged translation if it exists, and fall back
        # to the shared one otherwise.
        result = Store.of(self).find(
            TranslationMessage, *clauses).order_by(
              Desc(Coalesce(TranslationMessage.potemplateID, -1))).first()
        return result

    def getLocalTranslationMessages(self, potemplate, language,
                                    include_dismissed=False,
                                    include_unreviewed=True):
        """See `IPOTMsgSet`."""
        query = """
            is_current_ubuntu IS NOT TRUE AND
            is_current_upstream IS NOT TRUE AND
            potmsgset = %s AND
            language = %s
            """ % sqlvalues(self, language)
        msgstr_clause = make_plurals_sql_fragment(
            "msgstr%(form)d IS NOT NULL", "OR")
        query += " AND (%s)" % msgstr_clause
        if include_dismissed != include_unreviewed:
            current = self.getCurrentTranslation(
                potemplate, language, potemplate.translation_side)
            if current is not None:
                if current.date_reviewed is None:
                    comparing_date = current.date_created
                else:
                    comparing_date = current.date_reviewed
                if include_unreviewed:
                    term = " AND date_created > %s"
                else:
                    term = " AND date_created <= %s"
                query += term % sqlvalues(comparing_date)
        elif include_dismissed and include_unreviewed:
            # Return all messages
            pass
        else:
            # No need to run a query.
            return EmptyResultSet()

        return TranslationMessage.select(query)

    def _getExternalTranslationMessages(self, language, used):
        """Return external suggestions for this message.

        External suggestions are all TranslationMessages for the
        same english string which are used or suggested in other templates.

        A message is used if it's either imported or current, and unused
        otherwise.

        Suggestions are read-only, so these objects come from the slave
        store.
        """
        if not config.rosetta.global_suggestions_enabled:
            return []

        # Return empty list (no suggestions) for translation credit strings
        # because they are automatically translated.
        if self.is_translation_credit:
            return []
        # Watch out when changing this condition: make sure it's done in
        # a way so that indexes are indeed hit when the query is executed.
        # Also note that there is a NOT(in_use_clause) index.
        in_use_clause = (
            "(is_current_ubuntu IS TRUE OR is_current_upstream IS TRUE)")
        if used:
            query = [in_use_clause]
        else:
            query = ["(NOT %s)" % in_use_clause]
        query.append('TranslationMessage.language = %s' % sqlvalues(language))
        query.append('TranslationMessage.potmsgset <> %s' % sqlvalues(self))

        query.append('''
            potmsgset IN (
                SELECT POTMsgSet.id
                FROM POTMsgSet
                JOIN TranslationTemplateItem ON
                    TranslationTemplateItem.potmsgset = POTMsgSet.id
                JOIN SuggestivePOTemplate ON
                    TranslationTemplateItem.potemplate =
                        SuggestivePOTemplate.potemplate
                WHERE msgid_singular = %s
            )''' % sqlvalues(self.msgid_singular))

        # Subquery to find the ids of TranslationMessages that are
        # matching suggestions.
        # We're going to get a lot of duplicates, sometimes resulting in
        # thousands of suggestions.  Weed out most of that duplication by
        # excluding older messages that are identical to newer ones in
        # all translated forms.  The Python code can later sort out the
        # distinct translations per form.
        msgstrs = ', '.join([
            'COALESCE(msgstr%d, -1)' % form
            for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)])
        ids_query_params = {
            'msgstrs': msgstrs,
            'where': ' AND '.join(query),
        }
        ids_query = '''
            SELECT DISTINCT ON (%(msgstrs)s)
                TranslationMessage.id
            FROM TranslationMessage
            WHERE %(where)s
            ORDER BY %(msgstrs)s, date_created DESC
            ''' % ids_query_params

        result = ISlaveStore(TranslationMessage).find(
            TranslationMessage,
            TranslationMessage.id.is_in(SQL(ids_query)))

        return shortlist(result, longest_expected=100, hardlimit=2000)

    def getExternallyUsedTranslationMessages(self, language):
        """See `IPOTMsgSet`."""
        return self._getExternalTranslationMessages(language, used=True)

    def getExternallySuggestedTranslationMessages(self, language):
        """See `IPOTMsgSet`."""
        return self._getExternalTranslationMessages(language, used=False)

    @property
    def flags(self):
        if self.flagscomment is None:
            return []
        else:
            return [flag
                    for flag in self.flagscomment.replace(' ', '').split(',')
                    if flag != '']

    def hasTranslationChangedInLaunchpad(self, potemplate, language):
        """See `IPOTMsgSet`."""
        other_translation = self.getOtherTranslation(
            language, potemplate.translation_side)
        current_translation = self.getCurrentTranslation(
            potemplate, language, potemplate.translation_side)
        return (other_translation is not None and
                other_translation != current_translation)

    def isTranslationNewerThan(self, pofile, timestamp):
        """See `IPOTMsgSet`."""
        if timestamp is None:
            return False
        template = pofile.potemplate
        current = self.getCurrentTranslation(
            template, pofile.language, template.translation_side)
        if current is None:
            return False
        date_updated = current.date_created
        if (current.date_reviewed is not None and
            current.date_reviewed > date_updated):
            date_updated = current.date_reviewed
        return (date_updated is not None and date_updated > timestamp)

    def _sanitizeTranslations(self, translations, pluralforms):
        """Sanitize `translations` using self.applySanityFixes.

        If there is no certain pluralform in `translations`, set it to None.
        If there are `translations` with greater pluralforms than allowed,
        sanitize and keep them.
        """
        # Strip any trailing or leading whitespace, and normalize empty
        # translations to None.
        sanitized_translations = {}
        for pluralform in range(pluralforms):
            if pluralform < len(translations):
                sanitized_translations[pluralform] = self.applySanityFixes(
                    translations[pluralform])
            else:
                sanitized_translations[pluralform] = None
        # Unneeded plural forms are stored as well (needed since we may
        # have incorrect plural form data, so we can just reactivate them
        # once we fix the plural information for the language)
        for index, value in enumerate(translations):
            if index not in sanitized_translations:
                sanitized_translations[index] = self.applySanityFixes(value)

        return sanitized_translations

    def validateTranslations(self, translations):
        """See `IPOTMsgSet`."""
        validate_translation(
            self.singular_text, self.plural_text, translations, self.flags)

    def _validate_translations(self, translations, ignore_errors):
        """Validate all the `translations` and return a validation_status."""
        # By default all translations are correct.
        validation_status = TranslationValidationStatus.OK

        # Validate the translation we got from the translation form
        # to know if gettext is unhappy with the input.
        try:
            self.validateTranslations(translations)
        except GettextValidationError:
            if ignore_errors:
                # The translations are stored anyway, but we set them as
                # broken.
                validation_status = TranslationValidationStatus.UNKNOWNERROR
            else:
                # Check to know if there is any translation.
                if any(translations.values()):
                    # Partial translations cannot be stored, the
                    # exception is raised again and handled outside
                    # this method.
                    raise

        return validation_status

    def _findPOTranslations(self, translations):
        """Find all POTranslation records for passed `translations`."""
        potranslations = {}
        # Set all POTranslations we can have (up to MAX_PLURAL_FORMS)
        for pluralform in xrange(TranslationConstants.MAX_PLURAL_FORMS):
            translation = translations.get(pluralform)
            if translation is not None:
                # Find or create a POTranslation for the specified text
                potranslations[pluralform] = (
                    POTranslation.getOrCreateTranslation(translation))
            else:
                potranslations[pluralform] = None
        return potranslations

    def findTranslationMessage(self, pofile, translations=None,
                               prefer_shared=False):
        """Find the best matching message in this `pofile`.

        The returned message matches exactly the given `translations`
        strings (except plural forms not supported by `pofile`, which
        are ignored in the comparison).

        :param translations: A dict mapping plural forms to translation
            strings.
        :param prefer_shared: Whether to prefer a shared match over a
            diverged one.
        """
        potranslations = self._findPOTranslations(translations)
        return self._findMatchingTranslationMessage(
            pofile, potranslations, prefer_shared=prefer_shared)

    def _findMatchingTranslationMessage(self, pofile, potranslations,
                                        prefer_shared=False):
        """Find the best matching message in this `pofile`.

        :param pofile: The `POFile` to look in.
        :param potranslations: a list of `POTranslation`s.  Forms that
            are not translated should have None instead.
        :param prefer_shared: Whether to prefer a shared match over a
            diverged one.
        """
        clauses = ['potmsgset = %s' % sqlvalues(self),
                   'language = %s' % sqlvalues(pofile.language),
                   '(potemplate IS NULL OR potemplate = %s)' % sqlvalues(
                                                        pofile.potemplate)]

        for pluralform in range(pofile.plural_forms):
            if potranslations[pluralform] is None:
                clauses.append('msgstr%s IS NULL' % sqlvalues(pluralform))
            else:
                clauses.append('msgstr%s=%s' % (
                    sqlvalues(pluralform, potranslations[pluralform])))

        remaining_plural_forms = range(
            pofile.plural_forms, TranslationConstants.MAX_PLURAL_FORMS)

        # Prefer either shared or diverged messages, depending on
        # arguments.
        if prefer_shared:
            order = ['potemplate NULLS FIRST']
        else:
            order = ['potemplate NULLS LAST']

        # Normally at most one message should match.  But if there is
        # more than one, prefer the one that adds the fewest extraneous
        # plural forms.
        order.extend([
            'msgstr%s NULLS FIRST' % quote(form)
            for form in remaining_plural_forms])
        matches = list(
            TranslationMessage.select(' AND '.join(clauses), orderBy=order))

        if len(matches) > 0:
            if len(matches) > 1:
                logging.info(
                    "Translation for POTMsgSet %s into %s "
                    "matches %s existing translations." % sqlvalues(
                        self, pofile.language.code, len(matches)))
            return matches[0]
        else:
            return None

    def _makeTranslationMessageCurrent(self, pofile, new_message,
                                       upstream_message, is_current_upstream,
                                       submitter, force_shared=False,
                                       force_diverged=False):
        """Make the given translation message the current one."""
        current_message = self.getCurrentTranslationMessage(
            pofile.potemplate, pofile.language)

        # Converging from a diverged to a shared translation:
        # when the new translation matches a shared one (iscurrent,
        # potemplate==None), and a current translation is diverged
        # (potemplate != None), then we want to remove divergence.
        converge_shared = force_shared
        if (not force_diverged and
            (current_message is None or
             ((new_message.potemplate is None and
                new_message.is_current_ubuntu) and
              (current_message.potemplate is not None)))):
            converge_shared = True

        make_current = False

        if is_current_upstream:
            # A new imported message is made current
            # if there is no existing current message
            # or if there was no previous imported message
            # or if the current message came from import
            # or if current message is empty (deactivated translation),
            # or if current message is the same as new message,
            # or, if we are forcing a diverged imported translation.
            # Empty imported translations should not replace
            # non-empty imported translations.
            if (current_message is None or
                upstream_message is None or
                (current_message.is_current_upstream and
                 (current_message.is_empty or not new_message.is_empty)) or
                current_message.is_empty or
                (current_message == new_message) or
                (force_diverged and not new_message.is_empty)):
                make_current = True

                # Don't update the submitter and date changed
                # if there was no current message and an empty
                # message is submitted.
                if (not (current_message is None and
                         new_message.is_empty)):
                    pofile.lasttranslator = submitter
                    pofile.date_changed = UTC_NOW

        else:
            # Non-imported translations.
            make_current = True
            pofile.lasttranslator = submitter
            pofile.date_changed = UTC_NOW

            if new_message.origin == RosettaTranslationOrigin.ROSETTAWEB:
                # The submitted translation came from our UI, we give
                # give karma to the submitter of that translation.
                new_message.submitter.assignKarma(
                    'translationsuggestionapproved',
                    product=pofile.potemplate.product,
                    distribution=pofile.potemplate.distribution,
                    sourcepackagename=pofile.potemplate.sourcepackagename)

            # If the current message has been changed, and it was submitted
            # by a different person than is now doing the review (i.e.
            # `submitter`), then give this reviewer karma as well.
            if new_message != current_message:
                if new_message.submitter != submitter:
                    submitter.assignKarma(
                        'translationreview',
                        product=pofile.potemplate.product,
                        distribution=pofile.potemplate.distribution,
                        sourcepackagename=pofile.potemplate.sourcepackagename)

                new_message.markReviewed(submitter, UTC_NOW)
                pofile.date_changed = UTC_NOW
                pofile.lasttranslator = submitter

        unmark_upstream = (
            make_current and
            upstream_message is not None and (
                is_current_upstream or upstream_message == new_message))
        if unmark_upstream:
            # Unmark previous imported translation as 'imported'.
            was_diverged_to = upstream_message.potemplate
            if (was_diverged_to is not None or
                (was_diverged_to is None and
                 new_message == current_message and
                 new_message.potemplate is not None)):
                # If imported message was diverged,
                # or if it was shared, but there was
                # a diverged current message that is
                # now being imported, previous imported
                # message is neither imported nor current
                # anymore.
                upstream_message.is_current_upstream = False
                upstream_message.is_current_ubuntu = False
                upstream_message.potemplate = None
                if upstream_message != new_message:
                    Store.of(upstream_message).add_flush_order(
                        upstream_message, new_message)
            if not (force_diverged or force_shared):
                # If there was an imported message, keep the same
                # divergence/shared state unless something was forced.
                if (new_message.is_current_upstream and
                    new_message.potemplate is None):
                    # If we are reverting imported message to
                    # a shared imported message, do not
                    # set it as diverged anymore.
                    was_diverged_to = None
                new_message.potemplate = was_diverged_to

        # Change actual is_current_ubuntu flag only if it validates ok.
        if new_message.validation_status == TranslationValidationStatus.OK:
            if make_current:
                if (current_message is not None and
                    current_message.potemplate is not None):
                    # Deactivate previous diverged message.
                    current_message.is_current_ubuntu = False
                    if current_message != new_message:
                        Store.of(current_message).add_flush_order(
                            current_message, new_message)

                    # Do not "converge" a diverged imported message since
                    # there might be another shared imported message.
                    if not current_message.is_current_upstream:
                        current_message.potemplate = None
                    if not converge_shared:
                        force_diverged = True
                if force_diverged:
                    # Make the message diverged.
                    new_message.potemplate = pofile.potemplate
                else:
                    # Either converge_shared==True, or a new message.
                    new_message.potemplate = None

                new_message.makeCurrentUbuntu()
            else:
                new_message.potemplate = None
        if is_current_upstream or new_message == upstream_message:
            new_message.makeCurrentUpstream()

    def _isTranslationMessageASuggestion(self, force_suggestion,
                                         pofile, submitter,
                                         force_edition_rights,
                                         is_current_upstream, lock_timestamp):
        # Whether a message should be saved as a suggestion and
        # whether we should display a warning when an older translation is
        # submitted.
        # Returns a pair of (just_a_suggestion, warn_about_lock_timestamp).

        if force_suggestion:
            return True, False

        # Is the submitter allowed to edit translations?
        is_editor = (force_edition_rights or
                     pofile.canEditTranslations(submitter))

        if is_read_only():
            # This can happen if the request was just in time to slip
            # past the read-only check before the gate closed.  If it
            # does, that screws up the privileges checks below since
            # nobody has translation privileges in read-only mode.
            raise UnexpectedFormData(
                "Sorry, Launchpad is in read-only mode right now.")

        if is_current_upstream and not is_editor:
            raise AssertionError(
                'Only an editor can submit is_current_upstream translations.')

        assert is_editor or pofile.canAddSuggestions(submitter), (
            '%s cannot add suggestions here.' % submitter.displayname)

        # If not an editor, default to submitting a suggestion only.
        just_a_suggestion = not is_editor
        warn_about_lock_timestamp = False

        # Our current submission is newer than 'lock_timestamp'
        # and we try to change it, so just add a suggestion.
        if (not just_a_suggestion and not is_current_upstream and
            self.isTranslationNewerThan(pofile, lock_timestamp)):
            just_a_suggestion = True
            warn_about_lock_timestamp = True

        return just_a_suggestion, warn_about_lock_timestamp

    def allTranslationsAreEmpty(self, translations):
        """Return true if all translations are empty strings or None."""
        has_translations = False
        for pluralform in translations:
            translation = translations[pluralform]
            if (translation is not None and translation != u""):
                has_translations = True
                break
        return not has_translations

    def updateTranslation(self, pofile, submitter, new_translations,
                          is_current_upstream, lock_timestamp,
                          force_shared=False, force_diverged=False,
                          force_suggestion=False, ignore_errors=False,
                          force_edition_rights=False, allow_credits=False):
        """See `IPOTMsgSet`."""

        just_a_suggestion, warn_about_lock_timestamp = (
            self._isTranslationMessageASuggestion(force_suggestion,
                                                  pofile, submitter,
                                                  force_edition_rights,
                                                  is_current_upstream,
                                                  lock_timestamp))

        # If the update is on the translation credits message, yet
        # update is not is_current_upstream, silently return.
        deny_credits = (not allow_credits and
                        self.is_translation_credit and
                        not is_current_upstream)
        if deny_credits:
            return None

        # Sanitize translations
        sanitized_translations = self._sanitizeTranslations(
            new_translations, pofile.plural_forms)
        # Check that the translations are correct.
        validation_status = self._validate_translations(
            sanitized_translations, ignore_errors)

        # Find all POTranslation records for strings we need.
        potranslations = self._findPOTranslations(sanitized_translations)

        # Find an existing TranslationMessage with exactly the same set
        # of translations.  None if there is no such message and needs to be
        # created.
        matching_message = self._findMatchingTranslationMessage(
            pofile, potranslations, prefer_shared=True)

        match_is_upstream = (
            matching_message is not None and
            matching_message.is_current_upstream)
        if is_current_upstream or match_is_upstream:
            upstream_message = self.getImportedTranslationMessage(
                pofile.potemplate, pofile.language)
        else:
            upstream_message = None

        if matching_message is None:
            # Creating a new message.

            if is_current_upstream:
                origin = RosettaTranslationOrigin.SCM
            else:
                origin = RosettaTranslationOrigin.ROSETTAWEB

            assert TranslationConstants.MAX_PLURAL_FORMS == 6, (
                "Change this code to support %d plural forms."
                % TranslationConstants.MAX_PLURAL_FORMS)

            if (is_current_upstream and
                self.allTranslationsAreEmpty(sanitized_translations)):
                # Don't create empty is_current_upstream translations
                if upstream_message is not None:
                    upstream_message.is_current_upstream = False
                    if upstream_message.is_current_ubuntu:
                        upstream_message.is_current_ubuntu = False
                return None
            else:
                # The pofile=pofile is only needed until 10.09 rollout.
                matching_message = TranslationMessage(
                    potmsgset=self,
                    potemplate=pofile.potemplate,
                    language=pofile.language,
                    origin=origin,
                    submitter=submitter,
                    msgstr0=potranslations[0],
                    msgstr1=potranslations[1],
                    msgstr2=potranslations[2],
                    msgstr3=potranslations[3],
                    msgstr4=potranslations[4],
                    msgstr5=potranslations[5],
                    validation_status=validation_status)

                if just_a_suggestion:
                    # Adds suggestion karma: editors get their translations
                    # automatically approved, so they get 'reviewer' karma
                    # instead.
                    submitter.assignKarma(
                        'translationsuggestionadded',
                        product=pofile.potemplate.product,
                        distribution=pofile.potemplate.distribution,
                        sourcepackagename=pofile.potemplate.sourcepackagename)
        else:
            # There is an existing matching message. Update it as needed.
            # Also update validation status if needed
            matching_message.validation_status = validation_status

        if just_a_suggestion:
            # An existing message is just a suggestion, warn if needed.
            if warn_about_lock_timestamp:
                raise TranslationConflict(
                    'The new translations were saved as suggestions to '
                    'avoid possible conflicts. Please review them.')
        else:
            # Makes the new_message current if needed and also
            # assigns karma for translation approval.
            self._makeTranslationMessageCurrent(
                pofile, matching_message, upstream_message,
                is_current_upstream, submitter,
                force_shared=force_shared, force_diverged=force_diverged)

        # We need this sync so we don't set self.isfuzzy to the wrong
        # value because cache problems. See bug #102382 as an example of what
        # happened without having this flag + broken code. Our tests were not
        # able to find the problem.
        # XXX CarlosPerelloMarin 2007-11-14 Is there any way to avoid the
        # sync() call and leave it as syncUpdate? Without it we have cache
        # problems with workflows like the ones in
        # xx-pofile-translate-gettext-error-middle-page.txt so we don't see
        # the successful submissions when there are other errors in the same
        # page.
        matching_message.sync()
        return matching_message

    def submitSuggestion(self, pofile, submitter, new_translations):
        """See `IPOTMsgSet`."""
        if self.is_translation_credit:
            # We don't support suggestions on credits messages.
            return None

        potranslations = self._findPOTranslations(new_translations)

        existing_message = self._findMatchingTranslationMessage(
            pofile, potranslations, prefer_shared=True)
        if existing_message is not None:
            return existing_message

        forms = dict(
            ('msgstr%d' % form, potranslation)
            for form, potranslation in potranslations.iteritems())

        pofile.potemplate.awardKarma(submitter, 'translationsuggestionadded')

        return TranslationMessage(
            potmsgset=self, language=pofile.language,
            origin=RosettaTranslationOrigin.ROSETTAWEB, submitter=submitter,
            **forms)

    def _checkForConflict(self, current_message, lock_timestamp,
                          potranslations=None):
        """Check `message` for conflicting changes since `lock_timestamp`.

        Call this before changing this message's translations, to ensure
        that a read-modify-write operation on a message does not
        accidentally overwrite newer changes based on older information.

        One example of a read-modify-write operation is: user downloads
        translation file, translates a message, then re-uploads.
        Another is: user looks at a message in the web UI, decides that
        neither the current translation nor any of the suggestions are
        right, and clears the message.

        In these scenarios, it's possible for someone else to come along
        and change the message's translation between the time we provide
        the user with a view of the current state and the time we
        receive a change from the user.  We call this a conflict.

        Raises `TranslationConflict` if a conflict exists.

        :param currentmessage: The `TranslationMessage` that is current
            now.  This is where we'll see any conflicting changes
            reflected in the date_reviewed timestamp.
        :param lock_timestamp: The timestamp of the translation state
            that the change is based on.
        :param potranslations: `POTranslation`s dict for the new
            translation.  If these are given, and identical to those of
            `current_message`, there is no conflict.
        """
        if lock_timestamp is None:
            # We're not really being asked to check for conflicts.
            return
        if current_message is None:
            # There is no current message to conflict with.
            return
        try:
            self._maybeRaiseTranslationConflict(
                current_message, lock_timestamp)
        except TranslationConflict:
            if potranslations is None:
                # We don't know what translations are going to be set;
                # based on the timestamps this is a conflict.
                raise
            old_msgstrs = dictify_translations(current_message.all_msgstrs)
            new_msgstrs = dictify_translations(potranslations)
            if new_msgstrs != old_msgstrs:
                # Yup, there really is a difference.  This is a proper
                # conflict.
                raise
            else:
                # Two identical translations crossed.  Not a conflict.
                pass

    def _maybeRaiseTranslationConflict(self, message, lock_timestamp):
        """Checks if there is a translation conflict for the message.

        If a translation conflict is detected, TranslationConflict is raised.
        """
        if message.date_reviewed is not None:
            use_date = message.date_reviewed
        else:
            use_date = message.date_created
        if use_date >= lock_timestamp:
            raise TranslationConflict(
                'While you were reviewing these suggestions, somebody '
                'else changed the actual translation. This is not an '
                'error but you might want to re-review the strings '
                'concerned.')
        else:
            return

    def dismissAllSuggestions(self, pofile, reviewer, lock_timestamp):
        """See `IPOTMsgSet`."""
        assert lock_timestamp is not None, "lock_timestamp is required."

        template = pofile.potemplate
        language = pofile.language
        side = template.translation_side
        current = self.getCurrentTranslation(template, language, side)

        if current is None:
            # Create or activate an empty translation message.
            current = self.setCurrentTranslation(
                pofile, reviewer, {}, RosettaTranslationOrigin.ROSETTAWEB,
                lock_timestamp=lock_timestamp)
        else:
            # Check for translation conflicts and update review fields.
            self._maybeRaiseTranslationConflict(current, lock_timestamp)
        current.markReviewed(reviewer, lock_timestamp)
        assert self.getCurrentTranslation(template, language, side)

    def _nameMessageStatus(self, message, translation_side_traits):
        """Figure out the decision-matrix status of a message.

        This is used in navigating the decision matrix in
        `setCurrentTranslation`.
        """
        if message is None:
            return 'none'
        elif message.is_diverged:
            return 'diverged'
        elif translation_side_traits.other_side_traits.getFlag(message):
            return 'other_shared'
        else:
            return 'shared'

    def _makeTranslationMessage(self, pofile, submitter, translations, origin,
                                diverged=False):
        """Create a new `TranslationMessage`.

        The message will not be made current on either side (Ubuntu or
        upstream), but it can be diverged.  Only messages that are
        current should be diverged, but it's up to the caller to ensure
        the right state.
        """
        if diverged:
            potemplate = pofile.potemplate
        else:
            potemplate = None

        translation_args = dict(
            ('msgstr%d' % form, translation)
            for form, translation in translations.iteritems())

        return TranslationMessage(
            potmsgset=self,
            potemplate=potemplate,
            pofile=pofile,
            language=pofile.language,
            origin=origin,
            submitter=submitter,
            validation_status=TranslationValidationStatus.OK,
            **translation_args)

    def approveSuggestion(self, pofile, suggestion, reviewer,
                          share_with_other_side=False, lock_timestamp=None):
        """Approve a suggestion.

        :param pofile: The `POFile` that the suggestion is being approved for.
        :param suggestion: The `TranslationMessage` being approved.
        :param reviewer: The `Person` responsible for approving the
            suggestion.
        :param share_with_other_side: Policy selector: share this change with
            the other translation side if possible?
        :param lock_timestamp: Timestamp of the original translation state
            that this change is based on.
        """
        template = pofile.potemplate
        traits = getUtility(ITranslationSideTraitsSet).getTraits(
            template.translation_side)
        if traits.getFlag(suggestion):
            # Message is already current.
            return

        translator = suggestion.submitter
        potranslations = suggestion.all_msgstrs
        activated_message = self._setTranslation(
            pofile, translator, suggestion.origin, potranslations,
            share_with_other_side=share_with_other_side,
            identical_message=suggestion, lock_timestamp=lock_timestamp)

        activated_message.markReviewed(reviewer)
        if reviewer != translator:
            template.awardKarma(translator, 'translationsuggestionapproved')
            template.awardKarma(reviewer, 'translationreview')

    def _cloneAndDiverge(self, original_message, pofile):
        """Create a diverged clone of a `TranslationMessage`.

        The message is not made current; the caller must do so in order
        to keep the message in a consistent state.
        """
        potranslations = self._findPOTranslations(
            dict(enumerate(original_message.translations)))
        message = self._makeTranslationMessage(
            pofile, original_message.submitter, potranslations,
            original_message.origin, diverged=True)
        return message

    def approveAsDiverged(self, pofile, suggestion, reviewer,
                          lock_timestamp=None):
        """Approve a suggestion to become a diverged translation."""
        template = pofile.potemplate
        traits = getUtility(ITranslationSideTraitsSet).getTraits(
            template.translation_side)

        diverged = suggestion.is_diverged
        used_here = traits.getFlag(suggestion)
        used_on_other_side = traits.other_side_traits.getFlag(suggestion)

        if used_here and suggestion.potemplate == template:
            # The suggestion is already current and diverged for the
            # right template.
            return suggestion

        incumbent = traits.getCurrentMessage(self, template, pofile.language)
        if incumbent is not None:
            # Ensure that the current message hasn't changed from the
            # state the reviewer inspected before making this change.
            self._checkForConflict(incumbent, lock_timestamp)

        if incumbent is not None and incumbent.is_diverged:
            # The incumbent is also diverged, so it's in the way of the
            # suggestion we're trying to diverge.  Disable it.
            traits.setFlag(incumbent, False)
            incumbent.markReviewed(reviewer)
            incumbent.shareIfPossible()
            pofile.markChanged()

        if used_here and not diverged and not used_on_other_side:
            # This message is already the shared current message.  If it
            # was previously masked by a diverged message, it no longer
            # is.  This is probably the behaviour the user would expect.
            return suggestion

        if used_here or used_on_other_side:
            # The suggestion is already current somewhere else.  Can't
            # reuse it as a diverged message in this template, so clone
            # it.
            message = self._cloneAndDiverge(suggestion, pofile)
        else:
            # No obstacles.  Diverge.
            message = suggestion
            message.potemplate = template

        traits.setFlag(message, True)
        message.markReviewed(reviewer)
        pofile.markChanged()
        return message

    def setCurrentTranslation(self, pofile, submitter, translations, origin,
                              share_with_other_side=False,
                              lock_timestamp=None):
        """See `IPOTMsgSet`."""
        potranslations = self._findPOTranslations(translations)
        identical_message = self._findMatchingTranslationMessage(
            pofile, potranslations, prefer_shared=False)
        return self._setTranslation(
            pofile, submitter, origin, potranslations,
            share_with_other_side=share_with_other_side,
            identical_message=identical_message,
            lock_timestamp=lock_timestamp)

    def _setTranslation(self, pofile, submitter, origin, potranslations,
                        identical_message=None, share_with_other_side=False,
                        lock_timestamp=None):
        """Set the current translation.

        https://dev.launchpad.net/Translations/Specs/setCurrentTranslation

        :param pofile: The `POFile` to set the translation in.
        :param submitter: The `Person` who produced this translation.
        :param origin: The translation's `RosettaTranslationOrigin`.
        :param potranslations: List of `POTranslation`s, with a None for
            each untranslated plural-form.
        :param identical_message: The already existing message, if any,
            that's either shared or diverged for `pofile.potemplate`,
            whose translations are identical to the ones we're setting.
        :param share_with_other_side: Propagate this change to the other
            translation side if appropriate.
        :param lock_timestamp: The timestamp of the translation state
            that the change is based on.
        :return: The `TranslationMessage` that is current after
            completion.
        """
        twin = identical_message

        traits = getUtility(ITranslationSideTraitsSet).getTraits(
            pofile.potemplate.translation_side)

        # The current message on this translation side, if any.
        incumbent_message = traits.getCurrentMessage(
            self, pofile.potemplate, pofile.language)

        self._checkForConflict(
            incumbent_message, lock_timestamp, potranslations=potranslations)

        # Summary of the matrix:
        #  * If the incumbent message is diverged and we're setting a
        #    translation that's already shared: converge.
        #  * If the incumbent message is diverged and we're setting a
        #    translation that's not already shared: maintain divergence.
        #  * If the incumbent message is shared, replace it.
        #  * If there is no twin, simply create a new message (shared or
        #    diverged depending; see above).
        #  * If there is a shared twin, activate it (but also diverge if
        #    necessary; see above).
        #  * If there is a diverged twin, activate it (and converge it
        #    if appropriate; see above).
        #  * If there is a twin that's shared on the other side,

        decision_matrix = {
            'incumbent_none': {
                'twin_none': 'Z1*',
                'twin_shared': 'Z4*',
                'twin_diverged': 'Z7*',
                'twin_other_shared': 'Z4',
            },
            'incumbent_shared': {
                'twin_none': 'B1*',
                'twin_shared': 'B4*',
                'twin_diverged': 'B7*',
                'twin_other_shared': 'B4',
            },
            'incumbent_diverged': {
                'twin_none': 'A2',
                'twin_shared': 'A5',
                'twin_diverged': 'A4',
                'twin_other_shared': 'A6',
            },
            'incumbent_other_shared': {
                'twin_none': 'B1+',
                'twin_shared': 'B4+',
                'twin_diverged': 'B7+',
                'twin_other_shared': '',
            },
        }

        incumbent_state = "incumbent_%s" % self._nameMessageStatus(
            incumbent_message, traits)
        twin_state = "twin_%s" % self._nameMessageStatus(twin, traits)

        decisions = decision_matrix[incumbent_state][twin_state]
        assert re.match('[ABZ]?[124567]?[+*]?$', decisions), (
            "Bad decision string.")

        for character in decisions:
            if character == 'A':
                # Deactivate & converge.
                # There may be an identical shared message.
                traits.setFlag(incumbent_message, False)
                incumbent_message.shareIfPossible()
            elif character == 'B':
                # Deactivate.
                traits.setFlag(incumbent_message, False)
            elif character == 'Z':
                # There is no incumbent message, so do nothing to it.
                assert incumbent_message is None, (
                    "Incorrect Z in decision matrix.")
            elif character == '1':
                # Create & activate.
                message = self._makeTranslationMessage(
                    pofile, submitter, potranslations, origin)
            elif character == '2':
                # Create, diverge, activate.
                message = self._makeTranslationMessage(
                    pofile, submitter, potranslations, origin, diverged=True)
            elif character == '4':
                # Activate.
                message = twin
            elif character == '5':
                # If other is a suggestion, diverge and activate.
                # (If not, it's already active and has been unmasked by
                # our deactivating the incumbent).
                message = twin
                if not traits.getFlag(twin):
                    assert not traits.other_side_traits.getFlag(twin), (
                        "Trying to diverge a message that is current on the "
                        "other side.")
                    message.potemplate = pofile.potemplate
            elif character == '6':
                # If other is not active, fork a diverged message.
                if traits.getFlag(twin):
                    message = twin
                else:
                    # The twin is used on the other side, so we can't
                    # just reuse it for our diverged message.  Create a
                    # new one.
                    message = self._makeTranslationMessage(
                        pofile, submitter, potranslations, origin,
                        diverged=True)
            elif character == '7':
                # Converge & activate.
                message = twin
                message.shareIfPossible()
            elif character == '*':
                if share_with_other_side:
                    other_incumbent = (
                        traits.other_side_traits.getCurrentMessage(
                            self, pofile.potemplate, pofile.language))
                    if other_incumbent is None:
                        traits.other_side_traits.setFlag(message, True)
            elif character == '+':
                if share_with_other_side:
                    traits.other_side_traits.setFlag(incumbent_message, False)
                    traits.other_side_traits.setFlag(message, True)
            else:
                raise AssertionError(
                    "Bad character in decision string: %s" % character)

        if decisions == '':
            message = twin

        if not traits.getFlag(message):
            traits.setFlag(message, True)
            pofile.markChanged(translator=submitter)

        return message

    def old_resetCurrentTranslation(self, pofile, lock_timestamp):
        """See `POTMsgSet`.

        This message is OBSOLETE in the Recife feature branch.  It's
        still here only until we replace its one call with the new
        method.
        """
        assert lock_timestamp is not None, "No lock timestamp given."
        current = self.getCurrentTranslationMessage(
            pofile.potemplate, pofile.language)
        if current is None:
            return

        # Check for translation conflicts and update the required
        # attributes.
        self._maybeRaiseTranslationConflict(current, lock_timestamp)
        current.is_current_ubuntu = False
        # Converge the current translation only if it is diverged and
        # not current upstream.
        if current.is_diverged and not current.is_current_upstream:
            current.potemplate = None
        pofile.markChanged()

    def resetCurrentTranslation(self, pofile, lock_timestamp=None,
                                share_with_other_side=False):
        """See `IPOTMsgSet`."""
        traits = getUtility(ITranslationSideTraitsSet).getTraits(
            pofile.potemplate.translation_side)
        current_message = traits.getCurrentMessage(
            self, pofile.potemplate, pofile.language)

        if current_message is None:
            # Nothing to do here.
            return

        self._checkForConflict(current_message, lock_timestamp)
        traits.setFlag(current_message, False)
        if share_with_other_side:
            traits.other_side_traits.setFlag(current_message, False)
        current_message.shareIfPossible()
        pofile.markChanged()

    def clearCurrentTranslation(self, pofile, submitter, origin,
                                share_with_other_side=False,
                                lock_timestamp=None):
        """See `IPOTMsgSet`."""
        message = self.setCurrentTranslation(
            pofile, submitter, {}, origin,
            share_with_other_side=share_with_other_side,
            lock_timestamp=lock_timestamp)
        message.markReviewed(submitter)

    def applySanityFixes(self, text):
        """See `IPOTMsgSet`."""
        if text is None:
            return None

        # Fix the visual point that users copy & paste from the web interface.
        new_text = self.convertDotToSpace(text)
        # Now, fix the newline chars.
        new_text = self.normalizeNewLines(new_text)
        # Finally, set the same whitespaces at the start/end of the string.
        new_text = self.normalizeWhitespaces(new_text)
        # Also, if it's an empty string, replace it with None.
        # XXX CarlosPerelloMarin 2007-11-16: Until we figure out
        # ResettingTranslations
        if new_text == '':
            new_text = None

        return new_text

    def convertDotToSpace(self, text):
        """See IPOTMsgSet."""
        if u'\u2022' in self.singular_text or u'\u2022' not in text:
            return text

        return text.replace(u'\u2022', ' ')

    def normalizeWhitespaces(self, translation_text):
        """See IPOTMsgSet."""
        if translation_text is None:
            return None

        stripped_singular_text = self.singular_text.strip()
        stripped_translation_text = translation_text.strip()
        new_translation_text = None

        if (len(stripped_singular_text) > 0 and
            len(stripped_translation_text) == 0):
            return ''

        if len(stripped_singular_text) != len(self.singular_text):
            # There are whitespaces that we should copy to the 'text'
            # after stripping it.
            prefix = self.singular_text[:-len(self.singular_text.lstrip())]
            postfix = self.singular_text[len(self.singular_text.rstrip()):]
            new_translation_text = '%s%s%s' % (
                prefix, stripped_translation_text, postfix)
        elif len(stripped_translation_text) != len(translation_text):
            # msgid does not have any whitespace, we need to remove
            # the extra ones added to this text.
            new_translation_text = stripped_translation_text
        else:
            # The text is not changed.
            new_translation_text = translation_text

        return new_translation_text

    def normalizeNewLines(self, translation_text):
        """See IPOTMsgSet."""
        # There are three different kinds of newlines:
        windows_style = u'\r\n'
        mac_style = u'\r'
        unix_style = u'\n'
        # We need the stripped variables because a 'windows' style will be at
        # the same time a 'mac' and 'unix' style.
        stripped_translation_text = translation_text.replace(
            windows_style, u'')
        stripped_singular_text = self.singular_text.replace(
            windows_style, u'')

        # Get the style that uses singular_text.
        original_style = None
        if windows_style in self.singular_text:
            original_style = windows_style

        if mac_style in stripped_singular_text:
            if original_style is not None:
                raise BrokenTextError(
                    "original text (%r) mixes different newline markers" %
                        self.singular_text)
            original_style = mac_style

        if unix_style in stripped_singular_text:
            if original_style is not None:
                raise BrokenTextError(
                    "original text (%r) mixes different newline markers" %
                        self.singular_text)
            original_style = unix_style

        # Get the style that uses the given text.
        translation_style = None
        if windows_style in translation_text:
            translation_style = windows_style

        if mac_style in stripped_translation_text:
            if translation_style is not None:
                raise BrokenTextError(
                    "translation text (%r) mixes different newline markers" %
                        translation_text)
            translation_style = mac_style

        if unix_style in stripped_translation_text:
            if translation_style is not None:
                raise BrokenTextError(
                    "translation text (%r) mixes different newline markers" %
                        translation_text)
            translation_style = unix_style

        if original_style is None or translation_style is None:
            # We don't need to do anything, the text is not changed.
            return translation_text

        # Fix the newline chars.
        return translation_text.replace(translation_style, original_style)

    @property
    def hide_translations_from_anonymous(self):
        """See `IPOTMsgSet`."""
        # msgid_singular.msgid is pre-joined everywhere where
        # hide_translations_from_anonymous is used
        return self.is_translation_credit

    @property
    def is_translation_credit(self):
        """See `IPOTMsgSet`."""
        credit_type = self.translation_credits_type
        return credit_type != TranslationCreditsType.NOT_CREDITS

    @property
    def translation_credits_type(self):
        """See `IPOTMsgSet`."""
        if self.msgid_singular.msgid not in credits_message_info:
            return TranslationCreditsType.NOT_CREDITS

        expected_context, credits_type = (
            credits_message_info[self.msgid_singular.msgid])
        if expected_context is None or (self.context == expected_context):
            return credits_type
        return TranslationCreditsType.NOT_CREDITS

    def makeHTMLID(self, suffix=None):
        """See `IPOTMsgSet`."""
        elements = ['msgset', str(self.id)]
        if suffix is not None:
            elements.append(suffix)
        return '_'.join(elements)

    def updatePluralForm(self, plural_form_text):
        """See `IPOTMsgSet`."""
        if plural_form_text is None:
            self.msgid_plural = None
            return
        else:
            # Store the given plural form.
            try:
                pomsgid = POMsgID.byMsgid(plural_form_text)
            except SQLObjectNotFound:
                pomsgid = POMsgID(msgid=plural_form_text)
            self.msgid_plural = pomsgid

    def setTranslationCreditsToTranslated(self, pofile):
        """See `IPOTMsgSet`."""
        if not self.is_translation_credit:
            return

        shared_upstream_translation = self.getSharedTranslation(
            pofile.language, TranslationSide.UPSTREAM)

        if shared_upstream_translation is not None:
            return

        # The credits message has a fixed "translator."
        translator = getUtility(ILaunchpadCelebrities).rosetta_experts

        generated_translation = self.setCurrentTranslation(
            pofile, translator, {0: credits_message_str},
            RosettaTranslationOrigin.LAUNCHPAD_GENERATED,
            share_with_other_side=True)
        generated_translation.shareIfPossible()

    def setSequence(self, potemplate, sequence):
        """See `IPOTMsgSet`."""
        self.sequence = sequence
        translation_template_item = TranslationTemplateItem.selectOneBy(
            potmsgset=self, potemplate=potemplate)
        if translation_template_item is not None:
            # Update the sequence for the translation template item.
            translation_template_item.sequence = sequence
        elif sequence >= 0:
            # Introduce this new entry into the TranslationTemplateItem for
            # later usage.
            conflicts, uses_english_msgids = (
                self._conflictsExistingSourceFileFormats(
                    potemplate.source_file_format))
            if conflicts:
                # We are not allowing POTMsgSets to participate
                # in incompatible POTemplates.  Call-sites should
                # not try to introduce them, or they'll get an exception.
                raise POTMsgSetInIncompatibleTemplatesError(
                    "Attempt to add a POTMsgSet into a POTemplate which "
                    "has a conflicting value for uses_english_msgids.")

            TranslationTemplateItem(
                potemplate=potemplate,
                sequence=sequence,
                potmsgset=self)
        else:
            # There is no entry for this potmsgset in TranslationTemplateItem
            # table, neither we need to create one, given that the sequence is
            # less than zero.
            pass

    def getSequence(self, potemplate):
        """See `IPOTMsgSet`."""
        translation_template_item = TranslationTemplateItem.selectOneBy(
            potmsgset=self, potemplate=potemplate)
        if translation_template_item is not None:
            return translation_template_item.sequence
        else:
            return 0

    def getAllTranslationMessages(self):
        """See `IPOTMsgSet`."""
        return Store.of(self).find(
            TranslationMessage, TranslationMessage.potmsgset == self)

    def getAllTranslationTemplateItems(self):
        """See `IPOTMsgSet`."""
        return TranslationTemplateItem.selectBy(
            potmsgset=self, orderBy=['id'])
