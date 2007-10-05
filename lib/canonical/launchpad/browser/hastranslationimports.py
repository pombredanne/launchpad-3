# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""Browser view for IHasTranslationImports."""

__metaclass__ = type

__all__ = [
    'HasTranslationImportsView',
    ]

import datetime
import pytz
from zope.app.form.browser import DropdownWidget
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility
from zope.formlib import form
from zope.interface import implements
from zope.schema import Choice
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IDistribution, IHasTranslationImports, IPillarNameSet,
    ITranslationImportQueue, RosettaImportStatus, UnexpectedFormData)
from canonical.launchpad.webapp import (
    LaunchpadFormView, action, custom_widget, safe_action)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import TableBatchNavigator


class HasTranslationImportsView(LaunchpadFormView):
    """View class used for objects with translation imports."""
    schema = IHasTranslationImports
    field_names = []

    custom_widget('filter_target', DropdownWidget, cssClass='inlined-widget')
    custom_widget('filter_status', DropdownWidget, cssClass='inlined-widget')
    custom_widget(
        'filter_extension', DropdownWidget, cssClass='inlined-widget')
    custom_widget('status', DropdownWidget, cssClass='inlined-widget')

    translation_import_queue_macros = ViewPageTemplateFile(
        '../templates/translation-import-queue-macros.pt')

    @property
    def initial_values(self):
        return self._initial_values

    def initialize(self):
        """Set form label depending on the context."""
        self.label = 'Translation files waiting to be imported for %s' % (
            self.context.displayname)
        self._initial_values = {}
        LaunchpadFormView.initialize(self)

    def createFilterFieldHelper(self, name, source, title):
        """A helper method for creating filter fields."""
        self._initial_values[name] = 'all'
        return form.Fields(
            Choice(
                __name__=name,
                source=source,
                title=_(title)),
            custom_widget=self.custom_widgets[name],
            render_context=self.render_context)

    def createFilterStatusField(self):
        """Create a field with a vocabulary to filter by import status.

        :return: A form.Fields instance containing the status field.
        """
        return self.createFilterFieldHelper(
            name='filter_status',
            source=TranslationImportStatusVocabularyFactory(),
            title='Choose which status to show')

    def createFilterFileExtensionField(self):
        """Create a field with a vocabulary to filter by file extension.

        :return: A form.Fields instance containing the file extension field.
        """
        return self.createFilterFieldHelper(
            name='filter_extension',
            source=TranslationImportFileExtensionVocabularyFactory(),
            title='Show entries with this extension')

    def createFilterTargetField(self):
        """Create a field with a vocabulary to filter by target.

        By default this does nothing. Subclasses can override this.

        :return: A form.Fields instance containing the target field or None.
        """
        return None

    def createEntryStatusField(self, entry):
        """Create a field with a vocabulary with entry's import status.

        :return: A form.Fields instance containing the status field.
        """
        name = 'status_%d' % entry.id
        self._initial_values[name] = entry.status.name
        return form.Fields(
            Choice(
                __name__=name,
                source=EntryImportStatusVocabularyFactory(entry),
                title=_('Select import status')),
            custom_widget=self.custom_widgets['status'],
            render_context=self.render_context)

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpFields(self)
        # setup filter fields.
        target_field = self.createFilterTargetField()
        if target_field is not None:
            self.form_fields = (target_field + self.form_fields)

        self.form_fields = (
            self.createFilterStatusField() +
            self.createFilterFileExtensionField() +
            self.form_fields)

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpWidgets(self)

        if not self.filter_action.submitted():
            self.setUpEntriesWidgets()

    def setUpEntriesWidgets(self):
        """Prepare translation import entries widgets to be rendered."""
        fields = form.Fields()
        for entry in self.batchnav.currentBatch():
            fields += self.createEntryStatusField(entry)

        if len(fields) > 0:
            self.form_fields += fields

            self.widgets += form.setUpWidgets(
                fields, self.prefix, self.context, self.request,
                data=self.initial_values, ignore_request=False)

    @safe_action
    @action('Filter', name='filter')
    def filter_action(self, action, data):
        """Handle a filter action."""
        target_option = ''
        if self.has_target_filter:
            target_option = 'field.filter_target=%s&' % (
                self.widgets['filter_target'].getInputValue())

        # Redirect to the filtered URL.
        self.next_url = (
            '%s?%sfield.filter_status=%s&field.filter_extension=%s' % (
                self.request.URL,
                target_option,
                self.widgets['filter_status'].getInputValue(),
                self.widgets['filter_extension'].getInputValue()))

    @action("Change status", name='change_status')
    def change_status_action(self, action, data):
        """Handle a queue submission changing the status of its entries."""
        # The user must be logged in.
        if self.user is None:
            raise UnexpectedFormData(
                'Users not logged cannot submit this form.')

        number_of_changes = 0
        for form_item in data:
            if not form_item.startswith('status_'):
                # We are not interested on this form_item.
                continue

            # It's an form_item to handle.
            try:
                # 'ignored' is 'status' due to the previous check, so we could
                # ignore that part.
                ignored, id_string = form_item.split('_')
                # The id is an integer
                id = int(id_string)
            except ValueError:
                # We got an form_item with more than one '_' char or with an
                # id that is not a number, that means that someone is playing
                # badly with our system so it's safe to just ignore the
                # request.
                raise UnexpectedFormData(
                    'Ignored your request because it is broken.')
            # Get the entry we are working on.
            import_queue_set = getUtility(ITranslationImportQueue)
            entry = import_queue_set.get(id)
            new_status_name = data.get(form_item)
            if new_status_name == entry.status.name:
                # The entry's status didn't change we can jump to the next
                # entry.
                continue

            # The status changed.
            number_of_changes += 1

            # Only the importer, launchpad admins or Rosetta experts have
            # special permissions to change status.
            if (new_status_name == RosettaImportStatus.DELETED.name and
                check_permission('launchpad.Edit', entry)):
                entry.status = RosettaImportStatus.DELETED
            elif (new_status_name == RosettaImportStatus.BLOCKED.name and
                  check_permission('launchpad.Admin', entry)):
                entry.status = RosettaImportStatus.BLOCKED
            elif (new_status_name == RosettaImportStatus.APPROVED.name and
                  check_permission('launchpad.Admin', entry) and
                  entry.import_into is not None):
                entry.status = RosettaImportStatus.APPROVED
            elif (new_status_name == RosettaImportStatus.NEEDS_REVIEW.name and
                  check_permission('launchpad.Admin', entry)):
                entry.status = RosettaImportStatus.NEEDS_REVIEW
            else:
                # The user was not the importer or we are trying to set a
                # status that must not be set from this form. That means that
                # it's a broken request.
                raise UnexpectedFormData(
                    'Ignored the request to change the status from %s to %s.'
                        % (entry.status.name, new_status_name))

            # Update the date_status_change field.
            UTC = pytz.timezone('UTC')
            entry.date_status_changed = datetime.datetime.now(UTC)

        if number_of_changes == 0:
            self.request.response.addWarningNotification(
                "Ignored your status change request as you didn't select any"
                " change.")
        else:
            self.request.response.addInfoNotification(
                "Changed the status of %d queue entries." % number_of_changes)

    def getEntriesFilteringOptions(self):
        """Return the selected filtering."""
        target = None
        file_extension = None
        status = None
        filter_target_widget = self.widgets.get('filter_target')
        if (filter_target_widget is not None and
            filter_target_widget.hasValidInput()):
            target = filter_target_widget.getInputValue()
            pillar_name_set = getUtility(IPillarNameSet)
            if target == 'all':
                target = None
            elif '/' in target:
                # It's a distroseries, for them we have
                # 'distribution.name/distroseries.name' to identify it.
                distribution_name, distroseries_name = target.split('/', 1)
                pillar = pillar_name_set.getByName(distribution_name)
                if IDistribution.providedBy(pillar):
                    target = pillar.getSeries(distroseries_name)
                else:
                    raise UnexpectedFormData(
                        "Got a bad target option %s" % target)
            else:
                target = pillar_name_set.getByName(target)
        filter_extension_widget = self.widgets.get('filter_extension')
        if filter_extension_widget.hasValidInput():
            file_extension = filter_extension_widget.getInputValue()
            if file_extension == 'all':
                file_extension = None
        filter_status_widget = self.widgets.get('filter_status')
        if filter_status_widget.hasValidInput():
            status = filter_status_widget.getInputValue()
            if status == 'all':
                status = None
            else:
                status = RosettaImportStatus.items[status]
        return target, file_extension, status

    @property
    def translation_import_queue_content(self):
        """Macro displaying the import queue content."""
        macros = self.translation_import_queue_macros.macros
        return macros['translation-import-queue-content']

    @property
    def entries(self):
        """Return the entries in the queue for this context."""
        target, file_extension, status = self.getEntriesFilteringOptions()
        assert target is None, (
            'Inherit from this view class if target filter is being used.')

        return IHasTranslationImports(
            self.context).getTranslationImportQueueEntries(
                import_status=status, file_extension=file_extension)

    @property
    def has_target_filter(self):
        """Whether the form should show the target filter."""
        return self.widgets.get('filter_target') is not None

    @cachedproperty
    def batchnav(self):
        """Return batch object for this page."""
        return TableBatchNavigator(self.entries, self.request)


class EntryImportStatusVocabularyFactory:
    """Factory for a vocabulary containing a list of statuses for import."""

    implements(IContextSourceBinder)

    def __init__(self, entry):
        """Create a EntryImportStatusVocabularyFactory.

        :param entry: The ITranslationImportQueueEntry related with this
            vocabulary.
        """
        self.entry = entry

    def __call__(self, context):
        terms = []
        for status in RosettaImportStatus.items:
            if (status in (RosettaImportStatus.FAILED,
                           RosettaImportStatus.IMPORTED) and
                self.entry.status != status):
                # FAILED and IMPORTED status cannot be set by hand so we
                # don't give that choice.
                continue
            if (status == RosettaImportStatus.APPROVED and
                self.entry.status != status and
                (self.entry.import_into is None or
                 not check_permission('launchpad.Admin', self.entry))):
                # Only administrators are able to set the APPROVED status, and
                # that's only possible if we know where to import it
                # (import_into not None).
                continue
            if (status == RosettaImportStatus.BLOCKED and
                self.entry.status != status and
                not check_permission('launchpad.Admin', self.entry)):
                # Only administrators are able to set the BLOCKED status
                continue

            terms.append(SimpleTerm(status.name, status.name, status.title))
        return SimpleVocabulary(terms)


class TranslationImportStatusVocabularyFactory:
    """Factory for a vocabulary containing a list of import statuses."""

    implements(IContextSourceBinder)

    def __call__(self, context):
        terms = [SimpleTerm('all', 'all', 'All statuses')]
        for status in RosettaImportStatus.items:
            terms.append(SimpleTerm(status.name, status.name, status.title))
        return SimpleVocabulary(terms)


class TranslationImportFileExtensionVocabularyFactory:
    """Factory for a vocabulary containing a list of available extensions."""

    implements(IContextSourceBinder)

    def __call__(self, context):
        file_extensions = ('po', 'pot')

        terms = [SimpleTerm('all', 'all', 'All files')]
        for extension in file_extensions:
            title = 'Only %s files' % extension
            terms.append(SimpleTerm(extension, extension, title))
        return SimpleVocabulary(terms)

