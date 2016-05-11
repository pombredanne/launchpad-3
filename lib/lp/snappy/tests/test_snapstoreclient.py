# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for communication with the snap store."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from cgi import FieldStorage
from collections import OrderedDict
import io
import json

from httmock import (
    all_requests,
    HTTMock,
    urlmatch,
    )
from lazr.restful.utils import get_current_browser_request
from requests import Request
from requests.utils import parse_dict_header
from testtools.matchers import (
    Contains,
    Equals,
    Matcher,
    MatchesDict,
    MatchesStructure,
    StartsWith,
    )
import transaction
from zope.component import getUtility

from lp.services.features.testing import FeatureFixture
from lp.services.timeline.requesttimeline import get_request_timeline
from lp.snappy.interfaces.snap import SNAP_TESTING_FLAGS
from lp.snappy.interfaces.snapstoreclient import (
    BadRequestPackageUploadResponse,
    ISnapStoreClient,
    )
from lp.snappy.model.snapstoreclient import MacaroonAuth
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadZopelessLayer


class TestMacaroonAuth(TestCase):

    def test_good(self):
        r = Request()
        MacaroonAuth(OrderedDict([("root", "abc"), ("discharge", "def")]))(r)
        self.assertEqual(
            'Macaroon root="abc", discharge="def"', r.headers["Authorization"])

    def test_bad_framing(self):
        r = Request()
        self.assertRaises(AssertionError, MacaroonAuth({"root": 'ev"il'}), r)


class RequestMatches(Matcher):
    """Matches a request with the specified attributes."""

    def __init__(self, url, auth=None, json_data=None, form_data=None,
                 **kwargs):
        self.url = url
        self.auth = auth
        self.json_data = json_data
        self.form_data = form_data
        self.kwargs = kwargs

    def match(self, request):
        mismatch = MatchesStructure(url=self.url, **self.kwargs).match(request)
        if mismatch is not None:
            return mismatch
        if self.auth is not None:
            mismatch = Contains("Authorization").match(request.headers)
            if mismatch is not None:
                return mismatch
            auth_value = request.headers["Authorization"]
            auth_scheme, auth_params = self.auth
            mismatch = StartsWith(auth_scheme + " ").match(auth_value)
            if mismatch is not None:
                return mismatch
            mismatch = Equals(auth_params).match(
                parse_dict_header(auth_value[len(auth_scheme + " "):]))
            if mismatch is not None:
                return mismatch
        if self.json_data is not None:
            mismatch = Equals(self.json_data).match(json.loads(request.body))
            if mismatch is not None:
                return mismatch
        if self.form_data is not None:
            if hasattr(request.body, "read"):
                body = request.body.read()
            else:
                body = request.body
            fs = FieldStorage(
                fp=io.BytesIO(body),
                environ={"REQUEST_METHOD": request.method},
                headers=request.headers)
            mismatch = MatchesDict(self.form_data).match(fs)
            if mismatch is not None:
                return mismatch


class TestSnapStoreClient(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestSnapStoreClient, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))
        self.pushConfig(
            "snappy", store_url="http://sca.example/",
            store_upload_url="http://updown.example/")
        self.client = getUtility(ISnapStoreClient)

    def test_requestPackageUploadPermission(self):
        @all_requests
        def handler(url, request):
            self.request = request
            return {"status_code": 200, "content": {"macaroon": "dummy"}}

        snappy_series = self.factory.makeSnappySeries(name="rolling")
        with HTTMock(handler):
            macaroon = self.client.requestPackageUploadPermission(
                snappy_series, "test-snap")
        self.assertThat(self.request, RequestMatches(
            url=Equals("http://sca.example/dev/api/acl/"),
            method=Equals("POST"),
            json_data={
                "packages": [{"name": "test-snap", "series": "rolling"}],
                "permissions": ["package_upload"],
                }))
        self.assertEqual("dummy", macaroon)
        request = get_current_browser_request()
        start, stop = get_request_timeline(request).actions[-2:]
        self.assertEqual("request-snap-upload-macaroon-start", start.category)
        self.assertEqual("rolling/test-snap", start.detail)
        self.assertEqual("request-snap-upload-macaroon-stop", stop.category)
        self.assertEqual("rolling/test-snap", stop.detail)

    def test_requestPackageUploadPermission_missing_macaroon(self):
        @all_requests
        def handler(url, request):
            return {"status_code": 200, "content": {}}

        snappy_series = self.factory.makeSnappySeries()
        with HTTMock(handler):
            self.assertRaisesWithContent(
                BadRequestPackageUploadResponse, b"{}",
                self.client.requestPackageUploadPermission,
                snappy_series, "test-snap")

    def test_requestPackageUploadPermission_404(self):
        @all_requests
        def handler(url, request):
            return {"status_code": 404, "reason": b"Not found"}

        snappy_series = self.factory.makeSnappySeries()
        with HTTMock(handler):
            self.assertRaisesWithContent(
                BadRequestPackageUploadResponse,
                b"404 Client Error: Not found",
                self.client.requestPackageUploadPermission,
                snappy_series, "test-snap")

    def test_upload(self):
        @urlmatch(path=r".*/unscanned-upload/$")
        def unscanned_upload_handler(url, request):
            self.unscanned_upload_request = request
            return {
                "status_code": 200,
                "content": {"successful": True, "upload_id": 1},
                }

        @urlmatch(path=r".*/snap-upload/.*")
        def snap_upload_handler(url, request):
            self.snap_upload_request = request
            return {"status_code": 202, "content": {"success": True}}

        store_secrets = {"root": "dummy-root", "discharge": "dummy-discharge"}
        snap = self.factory.makeSnap(
            store_upload=True,
            store_series=self.factory.makeSnappySeries(name="rolling"),
            store_name="test-snap", store_secrets=store_secrets)
        snapbuild = self.factory.makeSnapBuild(snap=snap)
        lfa = self.factory.makeLibraryFileAlias(content="dummy snap content")
        self.factory.makeSnapFile(snapbuild=snapbuild, libraryfile=lfa)
        transaction.commit()
        with HTTMock(unscanned_upload_handler, snap_upload_handler):
            self.client.upload(snapbuild)
        self.assertThat(self.unscanned_upload_request, RequestMatches(
            url=Equals("http://updown.example/unscanned-upload/"),
            method=Equals("POST"),
            form_data={
                "binary": MatchesStructure.byEquality(
                    name="binary", filename="filename",
                    value="dummy snap content",
                    type="application/octet-stream",
                    )}))
        self.assertThat(self.snap_upload_request, RequestMatches(
            url=Equals("http://sca.example/dev/api/snap-upload/test-snap/"),
            method=Equals("POST"), auth=("Macaroon", store_secrets),
            form_data={
                "updown_id": MatchesStructure.byEquality(
                    name="updown_id", value="1"),
                "series": MatchesStructure.byEquality(
                    name="series", value="rolling")}))
