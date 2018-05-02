# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An `IBuildFarmJobBehaviour` for `SnapBuild`.

Dispatches snap package build jobs to build-farm slaves.
"""

__metaclass__ = type
__all__ = [
    'SnapBuildBehaviour',
    ]

import base64
import json
import time

from twisted.internet import defer
from twisted.web.client import getPage
from zope.component import adapter
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.model.buildfarmjobbehaviour import (
    BuildFarmJobBehaviourBase,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.services.config import config
from lp.services.webapp import canonical_url
from lp.snappy.interfaces.snap import SnapBuildArchiveOwnerMismatch
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building,
    )
from lp.soyuz.interfaces.archive import ArchiveDisabled


@adapter(ISnapBuild)
@implementer(IBuildFarmJobBehaviour)
class SnapBuildBehaviour(BuildFarmJobBehaviourBase):
    """Dispatches `SnapBuild` jobs to slaves."""

    builder_type = "snap"

    def getLogFileName(self):
        das = self.build.distro_arch_series

        # Examples:
        #   buildlog_snap_ubuntu_wily_amd64_name_FULLYBUILT.txt
        return 'buildlog_snap_%s_%s_%s_%s_%s.txt' % (
            das.distroseries.distribution.name, das.distroseries.name,
            das.architecturetag, self.build.snap.name, self.build.status.name)

    def verifyBuildRequest(self, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
         * The source archive may not be disabled
         * If the source archive is private, the snap owner must match the
           archive owner (see `SnapBuildArchiveOwnerMismatch` docstring)
         * Ensure that we have a chroot
        """
        build = self.build
        if build.virtualized and not self._builder.virtualized:
            raise AssertionError(
                "Attempt to build virtual item on a non-virtual builder.")

        if not build.archive.enabled:
            raise ArchiveDisabled(build.archive.displayname)
        if build.archive.private and build.snap.owner != build.archive.owner:
            raise SnapBuildArchiveOwnerMismatch()

        chroot = build.distro_arch_series.getChroot()
        if chroot is None:
            raise CannotBuild(
                "Missing chroot for %s" % build.distro_arch_series.displayname)

    @defer.inlineCallbacks
    def extraBuildArgs(self, logger=None):
        """
        Return the extra arguments required by the slave for the given build.
        """
        build = self.build
        args = yield super(SnapBuildBehaviour, self).extraBuildArgs(
            logger=logger)
        if config.snappy.builder_proxy_host and build.snap.allow_internet:
            token = yield self._requestProxyToken()
            args["proxy_url"] = (
                "http://{username}:{password}@{host}:{port}".format(
                    username=token['username'],
                    password=token['secret'],
                    host=config.snappy.builder_proxy_host,
                    port=config.snappy.builder_proxy_port))
            args["revocation_endpoint"] = (
                "{endpoint}/{token}".format(
                    endpoint=config.snappy.builder_proxy_auth_api_endpoint,
                    token=token['username']))
        args["name"] = build.snap.store_name or build.snap.name
        args["series"] = build.distro_series.name
        args["arch_tag"] = build.distro_arch_series.architecturetag
        # XXX cjwatson 2015-08-03: Allow tools_source to be overridden at
        # some more fine-grained level.
        args["archives"], args["trusted_keys"] = (
            yield get_sources_list_for_building(
                build, build.distro_arch_series, None,
                tools_source=config.snappy.tools_source,
                tools_fingerprint=config.snappy.tools_fingerprint,
                logger=logger))
        args["archive_private"] = build.archive.private
        args["build_url"] = canonical_url(build)
        if build.channels is not None:
            # We have to remove the security proxy that Zope applies to this
            # dict, since otherwise we'll be unable to serialise it to
            # XML-RPC.
            args["channels"] = removeSecurityProxy(build.channels)
        if build.snap.branch is not None:
            args["branch"] = build.snap.branch.bzr_identity
        elif build.snap.git_ref is not None:
            if build.snap.git_ref.repository_url is not None:
                args["git_repository"] = build.snap.git_ref.repository_url
            else:
                args["git_repository"] = (
                    build.snap.git_repository.git_https_url)
            # "git clone -b" doesn't accept full ref names.  If this becomes
            # a problem then we could change launchpad-buildd to do "git
            # clone" followed by "git checkout" instead.
            if build.snap.git_path != u"HEAD":
                args["git_path"] = build.snap.git_ref.name
        else:
            raise CannotBuild(
                "Source branch/repository for ~%s/%s has been deleted." %
                (build.snap.owner.name, build.snap.name))
        args["build_source_tarball"] = build.snap.build_source_tarball
        defer.returnValue(args)

    @defer.inlineCallbacks
    def _requestProxyToken(self):
        admin_username = config.snappy.builder_proxy_auth_api_admin_username
        if not admin_username:
            raise CannotBuild(
                "builder_proxy_auth_api_admin_username is not configured.")
        secret = config.snappy.builder_proxy_auth_api_admin_secret
        if not secret:
            raise CannotBuild(
                "builder_proxy_auth_api_admin_secret is not configured.")
        url = config.snappy.builder_proxy_auth_api_endpoint
        if not secret:
            raise CannotBuild(
                "builder_proxy_auth_api_endpoint is not configured.")
        timestamp = int(time.time())
        proxy_username = '{build_id}-{timestamp}'.format(
            build_id=self.build.build_cookie,
            timestamp=timestamp)
        auth_string = '{}:{}'.format(admin_username, secret).strip()
        auth_header = 'Basic ' + base64.b64encode(auth_string)
        data = json.dumps({'username': proxy_username})

        result = yield getPage(
            url,
            method='POST',
            postdata=data,
            headers={
                'Authorization': auth_header,
                'Content-Type': 'application/json'}
            )
        token = json.loads(result)
        defer.returnValue(token)

    def verifySuccessfulBuild(self):
        """See `IBuildFarmJobBehaviour`."""
        # The implementation in BuildFarmJobBehaviourBase checks whether the
        # target suite is modifiable in the target archive.  However, a
        # `SnapBuild`'s archive is a source rather than a target, so that
        # check does not make sense.  We do, however, refuse to build for
        # obsolete series.
        assert self.build.distro_series.status != SeriesStatus.OBSOLETE
