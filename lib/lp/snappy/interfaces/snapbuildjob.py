# Copyright 2016-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap build job interfaces."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ISnapBuildJob',
    'ISnapBuildStoreUploadStatusChangedEvent',
    'ISnapStoreUploadJob',
    'ISnapStoreUploadJobSource',
    ]

from lazr.restful.fields import Reference
from zope.component.interfaces import IObjectEvent
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import TextLine

from lp import _
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuild


class ISnapBuildJob(Interface):
    """A job related to a snap package."""

    job = Reference(
        title=_("The common Job attributes."), schema=IJob,
        required=True, readonly=True)

    snapbuild = Reference(
        title=_("The snap build to use for this job."),
        schema=ISnapBuild, required=True, readonly=True)

    metadata = Attribute(_("A dict of data about the job."))


class ISnapBuildStoreUploadStatusChangedEvent(IObjectEvent):
    """The store upload status of a snap package build changed."""


class ISnapStoreUploadJob(IRunnableJob):
    """A Job that uploads a snap build to the store."""

    error_message = TextLine(
        title=_("Error message"), required=False, readonly=True)

    store_url = TextLine(
        title=_("The URL on the store corresponding to this build"),
        required=False, readonly=True)


class ISnapStoreUploadJobSource(IJobSource):

    def create(snapbuild):
        """Upload a snap build to the store.

        :param snapbuild: The snap build to upload.
        """
