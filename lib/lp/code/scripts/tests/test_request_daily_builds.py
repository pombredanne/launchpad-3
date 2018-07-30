# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the request_daily_builds script."""

from collections import defaultdict
import json
import threading
from wsgiref.simple_server import (
    make_server,
    WSGIRequestHandler,
    )

from six.moves.urllib_parse import urlparse
import transaction

from lp.code.interfaces.codehosting import BRANCH_ID_ALIAS_PREFIX
from lp.services.config import config
from lp.services.config.fixture import (
    ConfigFixture,
    ConfigUseFixture,
    )
from lp.services.features.testing import FeatureFixture
from lp.services.scripts.tests import run_script
from lp.snappy.interfaces.snap import SNAP_TESTING_FLAGS
from lp.soyuz.enums import ArchivePurpose
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessAppServerLayer


class FakeLoggerheadApplication:
    """A WSGI application that provides some fake loggerhead endpoints."""

    def __init__(self):
        self.file_ids = defaultdict(dict)
        self.contents = defaultdict(dict)

    def _not_found(self, start_response):
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'']

    def __call__(self, environ, start_response):
        segments = environ['PATH_INFO'].lstrip('/').split('/')
        if len(segments) < 3 or segments[0] != BRANCH_ID_ALIAS_PREFIX:
            return self._not_found(start_response)
        try:
            branch_id = int(segments[1])
        except ValueError:
            return self._not_found(start_response)
        if segments[2:4] == ['+json', 'files']:
            if branch_id not in self.file_ids or len(segments) < 5:
                return self._not_found(start_response)
            directory = '/'.join(segments[5:])
            files = {
                path: file_id
                for path, file_id in self.file_ids[branch_id].items()
                if '/'.join(path.split('/')[:-1]) == directory
                }
            if not files:
                return self._not_found(start_response)
            response = {
                'filelist': [
                    {
                        'filename': path.split('/')[-1],
                        'file_id': file_id,
                        } for path, file_id in files.items()
                    ],
                }
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [json.dumps(response).encode('UTF-8')]
        elif segments[2:3] == ['download']:
            if branch_id not in self.contents or len(segments) != 5:
                return self._not_found(start_response)
            file_id = segments[4]
            if file_id not in self.contents[branch_id]:
                return self._not_found(start_response)
            start_response(
                '200 OK', [('Content-Type', 'application/octet-stream')])
            return [self.contents[branch_id][file_id]]
        else:
            return self._not_found(start_response)

    def addInventory(self, branch_id, path, file_id):
        self.file_ids[branch_id][path] = file_id

    def addBlob(self, branch_id, file_id, contents):
        self.contents[branch_id][file_id] = contents


class FakeLoggerheadRequestHandler(WSGIRequestHandler):
    """A request handler that doesn't log requests."""

    def log_message(self, fmt, *args):
        pass


class FakeLoggerheadServer(threading.Thread):
    """Thread that runs a fake loggerhead server."""

    def __init__(self, address):
        super(FakeLoggerheadServer, self).__init__()
        self.app = FakeLoggerheadApplication()
        self.server = make_server(
            address, 0, self.app, handler_class=FakeLoggerheadRequestHandler)

    def run(self):
        self.server.serve_forever()

    def getURL(self):
        host, port = self.server.server_address
        return 'http://%s:%d/' % (host, port)

    def addInventory(self, branch_id, path, file_id):
        self.app.addInventory(branch_id, path, file_id)

    def addBlob(self, branch_id, file_id, contents):
        self.app.addBlob(branch_id, file_id, contents)

    def stop(self):
        self.server.shutdown()


class TestRequestDailyBuilds(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def setUp(self):
        super(TestRequestDailyBuilds, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def makeLoggerheadServer(self):
        loggerhead_server = FakeLoggerheadServer(
            urlparse(config.codehosting.internal_bzr_api_endpoint).hostname)
        config_name = self.factory.getUniqueString()
        config_fixture = self.useFixture(ConfigFixture(
            config_name, self.layer.config_fixture.instance_name))
        setting_lines = [
            '[codehosting]',
            'internal_bzr_api_endpoint: %s' % loggerhead_server.getURL(),
            ]
        config_fixture.add_section('\n' + '\n'.join(setting_lines))
        self.useFixture(ConfigUseFixture(config_name))
        loggerhead_server.start()
        self.addCleanup(loggerhead_server.stop)
        return loggerhead_server

    def test_request_daily_builds(self):
        """Ensure the request_daily_builds script requests daily builds."""
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.factory.makeDistroArchSeries(
            processor=processor)
        fake_chroot = self.factory.makeLibraryFileAlias(
            filename="fake_chroot.tar.gz", db_only=True)
        distroarchseries.addOrUpdateChroot(fake_chroot)
        prod_branch = self.factory.makeProductBranch()
        prod_recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True, is_stale=True, branches=[prod_branch])
        prod_snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor],
            auto_build=True, is_stale=True, branch=prod_branch)
        pack_branch = self.factory.makePackageBranch()
        pack_recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True, is_stale=True, branches=[pack_branch])
        pack_snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor],
            auto_build=True, is_stale=True, branch=pack_branch)
        self.assertEqual(0, prod_recipe.pending_builds.count())
        self.assertEqual(0, prod_snap.pending_builds.count())
        self.assertEqual(0, pack_recipe.pending_builds.count())
        self.assertEqual(0, pack_snap.pending_builds.count())
        transaction.commit()
        loggerhead_server = self.makeLoggerheadServer()
        loggerhead_server.addInventory(prod_branch.id, 'snap', 'prod_snap')
        loggerhead_server.addInventory(
            prod_branch.id, 'snap/snapcraft.yaml', 'prod_snapcraft_yaml')
        loggerhead_server.addBlob(
            prod_branch.id, 'prod_snapcraft_yaml', b'name: prod-snap')
        loggerhead_server.addInventory(pack_branch.id, 'snap', 'pack_snap')
        loggerhead_server.addInventory(
            pack_branch.id, 'snap/snapcraft.yaml', 'pack_snapcraft_yaml')
        loggerhead_server.addBlob(
            pack_branch.id, 'pack_snapcraft_yaml', b'name: pack-snap')
        retcode, stdout, stderr = run_script(
            'cronscripts/request_daily_builds.py', [])
        self.assertIn('Requested 2 daily recipe builds.', stderr)
        self.assertIn('Requested 2 automatic snap package builds.', stderr)
        self.assertEqual(1, prod_recipe.pending_builds.count())
        self.assertEqual(1, prod_snap.pending_builds.count())
        self.assertEqual(1, pack_recipe.pending_builds.count())
        self.assertEqual(1, pack_snap.pending_builds.count())
        self.assertFalse(prod_recipe.is_stale)
        self.assertFalse(prod_snap.is_stale)
        self.assertFalse(pack_recipe.is_stale)
        self.assertFalse(pack_snap.is_stale)

    def test_request_daily_builds_oops(self):
        """Ensure errors are handled cleanly."""
        archive = self.factory.makeArchive(purpose=ArchivePurpose.COPY)
        recipe = self.factory.makeSourcePackageRecipe(
            daily_build_archive=archive, build_daily=True)
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/request_daily_builds.py', [])
        self.assertEqual(0, recipe.pending_builds.count())
        self.assertIn('Requested 0 daily recipe builds.', stderr)
        self.assertIn('Requested 0 automatic snap package builds.', stderr)
        self.oops_capture.sync()
        self.assertEqual('NonPPABuildRequest', self.oopses[0]['type'])
        self.assertEqual(
            1, len(self.oopses), "Too many OOPSes: %r" % (self.oopses,))
