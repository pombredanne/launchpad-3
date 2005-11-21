# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for ITranslationImportQueue."""

__metaclass__ = type

__all__ = [
    'TranslationImportQueueNavigation',
    'TranslationImportQueueURL',
    'TranslationImportQueueView',
    'TranslationImportQueueSetContextMenu',
    'TranslationImportQueueSetNavigation',
    'TranslationImportQueueSetView',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationImportQueue, ITranslationImportQueueSet, ICanonicalUrlData,
    ILaunchpadCelebrities, ITranslationImportQueueEdition, IPOTemplateSet,
    IRawFileData, RawFileBusy, NotFoundError)
from canonical.launchpad.webapp import (
    GetitemNavigation, LaunchpadView, ContextMenu, Link, canonical_url)
from canonical.launchpad.webapp.generalform import GeneralFormView


class TranslationImportQueueNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueue


class TranslationImportQueueURL:
    implements(ICanonicalUrlData)

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        translation_import_queue  = self.context
        return str(translation_import_queue.id)

    @property
    def inside(self):
        return getUtility(ITranslationImportQueueSet)


class TranslationImportQueueView(GeneralFormView):
    """The view part of the admin interface for the translation import queue.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.initialize()
        GeneralFormView.__init__(self, context, request)

    def initialize(self):
        """Set the fields that will be showed based on the 'context' values.

        If the context comes from a productseries, the sourcepackagename
        chooser is hidden.
        If the 'context.path' field ends with the string '.pot', it notes that
        the context is related with a '.pot' file, so we hide the language and
        variant fields as are useless here.
        """
        self.fieldNames = ['sourcepackagename', 'potemplatename', 'path',
            'language', 'variant']

        if (self.context.productseries is not None and
            'sourcepackagename' in self.fieldNames):
            self.fieldNames.remove('sourcepackagename')

        if self.context.path.endswith('.pot'):
            if 'language' in self.fieldNames:
                self.fieldNames.remove('language')
            if 'variant' in self.fieldNames:
                self.fieldNames.remove('variant')

    def process(self, potemplatename, path=None, sourcepackagename=None,
        language=None, variant=None):
        """Process the form we got from the submission."""
        translationimportqueue_set = getUtility(ITranslationImportQueueSet)

        if path and self.context.path != path:
            # The Rosetta Expert decided to change the path of the file.
            self.context.path = path

        if (sourcepackagename is not None and
            self.context.sourcepackagename is not None):
            # Got another sourcepackagename from the form, we will use it.
            destination_sourcepackagename = sourcepackagename
        else:
            destination_sourcepackagename = self.context.sourcepackagename

        potemplate_set = getUtility(IPOTemplateSet)
        potemplate_subset = potemplate_set.getSubset(
                productseries=self.context.productseries,
                distrorelease=self.context.distrorelease,
                sourcepackagename=destination_sourcepackagename)
        try:
            potemplate = potemplate_subset[potemplatename.name]
        except NotFoundError:
            # The POTemplate does not exist. In this case we don't care if
            # the file is a .pot or a .po file, we can use either as the base
            # template.
            potemplate = potemplate_subset.new(
                potemplatename,
                self.context.getFileContent(),
                self.context.importer)

            # Point to the right path.
            potemplate.path = self.context.path
            # Set the real import date.
            IRawFileData(potemplate).daterawimport = self.context.dateimported

            if language is None:
                # We can remove the element from the queue as it was a direct
                # import into an IPOTemplate.
                translationimportqueue_set.remove(self.context.id)
                return 'You associated the queue item with a PO Template.'

        if language is None:
            try:
                self.context.attachToPOFileOrPOTemplate(potemplate)
            except RawFileBusy:
                # There is already one file waiting for being imported, we add
                # a link to the IPOTemplate and wait for it.
                self.context.potemplate = potemplate
        else:
            # We are hadling an IPOFile import.
            pofile = potemplate.getOrCreatePOFile(language.code, variant,
                self.context.importer)
            try:
                self.context.attachToPOFileOrPOTemplate(pofile)
            except RawFileBusy:
                # There is already one file waiting for being imported, we add
                # a link to the IPOFile and wait for it.
                self.context.pofile = pofile

        return 'You associated the queue item with a PO File.'

    def nextURL(self):
        """Return the URL of the main import queue at 'rosetta/imports'."""
        translationimportqueue_set = getUtility(ITranslationImportQueueSet)
        return canonical_url(translationimportqueue_set)


class TranslationImportQueueSetNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueueSet


class TranslationImportQueueSetContextMenu(ContextMenu):
    usedfor = ITranslationImportQueueSet
    links = ['overview', 'blocked']

    def overview(self):
        target = ''
        text = 'Import queue'
        return Link(target, text)

    def blocked(self):
        target = '+blocked'
        text = 'Blocked items'
        return Link(target, text)


class TranslationImportQueueSetView(LaunchpadView):
    """View class used for Translation Import Queue management."""

    def initialize(self):
        """Useful initialization for this view class."""
        self.alerts = []
        self.notices = []
        self.form = self.request.form

        # Process the form.
        self.processForm()

    @property
    def has_things_to_import(self):
        """Return whether there are things ready to import or not."""
        for entry in self.context.getEntries():
            if entry.import_into is not None:
                return True
        return False

    @property
    def has_pending_reviews(self):
        """Return whether there are things pending to review or not."""
        for entry in self.context.getEntries():
            if entry.import_into is None:
                return True
        return False

    def readyToImport(self):
        """Iterate the entries that can be imported directly."""
        for entry in self.context.getEntries():
            if entry.import_into is not None:
                yield entry

    def pendingReview(self):
        """Iterate the entries that need manually review."""
        for entry in self.context.getEntries():
            if entry.import_into is None:
                yield entry

    def processForm(self):
        """Block or remove entries from the queue based on the selection of
        the form.
        """
        if self.request.method != 'POST' or self.user is None:
            # The form was not submitted or the user is not logged in.
            return

        self.form_entries = []

        for item in self.form:
            if item.startswith('entry-'):
                # It's an item to remove
                try:
                    common, id_string = item.split('-')
                    # The id is an integer
                    id = int(id_string)
                except ValueError:
                    # We got an item with more than one '-' char or with an id
                    # that is not a number, that means that someone is playing
                    # badly with our system so it's safe to just ignore the
                    # request.
                    raise AssertionError(
                        'Ignored your request because is broken.')
                self.form_entries.append(id)

        dispatch_table = {
            'remove_import': self.remove,
            'block_import': self.block,
            'remove_review': self.remove,
            'block_review': self.block,
            'remove_blocked': self.remove,
            'unblock': self.unblock
            }
        dispatch_to = [(key, method)
                        for key, method in dispatch_table
                        if key in self.form
                      ]
        if len(dispatch_to) != 1:
            raise AssertionError(
                "There should be only one command in the form",
                dispatch_to)
        key, method = dispatch_to[0]
        method()

    def remove(self):
        """Handle a form submission to remove items ready to be imported.

        It expects the list of items ids at self.form_entries
        """
        # The user must be logged in.
        assert self.user is not None

        removed = 0
        for id in self.form_entries:
            entry = self.context.get(id)
            if self.user.inTeam(entry.importer):
                # Do the removal.
                self.context.remove(id)
                removed += 1
            else:
                # The user was not the importer and that means that is a
                # broken request.
                raise AssertionError(
                    'Ignored your request to remove some items, because'
                    'they are not yours.')

        # Notifications.
        if removed == 1:
            self.notices.append('Removed %d item.' % removed)
        elif removed > 1:
            self.notices.append('Removed %d items.' % removed)

    def block(self):
        """Handle a form submission to block items to be imported.

        It expects the list of items ids at self.form_entries
        """
        blocked = 0
        for item in self.form_entries:
            celebrities = getUtility(ILaunchpadCelebrities)
            # Only admins or Rosetta experts will be able to block
            # imports:
            if (self.user.inTeam(celebrities.admin) or
                self.user.inTeam(celebrities.rosetta_expert)):
                # Block it.
                entry = self.context.get(id)
                entry.block()
                blocked += 1
            else:
                # The user does not have the needed permissions to do
                # this.
                raise AssertionError(
                    'Ignored your request to block some items, because'
                    'they are not yours.')

        # Notifications.
        if blocked == 1:
            self.notices.append('Blocked %d item.' % blocked)
        elif blocked > 1:
            self.notices.append('Blocked %d items.' % blocked)

    def unblock(self):
        """Handle a form submission to unblock items to be imported.

        It expects the list of items ids at self.form_entries
        """
        unblocked = 0
        for item in self.form_entries:
            celebrities = getUtility(ILaunchpadCelebrities)
            # Only admins or Rosetta experts will be able to unblock
            # imports:
            if (self.user.inTeam(celebrities.admin) or
                self.user.inTeam(celebrities.rosetta_expert)):
                # Unblock it.
                entry = self.context.get(id)
                entry.block(False)
                unblocked += 1
            else:
                # The user does not have the needed permissions to do
                # this.
                raise AssertionError(
                    'Ignored your request to block some items, because'
                    'they are not yours.')

        # Notifications.
        if unblocked == 1:
            self.notices.append('Unblocked %d item.' % unblocked)
        elif unblocked > 1:
            self.notices.append('Unblocked %d items.' % unblocked)
