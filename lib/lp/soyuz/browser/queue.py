# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for package queue."""

__metaclass__ = type

__all__ = [
    'QueueItemsView',
    ]

import cgi
import operator

from lazr.delegates import delegates
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from lp.app.errors import (
    NotFoundError,
    UnexpectedFormData,
    )
from lp.services.database.bulk import (
    load_referencing,
    load_related,
    )
from lp.services.job.model.job import Job
from lp.soyuz.enums import (
    PackagePublishingPriority,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageNameSet
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.files import (
    IBinaryPackageFileSet,
    ISourcePackageReleaseFileSet,
    )
from lp.soyuz.interfaces.packageset import IPackagesetSet
from lp.soyuz.interfaces.publishing import name_priority_map
from lp.soyuz.interfaces.queue import (
    IPackageUpload,
    IPackageUploadSet,
    QueueInconsistentStateError,
    )
from lp.soyuz.interfaces.section import ISectionSet


QUEUE_SIZE = 30


class QueueItemsView(LaunchpadView):
    """Base class used to present objects that contain queue items.

    It retrieves the UI queue_state selector action and sets up a proper
    batched list with the requested results. See further UI details in
    template/distroseries-queue.pt and callsite details in DistroSeries
    view classes.
    """

    def setupQueueList(self):
        """Setup a batched queue list.

        Returns None, so use tal:condition="not: view/setupQueueList" to
        invoke it in template.
        """

        # recover selected queue state and name filter
        self.name_filter = self.request.get('queue_text', '')

        try:
            state_value = int(self.request.get('queue_state', ''))
        except ValueError:
            state_value = PackageUploadStatus.NEW.value

        try:
            self.state = PackageUploadStatus.items[state_value]
        except KeyError:
            raise UnexpectedFormData(
                'No suitable status found for value "%s"' % state_value)

        self.queue = self.context.getPackageUploadQueue(self.state)

        valid_states = [
            PackageUploadStatus.NEW,
            PackageUploadStatus.ACCEPTED,
            PackageUploadStatus.REJECTED,
            PackageUploadStatus.DONE,
            PackageUploadStatus.UNAPPROVED,
            ]

        self.filtered_options = []

        for state in valid_states:
            selected = (state == self.state)
            self.filtered_options.append(
                dict(name=state.title, value=state.value, selected=selected))

        queue_items = self.context.getPackageUploads(
            status=self.state, name=self.name_filter)
        self.batchnav = BatchNavigator(
            queue_items, self.request, size=QUEUE_SIZE)

    def builds_dict(self, upload_ids, binary_files):
        """Return a dictionary of PackageUploadBuild keyed on build ID.

        :param upload_ids: A list of PackageUpload IDs.
        :param binary_files: A list of BinaryPackageReleaseFiles.
        """
        build_ids = [binary_file.binarypackagerelease.build.id
                     for binary_file in binary_files]
        upload_set = getUtility(IPackageUploadSet)
        package_upload_builds = upload_set.getBuildByBuildIDs(
            build_ids)
        package_upload_builds_dict = {}
        for package_upload_build in package_upload_builds:
            package_upload_builds_dict[
                package_upload_build.build.id] = package_upload_build
        return package_upload_builds_dict

    def binary_files_dict(self, package_upload_builds_dict, binary_files):
        """Build a dictionary of lists of binary files keyed by upload ID.

        To do this efficiently we need to get all the PacakgeUploadBuild
        records at once, otherwise the Ibuild.package_upload property
        causes one query per iteration of the loop.
        """
        build_upload_files = {}
        binary_package_names = set()
        for binary_file in binary_files:
            binary_package_names.add(
                binary_file.binarypackagerelease.binarypackagename.id)
            build_id = binary_file.binarypackagerelease.build.id
            upload_id = package_upload_builds_dict[build_id].packageupload.id
            if upload_id not in build_upload_files:
                build_upload_files[upload_id] = []
            build_upload_files[upload_id].append(binary_file)
        return build_upload_files, binary_package_names

    def source_dict(self, upload_ids, source_files):
        """Return a dictionary of PackageUploadSource keyed on SPR ID.

        :param upload_ids: A list of PackageUpload IDs.
        """
        sourcepackagerelease_ids = [
            source_file.sourcepackagerelease.id
            for source_file in source_files]

        upload_set = getUtility(IPackageUploadSet)
        pkg_upload_sources = upload_set.getSourceBySourcePackageReleaseIDs(
            sourcepackagerelease_ids)
        package_upload_source_dict = {}
        for pkg_upload_source in pkg_upload_sources:
            package_upload_source_dict[
                pkg_upload_source.sourcepackagerelease.id] = pkg_upload_source
        return package_upload_source_dict

    def source_files_dict(self, package_upload_source_dict, source_files):
        """Return a dictionary of source files keyed on PackageUpload ID."""
        source_upload_files = {}
        for source_file in source_files:
            upload_id = package_upload_source_dict[
                source_file.sourcepackagerelease.id].packageupload.id
            if upload_id not in source_upload_files:
                source_upload_files[upload_id] = []
            source_upload_files[upload_id].append(source_file)
        return source_upload_files

    def calculateOldBinaries(self, binary_package_names):
        """Calculate uploaded binary files in this batch that are old."""
        name_set = getUtility(IBinaryPackageNameSet)
        # removeSecurityProxy is needed because sqlvalues() inside
        # getNotNewByIDs can't handle a security-wrapped list of
        # integers.
        archive_ids = removeSecurityProxy(
            self.context.distribution.all_distro_archive_ids)
        old_binary_packages = name_set.getNotNewByNames(
            binary_package_names, self.context, archive_ids)
        # Listify to avoid repeated queries.
        return list(old_binary_packages)

    def getPackagesetsFor(self, source_package_releases):
        """Find associated `Packagesets`.

        :param source_package_releases: A sequence of `SourcePackageRelease`s.
        """
        sprs = [spr for spr in source_package_releases if spr is not None]
        return getUtility(IPackagesetSet).getForPackages(
            self.context, set(spr.sourcepackagenameID for spr in sprs))

    def loadPackageCopyJobs(self, uploads):
        """Batch-load `PackageCopyJob`s and related information."""
        # Avoid circular imports.
        from lp.registry.model.person import Person
        from lp.soyuz.model.archive import Archive
        from lp.soyuz.model.packagecopyjob import PackageCopyJob

        package_copy_jobs = load_related(
            PackageCopyJob, uploads, ['package_copy_job_id'])
        load_related(Archive, package_copy_jobs, ['source_archive_id'])
        jobs = load_related(Job, package_copy_jobs, ['job_id'])
        load_related(Person, jobs, ['requester_id'])

    def decoratedQueueBatch(self):
        """Return the current batch, converted to decorated objects.

        Each batch item, a PackageUpload, is converted to a
        CompletePackageUpload.  This avoids many additional SQL queries
        in the +queue template.
        """
        # Avoid circular imports.
        from lp.soyuz.model.queue import PackageUploadSource
        from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease

        uploads = list(self.batchnav.currentBatch())

        if len(uploads) == 0:
            return None

        # Operate only on upload and/or processed delayed-copies.
        upload_ids = [
            upload.id
            for upload in uploads
            if not (upload.is_delayed_copy and
                    upload.status != PackageUploadStatus.DONE)]
        binary_file_set = getUtility(IBinaryPackageFileSet)
        binary_files = binary_file_set.getByPackageUploadIDs(upload_ids)
        binary_file_set.loadLibraryFiles(binary_files)
        packageuploadsources = load_referencing(
            PackageUploadSource, uploads, ['packageuploadID'])
        source_file_set = getUtility(ISourcePackageReleaseFileSet)
        source_files = source_file_set.getByPackageUploadIDs(upload_ids)

        source_sprs = load_related(
            SourcePackageRelease, packageuploadsources,
            ['sourcepackagereleaseID'])

        # Get a dictionary of lists of binary files keyed by upload ID.
        package_upload_builds_dict = self.builds_dict(
            upload_ids, binary_files)

        build_upload_files, binary_package_names = self.binary_files_dict(
            package_upload_builds_dict, binary_files)

        # Get a dictionary of lists of source files keyed by upload ID.
        package_upload_source_dict = self.source_dict(
            upload_ids, source_files)
        source_upload_files = self.source_files_dict(
            package_upload_source_dict, source_files)

        # Get a list of binary package names that already exist in
        # the distribution.  The avoids multiple queries to is_new
        # on IBinaryPackageRelease.
        self.old_binary_packages = self.calculateOldBinaries(
            binary_package_names)

        package_sets = self.getPackagesetsFor(source_sprs)

        self.loadPackageCopyJobs(uploads)

        return [
            CompletePackageUpload(
                item, build_upload_files, source_upload_files, package_sets)
            for item in uploads]

    def is_new(self, binarypackagerelease):
        """Return True if the binarypackagerelease has no ancestry."""
        return (
            binarypackagerelease.binarypackagename
            not in self.old_binary_packages)

    def availableActions(self):
        """Return the available actions according to the selected queue state.

        Returns a list of labelled actions or an empty list.
        """
        # States that support actions.
        mutable_states = [
            PackageUploadStatus.NEW,
            PackageUploadStatus.REJECTED,
            PackageUploadStatus.UNAPPROVED
            ]

        # Return actions only for supported states and require
        # edit permission.
        if (self.state in mutable_states and
            check_permission('launchpad.Edit', self.queue)):
            return ['Accept', 'Reject']

        # No actions for unsupported states.
        return []

    def performQueueAction(self):
        """Execute the designed action over the selected queue items.

        Returns a message describing the action executed or None if nothing
        was done.
        """
        # Immediately bail out if the page is not the result of a submission.
        if self.request.method != "POST":
            return

        # Also bail out if an unauthorised user is faking submissions.
        if not check_permission('launchpad.Edit', self.queue):
            self.error = 'You do not have permission to act on queue items.'
            return

        # Retrieve the form data.
        accept = self.request.form.get('Accept', '')
        reject = self.request.form.get('Reject', '')
        component_override = self.request.form.get('component_override', '')
        section_override = self.request.form.get('section_override', '')
        priority_override = self.request.form.get('priority_override', '')
        queue_ids = self.request.form.get('QUEUE_ID', '')

        # If no boxes were checked, bail out.
        if (not accept and not reject) or not queue_ids:
            return

        # Determine if there is a source override requested.
        new_component = None
        new_section = None
        try:
            if component_override:
                new_component = getUtility(IComponentSet)[component_override]
        except NotFoundError:
            self.error = "Invalid component: %s" % component_override
            return

        # Get a list of components for which the user has rights to
        # override to or from.
        permission_set = getUtility(IArchivePermissionSet)
        permissions = permission_set.componentsForQueueAdmin(
            self.context.main_archive, self.user)
        allowed_components = set(
            permission.component for permission in permissions)

        try:
            if section_override:
                new_section = getUtility(ISectionSet)[section_override]
        except NotFoundError:
            self.error = "Invalid section: %s" % section_override
            return

        # Determine if there is a binary override requested.
        new_priority = None
        if priority_override not in name_priority_map:
            self.error = "Invalid priority: %s" % priority_override
            return

        new_priority = name_priority_map[priority_override]

        # Process the requested action.
        if not isinstance(queue_ids, list):
            queue_ids = [queue_ids]

        queue_set = getUtility(IPackageUploadSet)

        if accept:
            action = "accept"
        elif reject:
            action = "reject"

        success = []
        failure = []
        for queue_id in queue_ids:
            queue_item = queue_set.get(int(queue_id))
            # First check that the user has rights to accept/reject this
            # item by virtue of which component it has.
            if not check_permission('launchpad.Edit', queue_item):
                existing_component_names = ", ".join(
                    component.name for component in queue_item.components)
                failure.append(
                    "FAILED: %s (You have no rights to %s component(s) "
                    "'%s')" % (queue_item.displayname,
                               action,
                               existing_component_names))
                continue

            # Sources and binaries are mutually exclusive when it comes to
            # overriding, so only one of these will be set.
            try:
                source_overridden = queue_item.overrideSource(
                    new_component, new_section, allowed_components)
                binary_overridden = queue_item.overrideBinaries(
                    new_component, new_section, new_priority,
                    allowed_components)
            except QueueInconsistentStateError, info:
                failure.append("FAILED: %s (%s)" %
                               (queue_item.displayname, info))
                continue

            feedback_interpolations = {
                "name": queue_item.displayname,
                "component": "(unchanged)",
                "section": "(unchanged)",
                "priority": "(unchanged)",
                }
            if new_component:
                feedback_interpolations['component'] = new_component.name
            if new_section:
                feedback_interpolations['section'] = new_section.name
            if new_priority:
                feedback_interpolations[
                    'priority'] = new_priority.title.lower()

            try:
                getattr(self, 'queue_action_' + action)(queue_item)
            except QueueInconsistentStateError, info:
                failure.append('FAILED: %s (%s)' %
                               (queue_item.displayname, info))
            else:
                if source_overridden:
                    desc = "%(name)s(%(component)s/%(section)s)"
                elif binary_overridden:
                    desc = "%(name)s(%(component)s/%(section)s/%(priority)s)"
                else:
                    desc = "%(name)s"
                success.append(
                    "OK: " + desc % feedback_interpolations)

        for message in success:
            self.request.response.addInfoNotification(message)
        for message in failure:
            self.request.response.addErrorNotification(message)
        # Greasy hack!  Is there a better way of setting GET data in the
        # response?
        # (This is needed to make the user see the same queue page
        # after the redirection)
        url = str(self.request.URL) + "?queue_state=%s" % self.state.value
        self.request.response.redirect(url)

    def queue_action_accept(self, queue_item):
        """Reject the queue item passed."""
        queue_item.acceptFromQueue()

    def queue_action_reject(self, queue_item):
        """Accept the queue item passed."""
        queue_item.rejectFromQueue()

    def sortedSections(self):
        """Possible sections for the context distroseries.

        Return an iterable of possible sections for the context distroseries
        sorted by their name.
        """
        return sorted(
            self.context.sections, key=operator.attrgetter('name'))

    def priorities(self):
        """An iterable of priorities from PackagePublishingPriority."""
        return (priority for priority in PackagePublishingPriority)


class CompletePackageUpload:
    """A decorated `PackageUpload` including sources, builds and packages.

    This acts effectively as a view for package uploads.  Some properties of
    the class are cached here to reduce the number of queries that the +queue
    template has to make.  Others are added here exclusively.
    """
    # These need to be predeclared to avoid delegates taking them over.
    # Would be nice if there was a way of allowing writes to just work
    # (i.e. no proxying of __set__).
    pocket = None
    date_created = None
    sources = None
    builds = None
    customfiles = None
    contains_source = None
    contains_build = None
    sourcepackagerelease = None

    delegates(IPackageUpload)

    def __init__(self, packageupload, build_upload_files,
                 source_upload_files, package_sets):
        self.pocket = packageupload.pocket
        self.date_created = packageupload.date_created
        self.context = packageupload
        self.sources = list(packageupload.sources)
        self.contains_source = len(self.sources) > 0
        self.builds = list(packageupload.builds)
        self.contains_build = len(self.builds) > 0
        self.customfiles = list(packageupload.customfiles)

        # Create a dictionary of binary files keyed by
        # binarypackagerelease.
        self.binary_packages = {}
        for binary in build_upload_files.get(self.id, []):
            package = binary.binarypackagerelease
            self.binary_packages.setdefault(package, []).append(binary)

        # Create a list of source files if this is a source upload.
        self.source_files = source_upload_files.get(self.id, None)

        if self.contains_source:
            self.sourcepackagerelease = self.sources[0].sourcepackagerelease

        if self.contains_source:
            self.package_sets = package_sets.get(
                self.sourcepackagerelease.sourcepackagenameID, [])
        else:
            self.package_sets = []

    @property
    def pending_delayed_copy(self):
        """Whether the context is a delayed-copy pending processing."""
        return (
            self.is_delayed_copy and self.status != PackageUploadStatus.DONE)

    @property
    def changesfile(self):
        """Return the upload changesfile object, even for delayed-copies.

        If the context `PackageUpload` is a delayed-copy, which doesn't
        have '.changesfile' by design, return the changesfile originally
        used to upload the contained source.
        """
        if self.is_delayed_copy:
            return self.sourcepackagerelease.upload_changesfile
        return self.context.changesfile

    @property
    def display_package_sets(self):
        """Package sets, if any, for display on the +queue page."""
        return ' '.join(sorted(
            packageset.name for packageset in self.package_sets))

    @property
    def display_component(self):
        """Component name, if any, for display on the +queue page."""
        component_name = self.component_name
        if component_name is None:
            return ""
        else:
            return component_name.lower()

    @property
    def display_section(self):
        """Section name, if any, for display on the +queue page."""
        section_name = self.section_name
        if section_name is None:
            return ""
        else:
            return section_name.lower()

    @property
    def display_priority(self):
        """Priority name, if any, for display on the +queue page."""
        if self.contains_source:
            return self.sourcepackagerelease.urgency.name.lower()
        else:
            return ""

    def composeIcon(self, alt, icon, title=None):
        """Compose an icon for the package's icon list."""
        # These should really be sprites!
        if title is None:
            title = alt
        return '<img alt="[%s]" src="/@@/%s" title="%s" />' % (
            cgi.escape(alt, quote=True),
            icon,
            cgi.escape(title, quote=True),
            )

    def composeIconList(self):
        """List icons that should be shown for this upload."""
        ddtp = "Debian Description Translation Project Indexes"
        potential_icons = [
            (self.contains_source, ("Source", 'package-source')),
            (self.contains_build, ("Build", 'package-binary', "Binary")),
            (self.package_copy_job, ("Sync", 'package-sync')),
            (self.contains_translation, ("Translation", 'translation-file')),
            (self.contains_installer, ("Installer", 'ubuntu-icon')),
            (self.contains_upgrader, ("Upgrader", 'ubuntu-icon')),
            (self.contains_ddtp, (ddtp, 'ubuntu-icon')),
            ]
        return [
            self.composeIcon(*details)
            for condition, details in potential_icons
                if condition]

    def composeNameAndChangesLink(self):
        """Compose HTML: upload name and link to changes file."""
        raw_displayname = self.displayname
        displayname = cgi.escape(raw_displayname)
        if self.pending_delayed_copy or self.changesfile is None:
            return displayname
        else:
            return '<a href="%s" title="Changes file for %s">%s</a>' % (
                self.changesfile.http_url,
                cgi.escape(self.displayname, quote=True),
                displayname)

    @property
    def icons_and_name(self):
        """Icon list and name, linked to changes file if appropriate."""
        iconlist_id = "queue%d-iconlist" % self.id
        icons = self.composeIconList()
        link = self.composeNameAndChangesLink()
        return """
            <div id="%s">
              %s
              %s
              (%s)
            </div>
            """ % (iconlist_id, '\n'.join(icons), link, self.displayarchs)
