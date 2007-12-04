# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['DistributionMirrorEditView', 'DistributionMirrorFacets',
           'DistributionMirrorOverviewMenu', 'DistributionMirrorAddView',
           'DistributionMirrorView', 'DistributionMirrorOfficialApproveView',
           'DistributionMirrorReassignmentView',
           'DistributionMirrorDeleteView']

from zope.app.event.objectevent import ObjectCreatedEvent
from zope.event import notify

from canonical.archivepublisher.debversion import Version
from canonical.launchpad import _
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, enabled_with_permission,
    LaunchpadEditFormView, LaunchpadFormView, Link, StandardLaunchpadFacets)
from canonical.launchpad.interfaces import IDistributionMirror
from canonical.launchpad.browser.objectreassignment import (
    ObjectReassignmentView)
from canonical.launchpad.browser.sourceslist import (
    SourcesListEntries, SourcesListEntriesView)
from canonical.cachedproperty import cachedproperty


class DistributionMirrorFacets(StandardLaunchpadFacets):

    usedfor = IDistributionMirror
    enable_only = ['overview']


class DistributionMirrorOverviewMenu(ApplicationMenu):

    usedfor = IDistributionMirror
    facet = 'overview'
    links = ['proberlogs', 'edit', 'admin', 'reassign', 'delete']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def proberlogs(self):
        text = 'Prober logs'
        return Link('+prober-logs', text, icon='info')

    @enabled_with_permission('launchpad.Admin')
    def delete(self):
        enabled = False
        if self.context.last_probe_record is None:
            enabled = True
        text = 'Delete this mirror'
        return Link('+delete', text, icon='remove', enabled=enabled)

    @enabled_with_permission('launchpad.Admin')
    def reassign(self):
        text = 'Change owner'
        return Link('+reassign', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        if self.context.isOfficial():
            text = 'Mark as unofficial'
        else:
            text = 'Mark as official'
        return Link('+mark-official', text, icon='edit')


class _FlavoursByDistroSeries:
    """A simple class to help when rendering a table of series and flavours
    mirrored by a given Distro Series mirror.
    """

    def __init__(self, distroseries, flavours):
        self.distroseries = distroseries
        self.flavours = flavours


class DistributionMirrorView(LaunchpadView):

    def initialize(self):
        """Set up the sources.list entries for display."""
        valid_series = []
        # use an explicit loop to preserve ordering while getting rid of dupes
        for arch_series in self.summarized_arch_series:
            series = arch_series.distro_arch_series.distroseries
            if series not in valid_series:
                valid_series.append(series)
        entries = SourcesListEntries(self.context.distribution,
                                     self.context.http_base_url,
                                     valid_series)
        self.sources_list_entries = SourcesListEntriesView(entries,
                                                           self.request)

    @cachedproperty
    def probe_records(self):
        return BatchNavigator(self.context.all_probe_records, self.request)

    # Cached because it is used to construct the entries in initialize()
    @cachedproperty
    def summarized_arch_series(self):
        mirrors = self.context.getSummarizedMirroredArchSerieses()
        return sorted(
            mirrors, reverse=True,
            key=lambda mirror: Version(
                mirror.distro_arch_series.distroseries.version))

    @property
    def summarized_source_series(self):
        mirrors = self.context.getSummarizedMirroredSourceSerieses()
        return sorted(mirrors, reverse=True,
                      key=lambda mirror: Version(mirror.distroseries.version))

    def getCDImageMirroredFlavoursBySeries(self):
        """Return a list of _FlavoursByDistroSeries objects ordered
        descending by version.
        """
        serieses = {}
        for cdimage in self.context.cdimage_serieses:
            series, flavour = cdimage.distroseries, cdimage.flavour
            flavours_by_series = serieses.get(series)
            if flavours_by_series is None:
                flavours_by_series = _FlavoursByDistroSeries(series, [])
                serieses[series] = flavours_by_series
            flavours_by_series.flavours.append(flavour)
        flavours_by_serieses = serieses.values()
        return sorted(flavours_by_serieses, reverse=True,
                      key=lambda item: Version(item.distroseries.version))


class DistributionMirrorDeleteView(LaunchpadFormView):

    schema = IDistributionMirror
    field_names = []
    label = "Delete this distribution mirror"

    @action(_("Delete Mirror"), name="delete")
    def delete_action(self, action, data):
        # Although users will never be able to see/submit this form for a
        # mirror which has been probed already, they may have a stale page
        # and so we do this check here.
        if self.context.last_probe_record is not None:
            self.request.response.addInfoNotification(
                "This mirror has been probed and thus can't be deleted.")
            self.next_url = canonical_url(self.context)
            return

        self.next_url = canonical_url(self.context.distribution)
        self.request.response.addInfoNotification(
            "Mirror %s has been deleted." % self.context.title)
        self.context.destroySelf()

    @action(_("Cancel"), name="cancel")
    def cancel_action(self, action, data):
        self.next_url = canonical_url(self.context)


class DistributionMirrorAddView(LaunchpadFormView):

    schema = IDistributionMirror
    field_names = ["displayname", "description", "http_base_url",
                   "ftp_base_url", "rsync_base_url", "speed", "country",
                   "content", "official_candidate"]
    label = "Create a new distribution mirror"

    @action(_("Create Mirror"), name="create")
    def create_action(self, action, data):
        mirror = self.context.newMirror(
            owner=self.user, speed=data['speed'], country=data['country'],
            content=data['content'], displayname=data['displayname'],
            description=data['description'],
            http_base_url=data['http_base_url'],
            ftp_base_url=data['ftp_base_url'],
            rsync_base_url=data['rsync_base_url'],
            official_candidate=data['official_candidate'])

        self.next_url = canonical_url(mirror)
        notify(ObjectCreatedEvent(mirror))


class DistributionMirrorOfficialApproveView(LaunchpadEditFormView):

    schema = IDistributionMirror
    field_names = ['status', 'whiteboard']
    label = "Mark as official/unofficial"

    @action(_("Save"), name="save")
    def action_save(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class DistributionMirrorEditView(LaunchpadEditFormView):

    schema = IDistributionMirror
    field_names = ["name", "displayname", "description", "http_base_url",
                   "ftp_base_url", "rsync_base_url", "speed", "country",
                   "content", "official_candidate"]
    label = "Change mirror details"

    @action(_("Save"), name="save")
    def action_save(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class DistributionMirrorReassignmentView(ObjectReassignmentView):

    @property
    def contextName(self):
        return self.context.title

