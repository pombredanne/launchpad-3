# Copyright 2005-2008 Canonical Ltd.  All rights reserved.

"""Browser views for ITranslationImportQueue."""

__metaclass__ = type

__all__ = [
    'TranslationImportQueueEntryNavigation',
    'TranslationImportQueueEntryView',
    'TranslationImportQueueNavigation',
    'TranslationImportQueueView',
    ]

import os
from os.path import basename, splitext
from zope.app.form.interfaces import ConversionError
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
    NotFoundError, RosettaImportStatus, UnexpectedFormData,
    TranslationFileType)
from canonical.launchpad.webapp import (
    action, canonical_url, GetitemNavigation, LaunchpadFormView)


class TranslationImportQueueEntryNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueueEntry


class TranslationImportQueueEntryView(LaunchpadFormView):
    """The view part of admin interface for the translation import queue."""
    label = "Review import queue entry"
    schema = IEditTranslationImportQueueEntry

    @property
    def initial_values(self):
        """Initialize some values on the form, when it's possible."""
        field_values = {}
        if self.request.method == 'POST':
            # We got a form post, we don't need to do any initialisation.
            return field_values
        # Fill the know values.
        field_values['path'] = self.context.path
        (fname, fext) = splitext(self.context.path)
        if fext.lower() == '.po':
            file_type = TranslationFileType.PO
        elif fext.lower() == '.pot':
            file_type = TranslationFileType.POT
        else:
            file_type = TranslationFileType.UNSPEC
        field_values['file_type'] = file_type

        if self.context.sourcepackagename is not None:
            field_values['sourcepackagename'] = self.context.sourcepackagename
        if( file_type in (TranslationFileType.POT,
                          TranslationFileType.UNSPEC) and
                          self.context.potemplate is not None):
            field_values['name'] = (
                self.context.potemplate.name)
            field_values['translation_domain'] = (
                self.context.potemplate.translation_domain)
        if file_type in (TranslationFileType.PO, TranslationFileType.UNSPEC):
            field_values['potemplate'] = self.context.potemplate
            if self.context.pofile is not None:
                field_values['language'] = self.context.pofile.language
                field_values['variant'] = self.context.pofile.variant
            else:
                # The entries that are translations usually have the language
                # code
                # as its filename. We try to get it to use as a suggestion.
                language_set = getUtility(ILanguageSet)
                filename = os.path.basename(self.context.path)
                guessed_language, file_ext = filename.split(u'.', 1)
                (language, variant) = (
                    language_set.getLanguageAndVariantFromString(
                        guessed_language))
                if language is not None:
                    field_values['language'] = language
                    # Need to warn the user that we guessed the language
                    # information.
                    self.request.response.addWarningNotification(
                        "Review the language selection as we guessed it and"
                        " could not be accurate.")
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
        self.field_names = ['file_type', 'path', 'sourcepackagename',
                            'name', 'translation_domain',
                            'potemplate', 'potemplate_name',
                            'language', 'variant']

        if self.context.productseries is not None:
            # We are handling an entry for a productseries, this field is not
            # useful here.
            self.field_names.remove('sourcepackagename')

        # Execute default initialisation.
        LaunchpadFormView.initialize(self)

    def _checkProductOrPackage(self, obj):
        """Check if the given object is linked to the same productseries
        or sourcepackage as the context.

        :param obj: The object to check, must have productseries,
            distroseries and sourcepackagename attributes.
        :return: true if object and context match.
        """
        try:
            if self.context.productseries != None:
                return obj.productseries == self.context.productseries
            if self.context.distroseries != None:
                return (
                    obj.distroseries == self.context.distroseries and
                    obj.sourcepackagename == self.context.sourcepackagename)
        except AttributeError:
            pass  # return False
        return False

    def _getPOTemplateSubset(self, sourcepackagename):
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
        return potemplate_subset

    def validate(self, data):
        """Extra validations for the given fields."""
        # Without a file type we cannot do anything
        file_type = data.get('file_type')
        if file_type not in (TranslationFileType.PO,
                             TranslationFileType.POT):
            self.setFieldError('file_type', 'Please specify the file type')
            return

        path = data.get('path')
        if path == None or path.strip() == "":
            self.setFieldError('path', 'The file name is missing.')
        else:
            (fname, fext) = splitext(basename(path))
            if len(fname) == 0:
                self.setFieldError('path',
                                   'The file name is incomplete.')
            if (file_type == TranslationFileType.POT and
                    fext.lower() != '.pot' and fext.lower() != '.xpi'):
                self.setFieldError('path',
                                   'The file name must end with ".pot".')
            if (file_type == TranslationFileType.PO and
                    fext.lower() != '.po' and fext.lower() != '.xpi'):
                self.setFieldError('path',
                                   'The file name must end with ".po".')

            if self.context.path != path:
                # The Rosetta Expert decided to change the path of the file.
                # Before accepting such change, we should check first whether is
                # already another entry with that path in the same context
                # (sourcepackagename/distroseries or productseries).
                if file_type == TranslationFileType.POT:
                    potemplate_set = getUtility(IPOTemplateSet)
                    existing_file = potemplate_set.getPOTemplateByPathAndOrigin(
                        path, self.context.productseries,
                        self.context.distroseries,
                        self.context.sourcepackagename)
                else:
                    pofile_set = getUtility(IPOFileSet)
                    existing_file = pofile_set.getPOFileByPathAndOrigin(
                        path, self.context.productseries,
                        self.context.distroseries,
                        self.context.sourcepackagename)
                if existing_file is None:
                    # There is no other pofile in the given path for this context,
                    # let's change it as requested by admins.
                    self.context.path = path
                else:
                    # We already have an IPOFile in this path, let's notify the
                    # user about that so they choose another path.
                    self.setFieldError('path',
                        'There is already a file in the given path.')

        if file_type == TranslationFileType.POT:
            name = data.get('name')
            translation_domain = data.get('translation_domain')
            if name is None:
                self.setFieldError('name', 'Please specify a name for '
                                   'the template.')
            if translation_domain is None:
                self.setFieldError('translation_domain', 'Please specify a '
                                   'translation domain for the template.')
        if file_type == TranslationFileType.PO:
            potemplate_name = data.get('potemplate_name')
            self.man_potemplate = None
            if potemplate_name == None:
                potemplate = data.get('potemplate')
                if not self._checkProductOrPackage(potemplate):
                    self.setFieldError(
                        'potemplate', 'Please choose a template.')
            else:
                sourcepackagename = data.get('sourcepackagename')
                potemplate_subset = (
                    self._getPOTemplateSubset(sourcepackagename))
                try:
                    self.man_potemplate = potemplate_subset[potemplate_name]
                except NotFoundError:
                    self.setFieldError('potemplate_name',
                        'Please enter a valid template name '
                        'or choose from the list above.')

    @action("Approve")
    def change_action(self, action, data):
        """Process the form we got from the submission."""
        file_type = data.get('file_type')
        name = data.get('name')
        translation_domain = data.get('translation_domain')
        path = data.get('path')
        sourcepackagename = data.get('sourcepackagename')
        potemplate = data.get('potemplate')
        language = data.get('language')
        variant = data.get('variant')

        if file_type == TranslationFileType.PO:
            # We are hadling an IPOFile import.

            # Use manual potemplate, if given.
            # man_potemplate is set in validate().
            if self.man_potemplate != None:
               potemplate = self.man_potemplate

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
                pofile.setPathIfUnique(path)
            elif self.context.is_published:
                # This entry comes from upstream, which means that the path we
                # got is exactly the right one. If it's different from what
                # pofile has, that would mean that either the entry changed
                # its path since previous upload or that we had to guess it
                # and now that we got the right path, we should fix it.
                pofile.setPathIfUnique(self.context.path)
            else:
                # Leave path unchanged.
                pass

        
        if file_type == TranslationFileType.POT:
            # We are importing an IPOTemplate file.

            # Create a new potemplate if this template name
            # does not yet appear in this subset.
            potemplate_subset = self._getPOTemplateSubset(sourcepackagename)
            try:
                potemplate = potemplate_subset[name]
            except NotFoundError:
                potemplate = potemplate_subset.new(
                    name,
                    translation_domain,
                    self.context.path,
                    self.context.importer)

            if (self.context.sourcepackagename is not None and
                potemplate.sourcepackagename is not None and
                self.context.sourcepackagename != potemplate.sourcepackagename
                ):
                # We got the template from a different package than the one
                # selected by the user where the import should done, so we
                # note it here.
                potemplate.from_sourcepackagename = (
                    self.context.sourcepackagename)


        # Store the associated IPOTemplate.
        self.context.potemplate = potemplate

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
        target_filter = self.widgets['filter_target']
        if target_filter.hasInput() and not target_filter.hasValidInput():
            raise UnexpectedFormData("Unknown target.")

    @property
    def entries(self):
        """Return the entries in the queue for this context."""
        target, file_extension, import_status = (
            self.getEntriesFilteringOptions())
        if file_extension is None:
            extensions = None
        else:
            extensions = [file_extension]

        return self.context.getAllEntries(
                target=target, import_status=import_status,
                file_extensions=extensions)

    def createFilterTargetField(self):
        """Create a field with a vocabulary to filter by target.

        :return: A form.Fields instance containing the target field.
        """
        return self.createFilterFieldHelper(
            name='filter_target',
            source=TranslationImportTargetVocabularyFactory(self),
            title='Choose which target to show')


class TranslationImportTargetVocabularyFactory:
    """Factory for a vocabulary containing a list of targets."""

    implements(IContextSourceBinder)

    def __init__(self, view):
        """Create a `TranslationImportTargetVocabularyFactory`.

        :param view: The view that called this factory.  We access its
            filter_status widget later to see which status it filters for.
        """
        self.view = view

    def __call__(self, context):
        import_queue = getUtility(ITranslationImportQueue)
        targets = import_queue.getRequestTargets()
        filtered_targets = set()

        # Read filter_status, in order to mark targets that have requests with
        # that status pending.  This works because we set up the filter_status
        # widget before the filter_target one, which uses this vocabulary
        # factory.
        status_widget = self.view.widgets['filter_status']
        if status_widget.hasInput():
            try:
                status_filter = status_widget.getInputValue()
            except ConversionError:
                raise UnexpectedFormData("Invalid status parameter.")
            if status_filter != 'all':
                try:
                    status = RosettaImportStatus.items[status_filter]
                    filtered_targets = set(
                        import_queue.getRequestTargets(status))
                except LookupError:
                    # Unknown status.  Ignore.
                    pass

        terms = [SimpleTerm('all', 'all', 'All targets')]
        for target in targets:
            if IDistroSeries.providedBy(target):
                # Distroseries are not pillar names, we need to note
                # distribution.name/distroseries.name
                term_name = '%s/%s' % (target.distribution.name, target.name)
            else:
                term_name = target.name

            displayname = target.displayname
            if target in filtered_targets:
                displayname += '*'

            terms.append(SimpleTerm(term_name, term_name, displayname))
        return SimpleVocabulary(terms)
