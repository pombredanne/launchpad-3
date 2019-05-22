# Copyright 2015-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An `IBuildFarmJobBehaviour` for `SnapBuild`.

Dispatches snap package build jobs to build-farm slaves.
"""

__metaclass__ = type
__all__ = [
    'SnapBuildBehaviour',
    ]

import base64
import time

from six.moves.urllib.parse import (
    urlsplit,
    urlunsplit,
    )
import treq
from twisted.internet import defer
from zope.component import adapter
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import BuildBaseImageType
from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.model.buildfarmjobbehaviour import (
    BuildFarmJobBehaviourBase,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.services.config import config
from lp.services.features import getFeatureFlag
from lp.services.twistedsupport import cancel_on_timeout
from lp.services.twistedsupport.treq import check_status
from lp.snappy.interfaces.snap import (
    SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG,
    SnapBuildArchiveOwnerMismatch,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building,
    )
from lp.soyuz.interfaces.archive import ArchiveDisabled


def format_as_rfc3339(timestamp):
    """Return a RFC3339 representation of the given timestamp.

    Clear 'microsecond' and 'tzinfo' before returning its '.isoformat()'
    representation appended with 'Z' (https://www.ietf.org/rfc/rfc3339.txt)

    This is how snapd/SAS and snapcraft usually represent timestamps.
    """
    return timestamp.replace(microsecond=0, tzinfo=None).isoformat() + 'Z'


@adapter(ISnapBuild)
@implementer(IBuildFarmJobBehaviour)
class SnapBuildBehaviour(BuildFarmJobBehaviourBase):
    """Dispatches `SnapBuild` jobs to slaves."""

    builder_type = "snap"
    image_types = [BuildBaseImageType.LXD, BuildBaseImageType.CHROOT]

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

        chroot = build.distro_arch_series.getChroot(pocket=build.pocket)
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
        # XXX cjwatson 2015-08-03: Allow tools_source to be overridden at
        # some more fine-grained level.
        args["archives"], args["trusted_keys"] = (
            yield get_sources_list_for_building(
                build, build.distro_arch_series, None,
                tools_source=config.snappy.tools_source,
                tools_fingerprint=config.snappy.tools_fingerprint,
                logger=logger))
        channels = build.channels or {}
        if "snapcraft" not in channels:
            channels["snapcraft"] = (
                getFeatureFlag(SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG) or "apt")
        if channels.get("snapcraft") != "apt":
            # We have to remove the security proxy that Zope applies to this
            # dict, since otherwise we'll be unable to serialise it to
            # XML-RPC.
            args["channels"] = removeSecurityProxy(channels)
        if build.snap.branch is not None:
            args["branch"] = build.snap.branch.bzr_identity
        elif build.snap.git_ref is not None:
            if build.snap.git_ref.repository_url is not None:
                args["git_repository"] = build.snap.git_ref.repository_url
            elif build.snap.git_repository.private:
                macaroon_raw = yield cancel_on_timeout(
                    self._authserver.callRemote(
                        "issueMacaroon", "snap-build", "SnapBuild", build.id),
                    config.builddmaster.authentication_timeout)
                # XXX cjwatson 2019-03-07: This is ugly and needs
                # refactoring once we support more general HTTPS
                # authentication; see also comment in
                # GitRepository.git_https_url.
                split = urlsplit(build.snap.git_repository.getCodebrowseUrl())
                netloc = ":%s@%s" % (macaroon_raw, split.hostname)
                if split.port:
                    netloc += ":%s" % split.port
                args["git_repository"] = urlunsplit([
                    split.scheme, netloc, split.path, "", ""])
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
        args["private"] = build.is_private
        build_request = build.build_request
        if build_request is not None:
            args["build_request_id"] = build_request.id
            # RFC3339 format for timestamp
            # (matching snapd, SAS and snapcraft representation)
            timestamp = format_as_rfc3339(build_request.date_requested)
            args["build_request_timestamp"] = timestamp
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
        auth_header = b'Basic ' + base64.b64encode(auth_string)

        response = yield treq.post(
            url, headers={'Authorization': auth_header},
            json={'username': proxy_username},
            reactor=self._slave.reactor,
            pool=self._slave.pool)
        response = yield check_status(response)
        token = yield treq.json_content(response)
        defer.returnValue(token)

    def verifySuccessfulBuild(self):
        """See `IBuildFarmJobBehaviour`."""
        # The implementation in BuildFarmJobBehaviourBase checks whether the
        # target suite is modifiable in the target archive.  However, a
        # `SnapBuild`'s archive is a source rather than a target, so that
        # check does not make sense.  We do, however, refuse to build for
        # obsolete series.
        assert self.build.distro_series.status != SeriesStatus.OBSOLETE
