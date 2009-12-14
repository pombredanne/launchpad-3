# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []

from lazr.restful.fields import Reference
from lazr.restful.declarations import exported

from zope.interface import Interface
from zope.schema import (
    Choice, Datetime, Int, Object, Text, TextLine, Timedelta)

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias

from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.builder import IBuilder
from lp.soyuz.interfaces.sourcepackagerecipe import ISourcePackageRecipe


class ISourcePackageBuild(Interface):

    id = Int(readonly=True, required=True)

    date_created = Datetime(readonly=True, required=True)

    distroseries = exported(Reference(IDistroSeries, required=True))

    sourcepackagename = exported(Reference(ISourcePackageName))

    buildstate = exported(
        Choice(
            title=_('State'), required=True, vocabulary=BuildStatus,
            description=_("The current build state.")))

    date_built = exported(Datetime(required=False))

    build_duration = Timedelta(
        title=_("Build Duration"), required=False,
        description=_("Build duration interval, calculated when the "
                      "build result gets collected."))

    build_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the entire buildlog."))

    build_log_url = exported(
        TextLine(
            title=_("Build Log URL"), required=False,
            description=_("A URL for the build log. None if there is no "
                          "log available.")))

    builder = Object(
        title=_("Builder"), schema=IBuilder, required=False,
        description=_("The Builder which address this build request."))

    date_first_dispatched = exported(
        Datetime(
            title=_('Date first dispatched'), required=False,
            description=_("The actual build start time. Set when the build "
                          "is dispatched the first time and not changed in "
                          "subsequent build attempts.")))

    requester = exported(Reference(IPerson))

    recipe = exported(Reference(ISourcePackageRecipe, required=True))
    manifest = exported(Text())
