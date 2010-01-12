# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'ISourcePackageBuild',
    'ISourcePackageBuildSource',
    ]

from lazr.restful.fields import Reference

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Object, Timedelta

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias

from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.builder import IBuilder
from lp.soyuz.interfaces.sourcepackagerecipe import ISourcePackageRecipe


class ISourcePackageBuild(Interface):
    """A build of a source package."""

    # XXX: possibly move to a base class shared w/ IBuild
    date_created = Datetime(required=True, readonly=True)

    distroseries = Reference(
        IDistroSeries, title=_(
            "The distroseries this will build a source package for"),
        readonly=True)

    sourcepackagename = Reference(
        ISourcePackageName,
        title=_("The name of the source package will build"),
        readonly=True)

    # XXX: possibly move to a base class shared w/ IBuild. Maybe. It's got
    # some deb-specific stuff.
    build_state = Choice(
        title=_('State'), required=True, vocabulary=BuildStatus,
        description=_("The current build state."))

    # XXX: possibly move to a base class shared w/ IBuild
    date_built = Datetime(required=False)

    # XXX: possibly move to a base class shared w/ IBuild
    build_duration = Timedelta(
        title=_("Build Duration"), required=False,
        description=_("Build duration interval, calculated when the "
                      "build result gets collected."))

    # XXX: possibly move to a base class shared w/ IBuild
    build_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the entire buildlog."))

    # XXX: possibly move to a base class shared w/ IBuild
    builder = Object(
        title=_("Builder"), schema=IBuilder, required=False,
        description=_("The Builder which address this build request."))

    # XXX: possibly move to a base class shared w/ IBuild
    date_first_dispatched = Datetime(
        title=_('Date first dispatched'), required=False,
        description=_("The actual build start time. Set when the build "
                      "is dispatched the first time and not changed in "
                      "subsequent build attempts."))

    requester = Object(
        schema=IPerson, required=False,
        title=_("The person who wanted to do this."))

    recipe = Object(
        schema=ISourcePackageRecipe, required=True,
        title=_("The recipe being built."))

    manifest = Attribute(_("The manifest of the built package."))


class ISourcePackageBuildSource(Interface):
    """A utility of this interface be used to create source package builds."""

    def new():
        """Create an `ISourcePackageBuild`."""
