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
    ILaunchpadCelebrities, ITranslationImportQueueEdition)
from canonical.launchpad.webapp import (
    GetitemNavigation, LaunchpadView, ContextMenu, Link)
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
    """This view handles the view part of the admin interface for the
    translation import queue.
    """

    def process(self, potemplatename, productseries, sourcepackagename,
        language, variant, path):
        """Process the form we got from the submission."""
        return 'Hi!'



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
        """Return the set of entries that can be imported directly."""
        for entry in self.context.getEntries():
            if entry.import_into is not None:
                yield entry

    def pendingReview(self):
        """Return the set of entries that need manually review."""
        for entry in self.context.getEntries():
            if entry.import_into is None:
                yield entry

    def submitForm(self):
        """Called from the page template to do any processing needed if a form
        was submitted with the request."""

        if self.request.method == 'POST' and self.user is not None:
            if 'remove_import' in self.request.form:
                self.remove()
            elif "block_import" in self.request.form:
                self.block()
            elif 'remove_review' in self.request.form:
                self.remove()
            elif "block_review" in self.request.form:
                self.block()
            elif 'remove_blocked' in self.request.form:
                self.remove()
            elif "unblock" in self.request.form:
                self.unblock()

    def remove(self):
        """Handle a form submission to remove items ready to be imported."""
        removed = 0
        ignored = 0
        broken = 0
        for item in self.request.form:
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
                    broken += 1
                    continue

                entry = self.context.get(id)
                if self.user.inTeam(entry.importer):
                    # Do the removal.
                    self.context.remove(id)
                    removed += 1
                else:
                    # The user was not the importer so we ignore the request.
                    ignored += 1


        # Notifications.
        if broken == 1:
            self.alerts.append('A broken request was detected and ignored.')
        elif broken > 1:
            self.alerts.append(
                '%d broken requests were detected and were ignored.' % broken)
        if ignored == 1:
            self.alerts.append(
                '%d item removal was ignored becasue is not yours.' % ignored)
        elif ignored > 1:
            self.alerts.append(
                '%d item removals were ignored because aren\'t yours.' %
                    ignored)
        if removed == 1:
            self.notices.append('%d item was removed.' % removed)
        elif removed > 1:
            self.notices.append('%d items were removed.' % removed)

    def block(self):
        """Handle a form submission to block items to be imported."""
        blocked = 0
        ignored = 0
        broken = 0
        for item in self.request.form:
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
                    broken += 1
                    continue

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
                    ignored += 1

        # Notifications.
        if broken == 1:
            self.alerts.append('A broken request was detected and ignored.')
        elif broken > 1:
            self.alerts.append(
                '%d broken requests were detected and were ignored.' % broken)
        if ignored == 1:
            self.alerts.append(
                '%d item removal was ignored becasue is not yours.' % ignored)
        elif ignored > 1:
            self.alerts.append(
                '%d item removals were ignored because aren\'t yours.' %
                    ignored)
        if blocked == 1:
            self.notices.append('%d item was blocked.' % blocked)
        elif blocked > 1:
            self.notices.append('%d items were blocked.' % blocked)

    def unblock(self):
        """Handle a form submission to unblock items to be imported."""
        unblocked = 0
        ignored = 0
        broken = 0
        for item in self.request.form:
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
                    broken += 1
                    continue

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
                    ignored += 1

        # Notifications.
        if broken == 1:
            self.alerts.append('A broken request was detected and ignored.')
        elif broken > 1:
            self.alerts.append(
                '%d broken requests were detected and were ignored.' % broken)
        if ignored == 1:
            self.alerts.append(
                '%d item removal was ignored becasue is not yours.' % ignored)
        elif ignored > 1:
            self.alerts.append(
                '%d item removals were ignored because aren\'t yours.' %
                    ignored)
        if unblocked == 1:
            self.notices.append('%d item was unblocked.' % unblocked)
        elif unblocked > 1:
            self.notices.append('%d items were unblocked.' % unblocked)
