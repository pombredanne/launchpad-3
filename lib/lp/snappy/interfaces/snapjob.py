# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap job interfaces."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ISnapJob',
    'ISnapRequestBuildsJob',
    'ISnapRequestBuildsJobSource',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Dict,
    List,
    TextLine,
    )

from lp import _
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )
from lp.snappy.interfaces.snap import ISnap
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.soyuz.interfaces.archive import IArchive


class ISnapJob(Interface):
    """A job related to a snap package."""

    job = Reference(
        title=_("The common Job attributes."), schema=IJob,
        required=True, readonly=True)

    snap = Reference(
        title=_("The snap package to use for this job."),
        schema=ISnap, required=True, readonly=True)

    metadata = Attribute(_("A dict of data about the job."))


class ISnapRequestBuildsJob(IRunnableJob):
    """A Job that processes a request for builds of a snap package."""

    requester = Reference(
        title=_("The person requesting the builds."), schema=IPerson,
        required=True, readonly=True)

    archive = Reference(
        title=_("The archive to associate the builds with."), schema=IArchive,
        required=True, readonly=True)

    pocket = Choice(
        title=_("The pocket that should be targeted."),
        vocabulary=PackagePublishingPocket, required=True, readonly=True)

    channels = Dict(
        title=_("Source snap channels to use for these builds."),
        description=_(
            "A dictionary mapping snap names to channels to use for these "
            "builds.  Currently only 'core' and 'snapcraft' keys are "
            "supported."),
        key_type=TextLine(), required=False, readonly=True)

    error_message = TextLine(
        title=_("Error message resulting from running this job."),
        required=False, readonly=True)

    builds = List(
        title=_("The builds created by this request."),
        value_type=Reference(schema=ISnapBuild), required=True, readonly=True)


class ISnapRequestBuildsJobSource(IJobSource):

    def create(snap, requester, archive, pocket, channels):
        """Request builds of a snap package.

        :param snap: The snap package to build.
        :param requester: The person requesting the builds.
        :param archive: The IArchive to associate the builds with.
        :param pocket: The pocket that should be targeted.
        :param channels: A dictionary mapping snap names to channels to use
            for these builds.
        """

    def findBySnap(snap, statuses=None, job_ids=None):
        """Find jobs for a snap.

        :param snap: A snap package to search for.
        :param statuses: An optional iterable of `JobStatus`es to search for.
        :param job_ids: An optional iterable of job IDs to search for.
        :return: A sequence of `SnapRequestBuildsJob`s with the specified
            snap.
        """

    def getBySnapAndID(snap, job_id):
        """Get a job by snap and job ID.

        :return: The `SnapRequestBuildsJob` with the specified snap and ID.
        :raises: `NotFoundError` if there is no job with the specified snap
            and ID, or its `job_type` is not `SnapJobType.REQUEST_BUILDS`.
        """

    def findBuildsForJobs(jobs):
        """Find builds resulting from an iterable of `SnapRequestBuildJob`s.

        :return: A dictionary mapping `SnapRequestBuildJob` IDs to lists of
            their resulting builds.
        """
