# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for ITranslationImportQueue."""

__metaclass__ = type

__all__ = [
    'TranslationImportQueueEntryNavigation',
    'TranslationImportQueueEntryURL',
    'TranslationImportQueueEntryView',
    'TranslationImportQueueContextMenu',
    'TranslationImportQueueNavigation',
    'TranslationImportQueueView',
    ]

from zope.component import getUtility
from zope.interface import implements
from zope.app.form.browser.widget import renderElement

from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    ITranslationImportQueueEntry, ITranslationImportQueue, ICanonicalUrlData,
    IPOTemplateSet, NotFoundError, UnexpectedFormData)
from canonical.launchpad.webapp import (
    GetitemNavigation, LaunchpadView, ContextMenu, Link, canonical_url)
from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.lp.dbschema import RosettaImportStatus
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

class TranslationImportQueueEntryNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueueEntry


class TranslationImportQueueEntryURL:
    implements(ICanonicalUrlData)

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        translation_import_queue  = self.context
        return str(translation_import_queue.id)

    @property
    def inside(self):
        return getUtility(ITranslationImportQueue)


class TranslationImportQueueEntryView(GeneralFormView):
    """The view part of the admin interface for the translation import queue.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.initialize()
        GeneralFormView.__init__(self, context, request)

    def initialize(self):
        """Set the fields that will be shown based on the 'context' values.

        If the context comes from a productseries, the sourcepackagename
        chooser is hidden.
        If the 'context.path' field ends with the string '.pot', it means that
        the context is related with a '.pot' file, so we hide the language and
        variant fields as they are useless here.
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
        if self.context.productseries is None:
            potemplate_subset = potemplate_set.getSubset(
                distrorelease=self.context.distrorelease,
                sourcepackagename=destination_sourcepackagename)
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
        else:
            # We are hadling an IPOFile import.
            pofile = potemplate.getOrCreatePOFile(language.code, variant,
                self.context.importer)
            self.context.pofile = pofile

        self.context.status = RosettaImportStatus.APPROVED

    def nextURL(self):
        """Return the URL of the main import queue at 'rosetta/imports'."""
        translationimportqueue_set = getUtility(ITranslationImportQueue)
        return canonical_url(translationimportqueue_set)


class TranslationImportQueueNavigation(GetitemNavigation):

    usedfor = ITranslationImportQueue


class TranslationImportQueueContextMenu(ContextMenu):
    usedfor = ITranslationImportQueue
    links = ['overview']

    def overview(self):
        text = 'Import queue'
        return Link('', text)


class TranslationImportQueueView(LaunchpadView):
    """View class used for Translation Import Queue management."""

    DEFAULT_LENGTH = 50

    def _validateFilteringOptions(self):
        """Validate the filtering options for this form.

        This method initialize self.status and self.file_extension depending
        on the form values.

        Raise UnexpectedFormData if we get something wrong.
        """
        # Get the filtering arguments.
        self.status = str(self.form.get('status', 'all'))
        # but the file_extension must be in lower case.
        self.type = str(self.form.get('type', 'all'))

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
            (self.type not in ('all', 'po', 'pot'))):
            raise UnexpectedFormData(
                'The queue filtering got an unexpected value.')

        # Set to None status and type if they have the default value.
        if self.status == 'ALL':
            # Selected all status, the status is None to get all values.
            self.status = None
        else:
            # Get the DBSchema entry.
            self.status = RosettaImportStatus.items[status]
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
        self.start = int(self.request.get('batch_start', 0))
        self.batch = Batch(
            self.context.getAllEntries(
                status=self.status, file_extension=self.type),
            self.start, size=self.DEFAULT_LENGTH)
        self.batchnav = BatchNavigator(self.batch, self.request)

        # Flag to control whether the view page should be rendered.
        self.redirecting = False

        # Process the form.
        self.processForm()

    @property
    def has_entries(self):
        """Return whether there are things on the queue."""
        return len(self.context) > 0

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

        if entry.status == RosettaImportStatus.APPROVED:
            # If the entry is approved, this status should appear and set as
            # selected.
            approved_html = renderElement('option', selected='yes',
                value=RosettaImportStatus.APPROVED.name,
                contents=RosettaImportStatus.APPROVED.title)
        elif (helpers.check_permission('launchpad.Admin', entry) and
              entry.import_into is not None):
            # The entry is not approved but if we are an admin and we know
            # where it's going to be imported, we can approve it.
            approved_html = renderElement('option',
                value=RosettaImportStatus.APPROVED.name,
                contents=RosettaImportStatus.APPROVED.title)
        else:
            # We should not add the approved status for this entry.
            approved_html = ''

        if entry.status == RosettaImportStatus.IMPORTED:
            # If the entry is imported, this status should appear and set as
            # selected.
            imported_html = renderElement('option', selected='yes',
                value=RosettaImportStatus.IMPORTED.name,
                contents=RosettaImportStatus.IMPORTED.title)
        else:
            # Only the import script should be able to set the status to
            # imported, and thus, we don't add it as an option to select.
            imported_html = ''

        if entry.status == RosettaImportStatus.DELETED:
            # If the entry is deleted, this status should appear and set as
            # selected.
            deleted_html = renderElement('option', selected='yes',
                value=RosettaImportStatus.DELETED.name,
                contents=RosettaImportStatus.DELETED.title)
        else:
            deleted_html = renderElement('option',
                value=RosettaImportStatus.DELETED.name,
                contents=RosettaImportStatus.DELETED.title)


        if entry.status == RosettaImportStatus.FAILED:
            # If the entry is failed, this status should appear and set as
            # selected.
            failed_html = renderElement('option', selected='yes',
                value=RosettaImportStatus.FAILED.name,
                contents=RosettaImportStatus.FAILED.title)
        else:
            # Only the import script should be able to set the status to
            # failed, and thus, we don't add it as an option to select.
            failed_html = ''

        if entry.status == RosettaImportStatus.NEEDS_REVIEW:
            # If the entry needs review, this status should appear and set as
            # selected.
            needs_review_html = renderElement('option', selected='yes',
                value=RosettaImportStatus.NEEDS_REVIEW.name,
                contents=RosettaImportStatus.NEEDS_REVIEW.title)
        else:
            needs_review_html = renderElement('option',
                value=RosettaImportStatus.NEEDS_REVIEW.name,
                contents=RosettaImportStatus.NEEDS_REVIEW.title)

        if entry.status == RosettaImportStatus.BLOCKED:
            # If the entry is blocked, this status should appear and set as
            # selected.
            blocked_html = renderElement('option', selected='yes',
                value=RosettaImportStatus.BLOCKED.name,
                contents=RosettaImportStatus.BLOCKED.title)
        elif helpers.check_permission('launchpad.Admin', entry):
            # The entry is not blocked but if we are an admin, we can block
            # it.
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
