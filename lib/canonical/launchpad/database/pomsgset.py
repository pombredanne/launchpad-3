# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POMsgSet']

import logging

from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, sqlvalues, \
    flush_database_updates
from canonical.launchpad.interfaces import IEditPOMsgSet
from canonical.lp.dbschema import RosettaTranslationOrigin
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.potranslationsighting import \
    POTranslationSighting
from canonical.launchpad.database.potranslation import POTranslation


class POMsgSet(SQLBase):
    implements(IEditPOMsgSet)

    _table = 'POMsgSet'

    sequence = IntCol(dbName='sequence', notNull=True)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile', notNull=True)
    iscomplete = BoolCol(dbName='iscomplete', notNull=True)
    obsolete = BoolCol(dbName='obsolete', notNull=True)
    fuzzy = BoolCol(dbName='fuzzy', notNull=True)
    commenttext = StringCol(dbName='commenttext', notNull=False, default=None)
    potmsgset = ForeignKey(foreignKey='POTMsgSet', dbName='potmsgset',
        notNull=True)

    def pluralforms(self):
        if len(list(self.potmsgset.messageIDs())) > 1:
            # has plurals
            return self.pofile.pluralforms
        else:
            # message set is singular
            return 1

    def translations(self):
        pluralforms = self.pluralforms()
        if pluralforms is None:
            raise RuntimeError(
                "Don't know the number of plural forms for this PO file!")

        results = list(POTranslationSighting.select(
            'pomsgset = %d AND active = TRUE' % self.id,
            orderBy='pluralForm'))

        translations = []

        for form in range(pluralforms):
            if results and results[0].pluralform == form:
                translations.append(results.pop(0).potranslation.translation)
            else:
                translations.append(None)

        return translations

    # XXX: Carlos Perello Marin 15/10/04: Review this method, translations
    # could have more than one row and we always return only the firts one!
    def getTranslationSighting(self, pluralForm, allowOld=False):
        """Return the translation sighting that is committed and has the
        plural form specified."""
        if allowOld:
            translation = POTranslationSighting.selectOneBy(
                pomsgsetID=self.id,
                pluralform=pluralForm)
        else:
            translation = POTranslationSighting.selectOneBy(
                pomsgsetID=self.id,
                inlastrevision=True,
                pluralform=pluralForm)
        if translation is None:
            # XXX: This should be a NotFoundError.
            #      -- SteveAlexander, 2005-04-23
            raise IndexError, pluralForm
        return translation

    def translationSightings(self):
        return POTranslationSighting.selectBy(pomsgsetID=self.id)

    # IEditPOMsgSet

    def updateTranslation(self, person, new_translations, fuzzy, fromPOFile):
        was_complete = self.iscomplete
        was_fuzzy = self.fuzzy
        has_changes = False
        # By default we will think that all translations for this pomsgset
        # where available in last import
        all_in_last_revision = True

        # Get a hold of a list of existing translations for the message set.
        old_translations = self.translations()

        for index in new_translations.keys():
            # For each translation, add it to the database if it is
            # non-null and different to the old one.
            if new_translations[index] != old_translations[index]:
                has_changes = True
                if (new_translations[index] == '' or
                    new_translations[index] is None):
                    # Make all sightings inactive.
                    sightings = POTranslationSighting.select(
                        'pomsgset=%d AND pluralform = %d' % 
                        sqlvalues(self.id, index))
                    for sighting in sightings:
                        sighting.active = False
                    new_translations[index] = None
                    self.iscomplete = False
                else:
                    try:
                        old_sight = self.getTranslationSighting(index)
                    except IndexError:
                        # We don't have a sighting for this string, that means
                        # that either the translation is new or that the old
                        # translation does not comes from the pofile.
                        all_in_last_revision = False
                    else:
                        if not old_sight.active:
                            all_in_last_revision = False
                    self.makeTranslationSighting(
                        person = person,
                        text = new_translations[index],
                        pluralForm = index,
                        fromPOFile = fromPOFile)

        # We set the fuzzy flag as needed:
        if fuzzy and self.fuzzy == False:
            self.fuzzy = True
            has_changes = True
        elif not fuzzy and self.fuzzy == True:
            self.fuzzy = False
            has_changes = True

        if not has_changes:
            # We don't change the statistics if we didn't had any change.
            return

        # We do now a live update of the statistics.
        if self.iscomplete and not self.fuzzy:
            # New msgset translation is ready to be used.
            if not was_complete or was_fuzzy:
                # It was not ready before this change.
                if fromPOFile:
                    # The change was done outside Rosetta.
                    self.pofile.currentcount += 1
                else:
                    # The change was done with Rosetta.
                    self.pofile.rosettacount += 1
            elif not fromPOFile and all_in_last_revision:
                # We have updated a translation from Rosetta that was
                # already translated.
                self.pofile.updatescount += 1
        else:
            # This new msgset translation is not yet finished.
            if was_complete and not was_fuzzy:
                # But previously it was finished, so we lost its translation.
                if fromPOFile:
                    # It was lost outside Rosetta
                    self.pofile.currentcount -= 1
                else:
                    # It was lost inside Rosetta
                    self.pofile.rosettacount -= 1

        # XXX: Carlos Perello Marin 10/12/2004 Sanity test, the statistics
        # code is not as good as it should, we can get negative numbers, in
        # case we reach that status, we just change that field to 0.
        if self.pofile.currentcount < 0:
            self.pofile.currentcount = 0
        if self.pofile.rosettacount < 0:
            self.pofile.rosettacount = 0

    def makeTranslationSighting(self, person, text, pluralForm,
        fromPOFile=False):
        """Create a new translation sighting for this message set."""

        # First get hold of a POTranslation for the specified text.
        try:
            translation = POTranslation.byTranslation(text)
        except SQLObjectNotFound:
            translation = POTranslation(translation=text)

        # Now get hold of any existing translation sightings.

        sighting = POTranslationSighting.selectOneBy(
            pomsgsetID=self.id,
            potranslationID=translation.id,
            pluralform=pluralForm,
            personID=person.id)

        if sighting is None:
            # No sighting exists yet.

            if fromPOFile:
                origin = RosettaTranslationOrigin.SCM
            else:
                origin = RosettaTranslationOrigin.ROSETTAWEB

            sighting = POTranslationSighting(
                pomsgsetID=self.id,
                potranslationID=translation.id,
                datefirstseen=UTC_NOW,
                datelastactive=UTC_NOW,
                inlastrevision=fromPOFile,
                pluralform=pluralForm,
                active=False,
                personID=person.id,
                origin=origin)

        if not fromPOFile:
            # The translation comes from Rosetta, it has preference always.
            sighting.set(datelastactive=UTC_NOW, active=True)
            new_active = sighting
        else:
            # The translation comes from a PO import.

            # Look for the active TranslationSighting
            active_results = POTranslationSighting.selectOneBy(
                pomsgsetID=self.id,
                pluralform=pluralForm,
                active=True)
            if active_results is None:
                # Don't have yet an active translation, mark this one as
                # active and present in last PO.
                sighting.datelastactive = UTC_NOW
                sighting.active = True
                sighting.inlastrevision = True
                new_active = sighting
            else:
                old_active = active_results

                if old_active is sighting:
                    # Current sighting is already active, only update the
                    # timestamp and mark it as present in last import.
                    sighting.datelastactive = UTC_NOW
                    sighting.inlastrevision = True
                    new_active = sighting
                elif old_active.origin == RosettaTranslationOrigin.SCM:
                    # The current active translation is from a previous
                    # .po import so we can override it directly.
                    sighting.datelastactive = UTC_NOW
                    sighting.inlastrevision = True
                    sighting.active = True
                    new_active = sighting
                else:
                    # The current active translation is from Rosetta, we don't
                    # remove it, just mark this sighting as present in last
                    # .po import.
                    sighting.inlastrevision = True
                    previous_active_results = POTranslationSighting.select(
                        'pomsgset=%d AND pluralform=%d AND active=FALSE'
                            % sqlvalues(self.id, pluralForm),
                        orderBy='-datelastactive')
                    if (previous_active_results.count() > 1 and
                        previous_active_results[0] is not sighting):
                        # As we have more than one active row, there is an
                        # old translation that is not this one, and therefore,
                        # we get it as an update done outside Rosetta that we
                        # should accept.
                        sighting.active = True
                        sighting.datelastactive = UTC_NOW
                        new_active = sighting
                    else:
                        # We don't have an old translation there or it's the
                        # same we had so we should not kill Rosetta's one.
                        new_active = old_active

        # Make all other sightings inactive.

        sightings = POTranslationSighting.select(
            'pomsgset=%d AND pluralform = %d AND id <> %d'
            % (self.id, pluralForm, new_active.id))

        # In theory we should only get one resultset.
        if sightings.count() > 1:
            logging.warning("Got more than one POTranslationSighting row"
                            " for pomsgset = %d, pluralform = %d and"
                            " id <> %d. It must be <= 1 always"
                                % (self.id, pluralForm, new_active.id)
                           )

        for old_sighting in sightings:
            old_sighting.active = False

        # Ask for a sqlobject sync before reusing the data we just updated.
        flush_database_updates()

        # Implicit set of iscomplete. If we have all translations, it's 
        # complete, if we lack a translation, it's not complete.
        if None in self.translations():
            self.iscomplete = False
        else:
            self.iscomplete = True

        return sighting

