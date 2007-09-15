# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""Browser views for ITranslationImportQueue."""

__metaclass__ = type

__all__ = [
    'TranslationImportQueueEntryNavigation',
    'TranslationImportQueueEntryView',
    'TranslationImportQueueNavigation',
    'TranslationImportQueueView',
    ]

import os
from zope.component import getUtility
from zope.interface import implements
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.database.constants import UTC_NOW
from canonical.launchpad.browser.hastranslationimports import (
    HasTranslationImportsView)
from canonical.launchpad.interfaces import (
    IDistroSeries, IEditTranslationImportQueueEntry, ILanguageSet, IPOFileSet,
    IPOTemplateSet, ITranslationImportQueue, ITranslationImportQueueEntry,
    NotFoundError)
from canonical.launchpad.webapp import (
    GetitemNavigation, canonical_url, LaunchpadFormView, action
    )
from canonical.lp.dbschema import RosettaImportStatus

class TranslationImportQueueEntryNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueueEntry


class TranslationImportQueueEntryView(LaunchpadFormView):
    """The view part of admin interface for the translation import queue."""
    label = "Select where this entry should be attached"
    schema = IEditTranslationImportQueueEntry

    @property
    def initial_values(self):
        """Initialize some values on the form, when it's possible."""
        field_values = {}
        if self.request.method == 'POST':
            # We got a form post, we don't need to do any initialisation.
            return field_values
        # Fill the know values.
        if self.context.sourcepackagename is not None:
            field_values['sourcepackagename'] = self.context.sourcepackagename
        if self.context.potemplate is not None:
            field_values['potemplatename'] = (
                self.context.potemplate.potemplatename.name)
        if self.context.pofile is not None:
            field_values['language'] = self.context.pofile.language
            field_values['variant'] = self.context.pofile.variant
        else:
            # The entries that are translations usually have the language code
            # as its filename. We try to get it to use as a suggestion.
            language_set = getUtility(ILanguageSet)
            filename = os.path.basename(self.context.path)
            guessed_language, file_ext = filename.split(u'.', 1)
            (language, variant) = (
                language_set.getLanguageAndVariantFromString(guessed_language))
            if language is not None:
                field_values['language'] = language
                # Need to warn the user that we guessed the language
                # information.
                self.request.response.addWarningNotification(
                    "Review the language selection as we guessed it and"
                    " could not be accurated.")
            if variant is not None:
                field_values['variant'] = variant

        return field_values

    @property
    def next_url(self):
        """Return the URL of the main import queue at 'rosetta/imports'."""
        translationimportqueue_set = getUtility(ITranslationImportQueue)
        return canonical_url(translationimportqueue_set)

    def initialize(self):
        """Remove some fields based on the entry handled."""
        self.field_names = ['sourcepackagename', 'potemplatename', 'path',
                            'language', 'variant']

        if self.context.productseries is not None:
            # We are handling an entry for a productseries, this field is not
            # useful here.
            self.field_names.remove('sourcepackagename')

        # Execute default initialisation.
        LaunchpadFormView.initialize(self)

    def validate(self, data):
        """Extra validations for the given fields."""
        path = data.get('path')
        if path is not None and self.context.path != path:
            # The Rosetta Expert decided to change the path of the file.
            # Before accepting such change, we should check first whether is
            # already another entry with that path in the same context
            # (sourcepackagename/distroseries or productseries).
            pofile_set = getUtility(IPOFileSet)
            existing_pofile = pofile_set.getPOFileByPathAndOrigin(
                path, self.context.productseries, self.context.distroseries,
                self.context.sourcepackagename)
            if existing_pofile is None:
                # There is no other pofile in the given path for this context,
                # let's change it as requested by admins.
                self.context.path = path
            else:
                # We already have an IPOFile in this path, let's notify the
                # user about that so they choose another path.
                self.setFieldError('path',
                    'There is already a POFile in the given path.')

    @action("Attach")
    def change_action(self, action, data):
        """Process the form we got from the submission."""
        potemplatename = data.get('potemplatename')
        path = data.get('path')
        sourcepackagename = data.get('sourcepackagename')
        language = data.get('language')
        variant = data.get('variant')

        potemplate_set = getUtility(IPOTemplateSet)
        if self.context.productseries is None:
            if (sourcepackagename is not None and
                self.context.sourcepackagename is not None and
                sourcepackagename.id != self.context.sourcepackagename.id):
                # Got another sourcepackagename from the form, we will use it.
                potemplate_subset = potemplate_set.getSubset(
                    distroseries=self.context.distroseries,
                    sourcepackagename=sourcepackagename)
            else:
                potemplate_subset = potemplate_set.getSubset(
                    distroseries=self.context.distroseries,
                    sourcepackagename=self.context.sourcepackagename)
        else:
            potemplate_subset = potemplate_set.getSubset(
                productseries=self.context.productseries)
        try:
            potemplate = potemplate_subset[potemplatename.name]
        except NotFoundError:
            potemplate = potemplate_subset.new(
                potemplatename,
                self.context.path,
                self.context.importer)

        # Store the associated IPOTemplate.
        self.context.potemplate = potemplate

        if language is None:
            # We are importing an IPOTemplate file.
            if (self.context.sourcepackagename is not None and
                potemplate.sourcepackagename is not None and
                self.context.sourcepackagename != potemplate.sourcepackagename
                ):
                # We got the template from a different package than the one
                # selected by the user where the import should done, so we
                # note it here.
                potemplate.from_sourcepackagename = (
                    self.context.sourcepackagename)
        else:
            # We are hadling an IPOFile import.
            pofile = potemplate.getPOFileByLang(language.code, variant)
            if pofile is None:
                # We don't have such IPOFile, we need to create it.
                pofile = potemplate.newPOFile(
                    language.code, variant, self.context.importer)
            self.context.pofile = pofile
            if (self.context.sourcepackagename is not None and
                potemplate.sourcepackagename is not None and
                self.context.sourcepackagename.id !=
                pofile.potemplate.sourcepackagename.id):
                # We got the template from a different package than the one
                # selected by the user where the import should done, so we
                # note it here.
                pofile.from_sourcepackagename = self.context.sourcepackagename

            if path is not None:
                # We got a path to store as the new one for the POFile.
                pofile.path = path
            elif (self.context.is_published and
                  pofile.path != self.context.path):
                # This entry comes from upstream, which means that the path we
                # got is exactly the right one. If it's different from what
                # pofile has, that would mean that either the entry changed
                # its path since previous upload or that we had to guess it
                # and now that we got the right path, we should fix it.
                pofile.path = self.context.path

        self.context.status = RosettaImportStatus.APPROVED
        self.context.date_status_changed = UTC_NOW


class TranslationImportQueueNavigation(GetitemNavigation):
    usedfor = ITranslationImportQueue


class TranslationImportQueueView(HasTranslationImportsView):
    """View class used for Translation Import Queue management."""
    label = 'Translation files waiting to be imported.'

    def initialize(self):
        """Useful initialization for this view class."""
        self._initial_values = {}
        LaunchpadFormView.initialize(self)

    @property
    def entries(self):
        """Return the entries in the queue for this context."""
        target, file_extension, import_status = (
            self.getEntriesFilteringOptions())

        return self.context.getAllEntries(
                target=target, import_status=import_status,
                file_extension=file_extension)

    def createFilterTargetField(self):
        """Create a field with a vocabulary to filter by target.

        :return: A form.Fields instance containing the target field.
        """
        return self.createFilterFieldHelper(
            name='filter_target',
            source=TranslationImportTargetVocabularyFactory(),
            title='Choose which target to show')


class TranslationImportTargetVocabularyFactory:
    """Factory for a vocabulary containing a list of targets."""

    implements(IContextSourceBinder)

    def __call__(self, context):
        translation_import_queue = getUtility(ITranslationImportQueue)
        targets = translation_import_queue.getPillarObjectsWithImports()

        terms = [SimpleTerm('all', 'all', 'All targets')]
        for target in targets:
            if IDistroSeries.providedBy(target):
                # Distroseries are not pillar names, we need to note
                # distribution.name/distroseries.name
                term_name = '%s/%s' % (target.distribution.name, target.name)
            else:
                term_name = target.name
            terms.append(SimpleTerm(term_name, term_name, target.displayname))
        return SimpleVocabulary(terms)
