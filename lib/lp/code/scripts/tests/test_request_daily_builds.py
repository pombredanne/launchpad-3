# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the request_daily_builds script."""

import base64
from collections import defaultdict
import json
import threading
from wsgiref.simple_server import (
    make_server,
    WSGIRequestHandler,
    )

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


class SilentWSGIRequestHandler(WSGIRequestHandler):
    """A request handler that doesn't log requests."""

    def log_message(self, fmt, *args):
        pass


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


class FakeLoggerheadServer(threading.Thread):
    """Thread that runs a fake loggerhead server."""

    def __init__(self):
        super(FakeLoggerheadServer, self).__init__()
        self.app = FakeLoggerheadApplication()
        self.server = make_server(
            'localhost', 0, self.app, handler_class=SilentWSGIRequestHandler)

    def run(self):
        self.server.serve_forever()

    def getURL(self):
        host, port = self.server.server_address
        return 'http://%s:%d/' % (host, port)

    def addInventory(self, branch, path, file_id):
        self.app.addInventory(branch.id, path, file_id)

    def addBlob(self, branch, file_id, contents):
        self.app.addBlob(branch.id, file_id, contents)

    def stop(self):
        self.server.shutdown()


class FakeTurnipApplication:
    """A WSGI application that provides some fake turnip endpoints."""

    def __init__(self):
        self.contents = defaultdict(dict)

    def _not_found(self, start_response):
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'']

    def __call__(self, environ, start_response):
        segments = environ['PATH_INFO'].lstrip('/').split('/')
        if (len(segments) < 4 or
                segments[0] != 'repo' or segments[2] != 'blob'):
            return self._not_found(start_response)
        repository_id = segments[1]
        if repository_id not in self.contents:
            return self._not_found(start_response)
        filename = '/'.join(segments[3:])
        if filename not in self.contents[repository_id]:
            return self._not_found(start_response)
        blob = self.contents[repository_id][filename]
        response = {'size': len(blob), 'data': base64.b64encode(blob)}
        start_response(
            '200 OK', [('Content-Type', 'application/octet-stream')])
        return [json.dumps(response).encode('UTF-8')]

    def addBlob(self, repository, filename, contents):
        self.contents[repository.getInternalPath()][filename] = contents


class FakeTurnipServer(threading.Thread):
    """Thread that runs a fake turnip server."""

    def __init__(self):
        super(FakeTurnipServer, self).__init__()
        self.app = FakeTurnipApplication()
        self.server = make_server(
            'localhost', 0, self.app, handler_class=SilentWSGIRequestHandler)

    def run(self):
        self.server.serve_forever()

    def getURL(self):
        host, port = self.server.server_address
        return 'http://%s:%d/' % (host, port)

    def addBlob(self, repository_id, filename, contents):
        self.app.addBlob(repository_id, filename, contents)

    def stop(self):
        self.server.shutdown()


class TestRequestDailyBuilds(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def setUp(self):
        super(TestRequestDailyBuilds, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def makeLoggerheadServer(self):
        loggerhead_server = FakeLoggerheadServer()
        config_name = self.factory.getUniqueString()
        config_fixture = self.useFixture(ConfigFixture(
            config_name, config.instance_name))
        setting_lines = [
            '[codehosting]',
            'internal_bzr_api_endpoint: %s' % loggerhead_server.getURL(),
            ]
        config_fixture.add_section('\n' + '\n'.join(setting_lines))
        self.useFixture(ConfigUseFixture(config_name))
        loggerhead_server.start()
        self.addCleanup(loggerhead_server.stop)
        return loggerhead_server

    def makeTurnipServer(self):
        turnip_server = FakeTurnipServer()
        config_name = self.factory.getUniqueString()
        config_fixture = self.useFixture(ConfigFixture(
            config_name, config.instance_name))
        setting_lines = [
            '[codehosting]',
            'internal_git_api_endpoint: %s' % turnip_server.getURL(),
            ]
        config_fixture.add_section('\n' + '\n'.join(setting_lines))
        self.useFixture(ConfigUseFixture(config_name))
        turnip_server.start()
        self.addCleanup(turnip_server.stop)
        return turnip_server

    def test_request_daily_builds(self):
        """Ensure the request_daily_builds script requests daily builds."""
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.factory.makeDistroArchSeries(
            processor=processor)
        fake_chroot = self.factory.makeLibraryFileAlias(
            filename="fake_chroot.tar.gz", db_only=True)
        distroarchseries.addOrUpdateChroot(fake_chroot)
        product = self.factory.makeProduct()
        prod_branch = self.factory.makeBranch(product=product)
        [prod_ref] = self.factory.makeGitRefs(target=product)
        bzr_prod_recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True, is_stale=True, branches=[prod_branch])
        git_prod_recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True, is_stale=True, branches=[prod_ref])
        bzr_prod_snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor],
            auto_build=True, is_stale=True, branch=prod_branch)
        git_prod_snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor],
            auto_build=True, is_stale=True, git_ref=prod_ref)
        package = self.factory.makeSourcePackage()
        pack_branch = self.factory.makeBranch(sourcepackage=package)
        [pack_ref] = self.factory.makeGitRefs(
            target=package.distribution_sourcepackage)
        bzr_pack_recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True, is_stale=True, branches=[pack_branch])
        git_pack_recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True, is_stale=True, branches=[pack_ref])
        bzr_pack_snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor],
            auto_build=True, is_stale=True, branch=pack_branch)
        git_pack_snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor],
            auto_build=True, is_stale=True, git_ref=pack_ref)
        items = [
            bzr_prod_recipe, git_prod_recipe, bzr_prod_snap, git_prod_snap,
            bzr_pack_recipe, git_pack_recipe, bzr_pack_snap, git_pack_snap,
            ]
        for item in items:
            self.assertEqual(0, item.pending_builds.count())
        transaction.commit()
        loggerhead_server = self.makeLoggerheadServer()
        loggerhead_server.addInventory(prod_branch, 'snap', 'prod_snap')
        loggerhead_server.addInventory(
            prod_branch, 'snap/snapcraft.yaml', 'prod_snapcraft_yaml')
        loggerhead_server.addBlob(
            prod_branch, 'prod_snapcraft_yaml', b'name: prod-snap')
        loggerhead_server.addInventory(pack_branch, 'snap', 'pack_snap')
        loggerhead_server.addInventory(
            pack_branch, 'snap/snapcraft.yaml', 'pack_snapcraft_yaml')
        loggerhead_server.addBlob(
            pack_branch, 'pack_snapcraft_yaml', b'name: pack-snap')
        turnip_server = self.makeTurnipServer()
        turnip_server.addBlob(
            prod_ref.repository, 'snap/snapcraft.yaml', b'name: prod-snap')
        turnip_server.addBlob(
            pack_ref.repository, 'snap/snapcraft.yaml', b'name: pack-snap')
        retcode, stdout, stderr = run_script(
            'cronscripts/request_daily_builds.py', [])
        self.assertIn('Requested 4 daily recipe builds.', stderr)
        self.assertIn('Requested 4 automatic snap package builds.', stderr)
        for item in items:
            self.assertEqual(1, item.pending_builds.count())
            self.assertFalse(item.is_stale)

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
