# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Common views for objects that implement `IPillar`."""

__metaclass__ = type

__all__ = [
    'InvolvedMenu',
    'PillarBugsMenu',
    'PillarView',
    'PillarNavigationMixin',
    'PillarPersonSharingView',
    'PillarSharingView',
    ]


from operator import attrgetter
import simplejson

from lazr.restful import ResourceJSONEncoder
from lazr.restful.interfaces._rest import IJSONRequestCache

from zope.component import getUtility
from zope.interface import (
    implements,
    Interface,
    )
from zope.schema.interfaces import IVocabulary
from zope.schema.vocabulary import getVocabularyRegistry
from zope.security.interfaces import Unauthorized

from lp.app.browser.tales import MenuAPI
from lp.app.enums import (
    service_uses_launchpad,
    ServiceUsage,
    )
from lp.app.browser.vocabulary import vocabulary_filters
from lp.app.interfaces.launchpad import IServiceUsage
from lp.app.interfaces.services import IService
from lp.bugs.browser.structuralsubscription import (
    StructuralSubscriptionMenuMixin,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessPolicyGrantFlatSource,
    IAccessPolicySource,
    )
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.pillar import IPillar
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.person import IPersonSet
from lp.registry.model.pillar import PillarPerson
from lp.services.propertycache import cachedproperty
from lp.services.features import getFeatureFlag
from lp.services.webapp.authorization import check_permission
from lp.services.webapp import (
    ApplicationMenu,
    enabled_with_permission,
    Link,
    NavigationMenu,
    stepthrough,
    )
from lp.services.webapp.publisher import (
    LaunchpadView,
    nearest,
    )


class PillarNavigationMixin:

    @stepthrough('+sharingdetails')
    def traverse_details(self, name):
        """Traverse to the sharing details for a given person."""
        person = getUtility(IPersonSet).getByName(name)
        if person is None:
            return None
        policies = getUtility(IAccessPolicySource).findByPillar([self.context])
        source = getUtility(IAccessPolicyGrantFlatSource)
        artifacts = source.findArtifactsByGrantee(person, policies)
        if artifacts.is_empty():
            return None
        return PillarPerson.create(self.context, person)


class IInvolved(Interface):
    """A marker interface for getting involved."""


class InvolvedMenu(NavigationMenu):
    """The get involved menu."""
    usedfor = IInvolved
    links = [
        'report_bug', 'ask_question', 'help_translate', 'register_blueprint']

    @property
    def pillar(self):
        return self.context

    def report_bug(self):
        return Link(
            '+filebug', 'Report a bug', site='bugs', icon='bugs',
            enabled=self.pillar.official_malone)

    def ask_question(self):
        return Link(
            '+addquestion', 'Ask a question', site='answers', icon='answers',
            enabled=service_uses_launchpad(self.pillar.answers_usage))

    def help_translate(self):
        return Link(
            '', 'Help translate', site='translations', icon='translations',
            enabled=service_uses_launchpad(self.pillar.translations_usage))

    def register_blueprint(self):
        return Link(
            '+addspec',
            'Register a blueprint',
            site='blueprints',
            icon='blueprints',
            enabled=service_uses_launchpad(self.pillar.blueprints_usage))


class PillarView(LaunchpadView):
    """A view for any `IPillar`."""
    implements(IInvolved)

    configuration_links = []
    visible_disabled_link_names = []

    def __init__(self, context, request):
        super(PillarView, self).__init__(context, request)
        self.official_malone = False
        self.answers_usage = ServiceUsage.UNKNOWN
        self.blueprints_usage = ServiceUsage.UNKNOWN
        self.translations_usage = ServiceUsage.UNKNOWN
        self.codehosting_usage = ServiceUsage.UNKNOWN
        pillar = nearest(self.context, IPillar)

        self._set_official_launchpad(pillar)
        if IDistroSeries.providedBy(self.context):
            distribution = self.context.distribution
            self.codehosting_usage = distribution.codehosting_usage
            self.answers_usage = ServiceUsage.NOT_APPLICABLE
        elif IDistributionSourcePackage.providedBy(self.context):
            self.blueprints_usage = ServiceUsage.UNKNOWN
            self.translations_usage = ServiceUsage.UNKNOWN
        elif IProjectGroup.providedBy(pillar):
            # XXX: 2010-10-07 EdwinGrubbs bug=656292
            # Fix _set_official_launchpad().

            # Project groups do not support submit code, override the
            # default.
            self.codehosting_usage = ServiceUsage.NOT_APPLICABLE
        else:
            # The context is used by all apps.
            pass

    def _set_official_launchpad(self, pillar):
        """Does the pillar officially use launchpad."""
        # XXX: 2010-10-07 EdwinGrubbs bug=656292
        # Fix _set_official_launchpad().
        # This if structure is required because it may be called many
        # times to build the complete set of official applications.
        if service_uses_launchpad(IServiceUsage(pillar).bug_tracking_usage):
            self.official_malone = True
        if service_uses_launchpad(IServiceUsage(pillar).answers_usage):
            self.answers_usage = ServiceUsage.LAUNCHPAD
        if service_uses_launchpad(IServiceUsage(pillar).blueprints_usage):
            self.blueprints_usage = ServiceUsage.LAUNCHPAD
        if service_uses_launchpad(pillar.translations_usage):
            self.translations_usage = ServiceUsage.LAUNCHPAD
        if service_uses_launchpad(IServiceUsage(pillar).codehosting_usage):
            self.codehosting_usage = ServiceUsage.LAUNCHPAD

    @property
    def has_involvement(self):
        """This `IPillar` uses Launchpad."""
        return (self.official_malone
            or service_uses_launchpad(self.answers_usage)
            or service_uses_launchpad(self.blueprints_usage)
            or service_uses_launchpad(self.translations_usage)
            or service_uses_launchpad(self.codehosting_usage))

    @property
    def enabled_links(self):
        """The enabled involvement links."""
        menuapi = MenuAPI(self)
        return sorted([
            link for link in menuapi.navigation.values() if link.enabled],
            key=attrgetter('sort_key'))

    @cachedproperty
    def visible_disabled_links(self):
        """Important disabled links.

        These are displayed to notify the user to provide configuration
        info to enable the links.

        Override the visible_disabled_link_names attribute to change
        the results.
        """
        involved_menu = MenuAPI(self).navigation
        important_links = [
            involved_menu[name]
            for name in self.visible_disabled_link_names]
        return sorted([
            link for link in important_links if not link.enabled],
            key=attrgetter('sort_key'))

    @property
    def registration_completeness(self):
        """The percent complete for registration.

        Not used by all pillars.
        """
        return None


class PillarBugsMenu(ApplicationMenu, StructuralSubscriptionMenuMixin):
    """Base class for pillar bugs menus."""

    facet = 'bugs'
    configurable_bugtracker = False

    @enabled_with_permission('launchpad.Edit')
    def bugsupervisor(self):
        text = 'Change bug supervisor'
        return Link('+bugsupervisor', text, icon='edit')

    def cve(self):
        text = 'CVE reports'
        return Link('+cve', text, icon='cve')

    def filebug(self):
        text = 'Report a bug'
        return Link('+filebug', text, icon='bug')

    @enabled_with_permission('launchpad.Edit')
    def securitycontact(self):
        text = 'Change security contact'
        return Link('+securitycontact', text, icon='edit')


class PillarSharingView(LaunchpadView):

    page_title = "Sharing"
    label = "Sharing information"

    related_features = (
        'disclosure.enhanced_sharing.enabled',
        'disclosure.enhanced_sharing.writable',
        )

    def _getSharingService(self):
        return getUtility(IService, 'sharing')

    @property
    def information_types(self):
        return self._getSharingService().getInformationTypes(self.context)

    @property
    def sharing_permissions(self):
        return self._getSharingService().getSharingPermissions()

    @cachedproperty
    def sharing_vocabulary(self):
        registry = getVocabularyRegistry()
        return registry.get(
            IVocabulary, 'ValidPillarOwner')

    @cachedproperty
    def sharing_vocabulary_filters(self):
        return vocabulary_filters(self.sharing_vocabulary)

    @property
    def sharing_picker_config(self):
        return dict(
            vocabulary='ValidPillarOwner',
            vocabulary_filters=self.sharing_vocabulary_filters,
            header='Share with a user or team')

    @property
    def json_sharing_picker_config(self):
        return simplejson.dumps(
            self.sharing_picker_config, cls=ResourceJSONEncoder)

    @property
    def sharee_data(self):
        return self._getSharingService().getPillarSharees(self.context)

    def initialize(self):
        super(PillarSharingView, self).initialize()
        enabled_readonly_flag = 'disclosure.enhanced_sharing.enabled'
        enabled_writable_flag = (
            'disclosure.enhanced_sharing.writable')
        enabled = bool(getFeatureFlag(enabled_readonly_flag))
        write_flag_enabled = bool(getFeatureFlag(enabled_writable_flag))
        if not enabled and not write_flag_enabled:
            raise Unauthorized("This feature is not yet available.")
        cache = IJSONRequestCache(self.request)
        cache.objects['sharing_write_enabled'] = (write_flag_enabled
            and check_permission('launchpad.Edit', self.context))
        cache.objects['information_types'] = self.information_types
        cache.objects['sharing_permissions'] = self.sharing_permissions
        cache.objects['sharee_data'] = self.sharee_data


class PillarPersonSharingView(LaunchpadView):

    page_title = "Person or team"
    label = "Information shared with person or team"

    def initialize(self):
        enabled_flag = 'disclosure.enhanced_sharing.enabled'
        enabled = bool(getFeatureFlag(enabled_flag))
        if not enabled:
            raise Unauthorized("This feature is not yet available.")

        self.pillar = self.context.pillar
        self.person = self.context.person

        self.label = "Information shared with %s" % self.person.displayname
        self.page_title = "%s" % self.person.displayname
