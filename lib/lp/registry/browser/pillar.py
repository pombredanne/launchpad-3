# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Common views for objects that implement `IPillar`."""

__metaclass__ = type

__all__ = [
    'PillarView',
    ]


from operator import attrgetter

from zope.component import provideAdapter
from zope.interface import implements, Interface

from canonical.launchpad.webapp.interfaces import INavigationMenu
from canonical.launchpad.webapp.menu import Link, NavigationMenu
from canonical.launchpad.webapp.publisher import LaunchpadView, nearest
from canonical.launchpad.webapp.tales import MenuAPI

from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from lp.registry.interfaces.pillar import IPillar
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.project import IProject


class IInvolved(Interface):
    """A marker interface for getting involved."""


class InvolvedMenu(NavigationMenu):
    """The get involved menu."""
    usedfor = IInvolved
    links = [
        'report_bug', 'ask_question', 'help_translate', 'submit_code',
        'register_blueprint']

    def report_bug(self):
        return Link(
            '+filebug', 'Report a bug', site='bugs', icon='bugs',
            enabled=self.context.official_malone)

    def ask_question(self):
        return Link(
            '+addquestion', 'Ask a question', site='answers', icon='answers',
            enabled=self.context.official_answers)

    def help_translate(self):
        return Link(
            '', 'Help translate', site='translations', icon='translations',
            enabled=self.context.official_rosetta)

    def submit_code(self):
        return Link(
            '+addbranch', 'Submit code', site='code', icon='code',
            enabled=self.context.official_codehosting)

    def register_blueprint(self):
        return Link(
            '+addspec', 'Register a blueprint', site='blueprints',
            icon='blueprints', enabled=self.context.official_blueprints)


class PillarView(LaunchpadView):
    """A view for any `IPillar`."""
    implements(IInvolved)

    def __init__(self, context, request):
        super(PillarView, self).__init__(context, request)
        self.official_malone = False
        self.official_answers = False
        self.official_blueprints = False
        self.official_rosetta = False
        self.official_codehosting = False
        pillar = nearest(self.context, IPillar)
        if IProject.providedBy(pillar):
            for product in pillar.products:
                self._set_official_launchpad(product)
            # Projectgroups do not support submit code, override the
            # default.
            self.official_codehosting = False
        else:
            self._set_official_launchpad(pillar)
            if IProductSeries.providedBy(self.context):
                self.official_answers = False
            elif IDistroSeries.providedBy(self.context):
                self.official_answers = False
                self.official_codehosting = False
            elif IDistributionSourcePackage.providedBy(self.context):
                self.official_blueprints = False
                self.official_rosetta = False
            else:
                # The context is used by all apps.
                pass

    def _set_official_launchpad(self, pillar):
        """Does the pillar officially use launchpad."""
        # This if structure is required because it may be called many
        # times to build the complete set of official applications.
        if pillar.official_malone:
            self.official_malone = True
        if pillar.official_answers:
            self.official_answers = True
        if pillar.official_blueprints:
            self.official_blueprints = True
        if pillar.official_rosetta:
            self.official_rosetta = True
        if pillar.official_codehosting:
            self.official_codehosting = True

    @property
    def has_involvement(self):
        """This `IPillar` uses Launchpad."""
        return (
            self.official_malone or self.official_answers
            or self.official_blueprints or self.official_rosetta
            or self.official_codehosting)

    @property
    def enabled_links(self):
        """The enabled involvement links."""
        menuapi = MenuAPI(self)
        return sorted([
            link for link in menuapi.navigation.values() if link.enabled],
            key=attrgetter('sort_key'))


provideAdapter(
    InvolvedMenu, [IInvolved], INavigationMenu, name="overview")
