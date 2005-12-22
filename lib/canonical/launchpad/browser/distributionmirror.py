# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['DistributionMirrorEditView', 'DistributionMirrorFacets',
           'DistributionMirrorOverviewMenu', 'DistributionMirrorAddSourceView',
           'DistributionMirrorAddArchView']

from zope.app.form.interfaces import WidgetsError
from zope.event import notify

from canonical.launchpad import _
from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, Link, ApplicationMenu, 
    enabled_with_permission)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.interfaces import IDistributionMirror
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.lp.dbschema import MirrorPulseType


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


class DistributionMirrorEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))

    def doSchemaValidation(self, data):
        # XXX: This code can probably be moved somewhere else so it can be
        # shared with DistributionAddMirrorView.createAndAdd().
        # -- Guilherme Salgado, 2005-12-21
        errors = []
        if (data['pulse_type'] == MirrorPulseType.PULL and
            not data['pulse_source']):
            errors.append(LaunchpadValidationError(_(
                "You have choosen 'Pull' as the pulse type but have not "
                "supplied a pulse source.")))

        if not (data['http_base_url'] or data['ftp_base_url']
                or data['rsync_base_url']):
            errors.append(
                LaunchpadValidationError(_(
                    "All mirrors require at least one URL (HTTP, FTP or "
                    "Rsync) to be specified.")))

        if errors:
            raise WidgetsError(errors)


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

