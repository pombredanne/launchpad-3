# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""Browser view for IHasTranslationImports."""

__metaclass__ = type

__all__ = [
    'HasTranslationImportsView',
    ]

import datetime
import pytz
from zope.app.form.browser.widget import renderElement
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IHasTranslationImports, ITranslationImportQueue,
    UnexpectedFormData)
from canonical.launchpad.webapp import (
    LaunchpadFormView, action, canonical_url)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.lp.dbschema import RosettaImportStatus

class HasTranslationImportsView(LaunchpadFormView):
    """View class used for objects with translation imports."""
    schema = IHasTranslationImports
    field_names = []

    def _validateFilteringOptions(self):
        """Validate the filtering options for this form.

        This method initialize self.status and self.file_extension depending
        on the form values.

        Raise UnexpectedFormData if we get something wrong.
        """
        form = self.request.form
        # Get the filtering arguments.
        self.status = str(form.get('status', 'all'))
        self.type = str(form.get('type', 'all'))

        # Fix the case to our needs.
        if self.status is not None:
            self.status = self.status.upper()
        if self.type is not None:
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
            self.status = RosettaImportStatus.items[self.status]

        if self.type == 'all':
            # Selected all types, so the type is None to get all values.
            self.type = None

        if 'field.actions.filter' in form:
            # Got a filter action, redirect to the next url.
            self.request.response.redirect(self.next_url)

    def initialize(self):
        # Validate the filtering arguments.
        self._validateFilteringOptions()

        self.label = 'Translation files waiting to be imported for %s' % (
            self.context.displayname)

        LaunchpadFormView.initialize(self)


    @action("Change status")
    def change_status_action(self, action, data):
        """Handle a queue submission changing the status of its entries."""
        # The user must be logged in.
        assert self.user is not None

        # We are not rendering rows automatically based on an Interface and
        # thus, data is always empty. We fill it with form's content.
        data = self.request.form

        number_of_changes = 0
        for form_item in data:
            if not form_item.startswith('field.status-'):
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

    @property
    def entries(self):
        """Return the entries in the queue for this context."""
        return self.context.getTranslationImportQueueEntries(
            status=self.status, file_extension=self.type)

    @property
    def has_entries(self):
        """Whether there are entries in the queue."""
        return self.entries.count() > 0

    @property
    def batchnav(self):
        """Return batch object for this page."""
        return BatchNavigator(self.entries, self.request)

    @property
    def next_url(self):
        arguments = []
        if self.status is not None:
            arguments.append('status=%s' % self.status.name)
        if self.type is not None:
            arguments.append('type=%s' % self.type)
        if len(arguments) > 0:
            arg_string = '?%s' % '&'.join(arguments)
        else:
            arg_string = ''
        return '/'.join(
                [canonical_url(self.context), '+imports%s' % arg_string])


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
        selected_status = self.request.form.get('status', 'all')
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
        assert check_permission('launchpad.Edit', entry), (
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
        elif (check_permission('launchpad.Admin', entry) and
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
        elif check_permission('launchpad.Admin', entry):
            blocked_html = renderElement('option',
                value=RosettaImportStatus.BLOCKED.name,
                contents=RosettaImportStatus.BLOCKED.title)
        else:
            # We should not add the blocked status for this entry.
            blocked_html = ''

        # Generate the final select html tag with the possible values.
        entry_id = 'field.status-%d' % entry.id
        return renderElement('select', id=entry_id, name=entry_id,
            contents='%s\n%s\n%s\n%s\n%s\n%s\n' % (
                approved_html, imported_html, deleted_html, failed_html,
                needs_review_html, blocked_html))
