# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for ITranslationImportQueue."""

__metaclass__ = type

__all__ = [
    'TranslationImportQueueEntryNavigation',
    'TranslationImportQueueEntryURL',
    'TranslationImportQueueEntryView',
    'TranslationImportQueueEntryContextMenu',
    'TranslationImportQueueContextMenu',
    'TranslationImportQueueNavigation',
    'TranslationImportQueueView',
    ]

import datetime
import os
import pytz
from zope.component import getUtility
from zope.interface import implements
from zope.app.form.browser.widget import renderElement

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import helpers
from canonical.database.constants import UTC_NOW
from canonical.launchpad.browser.launchpad import RosettaContextMenu
from canonical.launchpad.interfaces import (
    ITranslationImportQueueEntry, IEditTranslationImportQueueEntry,
    ITranslationImportQueue, ICanonicalUrlData, IPOTemplateSet,
    ILanguageSet, NotFoundError, UnexpectedFormData)
from canonical.launchpad.webapp import (
    GetitemNavigation, LaunchpadView, canonical_url, LaunchpadFormView, action
    )
from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.lp.dbschema import RosettaImportStatus

class TranslationImportQueueEntryNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueueEntry


class TranslationImportQueueEntryURL:
    implements(ICanonicalUrlData)

    rootsite = 'mainsite'

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        translation_import_queue  = self.context
        return str(translation_import_queue.id)

    @property
    def inside(self):
        return getUtility(ITranslationImportQueue)


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
            # It's not a template, we try to guess the language based on its
            # file name.
            language_set = getUtility(ILanguageSet)
            filename = os.path.basename(self.context.path)
            guessed_language, file_ext = filename.split(u'.', 1)
            if file_ext == 'po':
                # The entry is a .po file so its filename would be a language
                # code.
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

        if self.context.path.endswith('.pot'):
            # It's template file, we don't need to choose the language and
            # variant.
            self.field_names.remove('language')
            self.field_names.remove('variant')

        # Execute default initialisation.
        LaunchpadFormView.initialize(self)

    def validate(self, data):
        """Extra validations for the given fields."""
        path = data.get('path')
        if path is not None and self.context.path != path:
            # The Rosetta Expert decided to change the path of the file.
            # Before accepting such change, we should check first whether is
            # already another entry with that path in the same context
            # (sourcepackagename/distrorelease or productseries).
            pofile_set = getUtility(IPOFileSet)
            existing_pofile = pofile_set.getPOFileByPathAndOrigin(
                path, self.context.productseries, self.context.distrorelease,
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
                    distrorelease=self.context.distrorelease,
                    sourcepackagename=sourcepackagename)
            else:
                potemplate_subset = potemplate_set.getSubset(
                    distrorelease=self.context.distrorelease,
                    sourcepackagename=self.context.sourcepackagename)
        else:
            potemplate_subset = potemplate_set.getSubset(
                productseries=self.context.productseries)
        try:
            potemplate = potemplate_subset[potemplatename.name]
        except NotFoundError:
            # The POTemplate does not exist. In this case we don't care if
            # the file is a .pot or a .po file, we can use either as the base
            # template.
            potemplate = potemplate_subset.new(
                potemplatename,
                self.context.path,
                self.context.importer)

        # Store the associated IPOTemplate.
        self.context.potemplate = potemplate

        if language is None:
            # We are importing an IPOTemplate file.
            if self.context.path.endswith('.po'):
                # The original import was a .po file but the admin decided to
                # import it as a .pot file, we update the path changing the
                # file extension from .po to .pot to reflect this fact.
                self.context.path = '%st' % self.context.path
            if (self.context.sourcepackagename is not None and
                potemplate.sourcepackagename is not None and
                self.context.sourcepackagename.id !=
                potemplate.sourcepackagename.id):
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


class TranslationImportQueueContextMenu(RosettaContextMenu):
    usedfor = ITranslationImportQueue


class TranslationImportQueueEntryContextMenu(RosettaContextMenu):
    usedfor = ITranslationImportQueueEntry


class TranslationImportQueueView(LaunchpadView):
    """View class used for Translation Import Queue management."""

    def _validateFilteringOptions(self):
        """Validate the filtering options for this form.

        This method initialize self.status and self.file_extension depending
        on the form values.

        Raise UnexpectedFormData if we get something wrong.
        """
        # Get the filtering arguments.
        self.status = str(self.form.get('status', 'all'))
        self.type = str(self.form.get('type', 'all'))
        self.target = str(self.form.get('target', 'all'))

        # Fix the case to our needs.
        if self.status:
            self.status = self.status.upper()
        if self.type:
            self.type = self.type.lower()

        # Prepare the list of available status.
        available_status = [
            status.name
            for status in RosettaImportStatus.items
            ]
        available_status.append('ALL')

        # Sanity checks so we don't accept broken input.
        if (not (self.status and self.type) or
            (self.status not in available_status) or
            (self.type not in ('all', 'po', 'pot')) or
            (self.target not in ('all', 'distros', 'products'))):
            raise UnexpectedFormData(
                'The queue filtering got an unexpected value.')

        # Set to None target, status and type if they have the default value.
        if self.target == 'all':
            self.target = None
        if self.status == 'ALL':
            # Selected all status, the status is None to get all values.
            self.status = None
        else:
            # Get the DBSchema entry.
            self.status = RosettaImportStatus.items[self.status]
        if self.type == 'all':
            # Selected all types, so the type is None to get all values.
            self.type = None

    def initialize(self):
        """Useful initialization for this view class."""
        # Get the filtering arguments.
        self.form = self.request.form

        # Validate the filtering arguments.
        self._validateFilteringOptions()

        # Setup the batching for this page.
        self.batchnav = BatchNavigator(self.context.getAllEntries(
            target=self.target, status=self.status, file_extension=self.type),
            self.request)

        # Flag to control whether the view page should be rendered.
        self.redirecting = False

        # Process the form.
        self.processForm()

    @cachedproperty
    def has_entries(self):
        """Return whether there are things on the queue."""
        return bool(self.context.entryCount())

    def processForm(self):
        """Block or remove entries from the queue based on the selection of
        the form.
        """
        if self.request.method != 'POST' or self.user is None:
            # The form was not submitted or the user is not logged in.
            return

        dispatch_table = {
            'handle_queue': self._handle_queue,
            }
        dispatch_to = [(key, method)
                        for key, method in dispatch_table.items()
                        if key in self.form
                      ]
        if len(dispatch_to) != 1:
            raise UnexpectedFormData(
                "There should be only one command in the form",
                dispatch_to)
        key, method = dispatch_to[0]
        method()

    def _handle_queue(self):
        """Handle a queue submission changing the status of its entries."""
        # The user must be logged in.
        assert self.user is not None

        number_of_changes = 0
        for form_item in self.form:
            if not form_item.startswith('status-'):
                # We are not interested on this form_item.
                continue

            # It's an form_item to handle.
            try:
                common, id_string = form_item.split('-')
                # The id is an integer
                id = int(id_string)
            except ValueError:
                # We got an form_item with more than one '-' char or with an
                # id that is not a number, that means that someone is playing
                # badly with our system so it's safe to just ignore the
                # request.
                raise UnexpectedFormData(
                    'Ignored your request because it is broken.')
            # Get the entry we are working on.
            entry = self.context.get(id)
            new_status_name = self.form.get(form_item)
            if new_status_name == entry.status.name:
                # The entry's status didn't change we can jump to the next
                # entry.
                continue

            # The status changed.

            number_of_changes += 1

            # Only the importer, launchpad admins or Rosetta experts have
            # special permissions to change status.
            if (new_status_name == RosettaImportStatus.DELETED.name and
                helpers.check_permission('launchpad.Edit', entry)):
                entry.status = RosettaImportStatus.DELETED
            elif (new_status_name == RosettaImportStatus.BLOCKED.name and
                  helpers.check_permission('launchpad.Admin', entry)):
                entry.status = RosettaImportStatus.BLOCKED
            elif (new_status_name == RosettaImportStatus.APPROVED.name and
                  helpers.check_permission('launchpad.Admin', entry) and
                  entry.import_into is not None):
                entry.status = RosettaImportStatus.APPROVED
            elif (new_status_name == RosettaImportStatus.NEEDS_REVIEW.name and
                  helpers.check_permission('launchpad.Admin', entry)):
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

        # We do a redirect so the submit doesn't breaks if the rendering of
        # the page takes too much time.
        url_string = self.request.getURL()
        query_string = self.request.environment.get("QUERY_STRING")
        if query_string:
            url_string = "%s?%s" % (url_string, query_string)
        self.request.response.redirect(url_string)
        self.redirecting = True

    def renderOption(self, status, selected=False, check_status=None,
                     empty_if_check_fails=False):
        """Render an option for a certain status

        When check_status is supplied, check if the supplied status
        matches the check_status. If empty_if_check_fails is
        additionally set to True, and the check fails, return an empty
        string.
        """
        if check_status is not None:
            if check_status == status:
                selected = True
            elif empty_if_check_fails:
                return ''

        # We need to supply selected as a dictionary because it can't
        # appear at all in the argument list for renderElement -- if it
        # does it is included in the HTML output
        if selected:
            selected = {'selected': 'yes'}
        else:
            selected = {}
        html = renderElement('option',
            value=status.name,
            contents=status.title,
            **selected)

        return html

    def getStatusFilteringSelect(self):
        """Return a select html tag with all status for filtering purposes."""
        selected_status = self.form.get('status', 'all')
        html = ''
        for status in RosettaImportStatus.items:
            selected = (status.name.lower() == selected_status.lower())
            html = '%s\n%s' % (
                html, self.renderOption(status, selected=selected))
        return html

    def getStatusSelect(self, entry):
        """Return a select html tag with the possible status for entry

        :arg entry: An ITranslationImportQueueEntry.
        """
        assert helpers.check_permission('launchpad.Edit', entry), (
            'You can only change the status if you have rights to do it')

        deleted_html = self.renderOption(RosettaImportStatus.DELETED,
                                         check_status=entry.status)
        needs_review_html = self.renderOption(RosettaImportStatus.NEEDS_REVIEW,
                                              check_status=entry.status)

        failed_html = self.renderOption(RosettaImportStatus.FAILED,
                                        check_status=entry.status,
                                        empty_if_check_fails=True)
        imported_html = self.renderOption(RosettaImportStatus.IMPORTED,
                                          check_status=entry.status,
                                          empty_if_check_fails=True)

        # These two options have special checks for permissions -- only
        # admins can select them, though anyone can unselect.
        if entry.status == RosettaImportStatus.APPROVED:
            approved_html = self.renderOption(RosettaImportStatus.APPROVED,
                                              selected=True)
        elif (helpers.check_permission('launchpad.Admin', entry) and
              entry.import_into is not None):
            # We also need to check here if we know where to import this
            # entry; if not, there's no sense in allowing this to be set
            # as approved.
            approved_html = self.renderOption(RosettaImportStatus.APPROVED,
                                              selected=False)
        else:
            approved_html = ''

        if entry.status == RosettaImportStatus.BLOCKED:
            blocked_html = renderElement('option', selected='yes',
                value=RosettaImportStatus.BLOCKED.name,
                contents=RosettaImportStatus.BLOCKED.title)
        elif helpers.check_permission('launchpad.Admin', entry):
            blocked_html = renderElement('option',
                value=RosettaImportStatus.BLOCKED.name,
                contents=RosettaImportStatus.BLOCKED.title)
        else:
            # We should not add the blocked status for this entry.
            blocked_html = ''

        # Generate the final select html tag with the possible values.
        return renderElement('select', name='status-%d' % entry.id,
            contents='%s\n%s\n%s\n%s\n%s\n%s\n' % (
                approved_html, imported_html, deleted_html, failed_html,
                needs_review_html, blocked_html))

    def render(self):
        if self.redirecting:
            return u''
        else:
            return LaunchpadView.render(self)


