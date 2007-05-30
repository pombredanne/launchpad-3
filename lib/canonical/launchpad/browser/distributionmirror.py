# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['DistributionMirrorEditView', 'DistributionMirrorFacets',
           'DistributionMirrorOverviewMenu', 'DistributionMirrorAddView',
           'DistributionMirrorView', 'DistributionMirrorOfficialApproveView',
           'DistributionMirrorReassignmentView']

from zope.app.event.objectevent import ObjectCreatedEvent
from zope.event import notify

from sourcerer.deb.version import Version

from canonical.launchpad import _
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, enabled_with_permission,
    LaunchpadEditFormView, LaunchpadFormView, Link, StandardLaunchpadFacets)
from canonical.launchpad.interfaces import IDistributionMirror
from canonical.launchpad.browser.person import ObjectReassignmentView
from canonical.cachedproperty import cachedproperty


class DistributionMirrorFacets(StandardLaunchpadFacets):

    usedfor = IDistributionMirror
    enable_only = ['overview']


class DistributionMirrorOverviewMenu(ApplicationMenu):

    usedfor = IDistributionMirror
    facet = 'overview'
    links = ['proberlogs', 'edit', 'admin', 'reassign']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def proberlogs(self):
        text = 'Prober logs'
        return Link('+prober-logs', text, icon='info')

    @enabled_with_permission('launchpad.Admin')
    def reassign(self):
        text = 'Change owner'
        return Link('+reassign', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
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

    @cachedproperty
    def probe_records(self):
        return BatchNavigator(self.context.all_probe_records, self.request)

    def getSummarizedMirroredSourceSerieses(self):
        mirrors = self.context.getSummarizedMirroredSourceSerieses()
        return sorted(mirrors, reverse=True,
                      key=lambda mirror: Version(mirror.distroseries.version))

    def getSummarizedMirroredArchSerieses(self):
        mirrors = self.context.getSummarizedMirroredArchSerieses()
        return sorted(
            mirrors, reverse=True,
            key=lambda mirror: Version(
                mirror.distro_arch_series.distroseries.version))

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


class DistributionMirrorAddView(LaunchpadFormView):

    schema = IDistributionMirror
    field_names = ["displayname", "http_base_url", "ftp_base_url",
                   "rsync_base_url", "speed", "country", "content",
                   "official_candidate"]
    label = "Create a new distribution mirror"

    @action(_("Create Mirror"), name="create")
    def create_action(self, action, data):
        mirror = self.context.newMirror(
            owner=self.user, speed=data['speed'], country=data['country'],
            content=data['content'], displayname=data['displayname'],
            http_base_url=data['http_base_url'],
            ftp_base_url=data['ftp_base_url'],
            rsync_base_url=data['rsync_base_url'],
            official_candidate=data['official_candidate'])

        self.next_url = canonical_url(mirror)
        notify(ObjectCreatedEvent(mirror))


class DistributionMirrorOfficialApproveView(LaunchpadEditFormView):

    schema = IDistributionMirror
    field_names = ['official_approved']
    label = "Mark as official"

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

