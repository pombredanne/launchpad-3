# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['DistributionMirrorEditView', 'DistributionMirrorFacets',
           'DistributionMirrorOverviewMenu', 'DistributionMirrorAddSourceView',
           'DistributionMirrorAddArchView', 'DistributionMirrorAddView']

from zope.app.event.objectevent import ObjectCreatedEvent
from zope.event import notify

from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, Link, ApplicationMenu, 
    enabled_with_permission)
from canonical.launchpad.interfaces import (
    IDistributionMirror, validate_distribution_mirror_schema)
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.browser.editview import SQLObjectEditView


class DistributionMirrorFacets(StandardLaunchpadFacets):

    usedfor = IDistributionMirror
    enable_only = ['overview']


class DistributionMirrorOverviewMenu(ApplicationMenu):

    usedfor = IDistributionMirror
    facet = 'overview'
    links = ['edit', 'admin', 'addarchrelease', 'addsourcerelease']

    def addarchrelease(self):
        text = 'Register Arch Release'
        return Link('+addarchrelease', text, icon='add')

    def addsourcerelease(self):
        text = 'Register Source Release'
        return Link('+addsourcerelease', text, icon='add')

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer this Mirror'
        return Link('+admin', text, icon='edit')


class DistributionMirrorAddView(GeneralFormView):

    # XXX: This is a workaround while
    # https://launchpad.net/products/launchpad/+bug/5792 isn't fixed.
    __launchpad_facetname__ = 'overview'

    def doSchemaValidation(self, form_values):
        validate_distribution_mirror_schema(form_values)

    def process(self, owner, name, displayname, description, speed, country,
                content, http_base_url, ftp_base_url, rsync_base_url,
                pulse_type, pulse_source, enabled, official_candidate):
        mirror = self.context.newMirror(
            owner=owner, name=name, speed=speed, country=country,
            content=content, pulse_type=pulse_type, displayname=displayname,
            description=description, http_base_url=http_base_url,
            ftp_base_url=ftp_base_url, rsync_base_url=rsync_base_url,
            official_candidate=official_candidate, enabled=enabled,
            pulse_source=pulse_source)

        self._nextURL = canonical_url(mirror)
        notify(ObjectCreatedEvent(mirror))
        return mirror
        

class DistributionMirrorEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))

    def doSchemaValidation(self, form_values):
        validate_distribution_mirror_schema(form_values)


class DistributionMirrorAddSourceView(GeneralFormView):

    # XXX: This is a workaround while
    # https://launchpad.net/products/launchpad/+bug/5792 isn't fixed.
    __launchpad_facetname__ = 'overview'

    def process(self, distro_release):
        notify(SQLObjectCreatedEvent(
            self.context.newMirrorSourceRelease(distro_release)))
        self._nextURL = canonical_url(self.context)


class DistributionMirrorAddArchView(GeneralFormView):

    # XXX: This is a workaround while
    # https://launchpad.net/products/launchpad/+bug/5792 isn't fixed.
    __launchpad_facetname__ = 'overview'

    def process(self, distro_arch_release, pocket):
        notify(SQLObjectCreatedEvent(
            self.context.newMirrorArchRelease(distro_arch_release, pocket)))
        self._nextURL = canonical_url(self.context)

