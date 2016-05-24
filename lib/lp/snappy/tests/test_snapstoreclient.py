# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for communication with the snap store."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from cgi import FieldStorage
import hashlib
import io
import json

from httmock import (
    all_requests,
    HTTMock,
    urlmatch,
    )
from lazr.restful.utils import get_current_browser_request
from pymacaroons import (
    Macaroon,
    Verifier,
    )
from requests import Request
from requests.utils import parse_dict_header
from testtools.matchers import (
    Contains,
    Equals,
    KeysEqual,
    Matcher,
    MatchesDict,
    MatchesStructure,
    Mismatch,
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


class MacaroonsVerify(Matcher):
    """Matches if serialised macaroons pass verification."""

    def __init__(self, key):
        self.key = key

    def match(self, macaroons):
        mismatch = KeysEqual("root", "discharge").match(macaroons)
        if mismatch is not None:
            return mismatch
        root_macaroon = Macaroon.deserialize(macaroons["root"])
        discharge_macaroon = Macaroon.deserialize(macaroons["discharge"])
        try:
            Verifier().verify(root_macaroon, self.key, [discharge_macaroon])
        except Exception as e:
            return Mismatch("Macaroons do not verify: %s" % e)


class TestMacaroonAuth(TestCase):

    def test_good(self):
        r = Request()
        root_key = hashlib.sha256("root").hexdigest()
        root_macaroon = Macaroon(key=root_key)
        discharge_key = hashlib.sha256("discharge").hexdigest()
        discharge_caveat_id = '{"secret": "thing"}'
        root_macaroon.add_third_party_caveat(
            "sso.example", discharge_key, discharge_caveat_id)
        unbound_discharge_macaroon = Macaroon(
            location="sso.example", key=discharge_key,
            identifier=discharge_caveat_id)
        MacaroonAuth(
            root_macaroon.serialize(),
            unbound_discharge_macaroon.serialize())(r)
        auth_value = r.headers["Authorization"]
        self.assertThat(auth_value, StartsWith("Macaroon "))
        self.assertThat(
            parse_dict_header(auth_value[len("Macaroon "):]),
            MacaroonsVerify(root_key))

    def test_bad_framing(self):
        r = Request()
        self.assertRaises(AssertionError, MacaroonAuth('ev"il', 'wic"ked'), r)


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
            auth_scheme, auth_params_matcher = self.auth
            mismatch = StartsWith(auth_scheme + " ").match(auth_value)
            if mismatch is not None:
                return mismatch
            mismatch = auth_params_matcher.match(
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

        @urlmatch(path=r".*/snap-upload/$")
        def snap_upload_handler(url, request):
            self.snap_upload_request = request
            return {"status_code": 202, "content": {"success": True}}

        root_key = hashlib.sha256(self.factory.getUniqueString()).hexdigest()
        root_macaroon = Macaroon(key=root_key)
        discharge_key = hashlib.sha256(
            self.factory.getUniqueString()).hexdigest()
        discharge_caveat_id = self.factory.getUniqueString()
        root_macaroon.add_third_party_caveat(
            "sso.example", discharge_key, discharge_caveat_id)
        unbound_discharge_macaroon = Macaroon(
            location="sso.example", key=discharge_key,
            identifier=discharge_caveat_id)
        store_secrets = {
            "root": root_macaroon.serialize(),
            "discharge": unbound_discharge_macaroon.serialize(),
            }
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
            url=Equals("http://sca.example/dev/api/snap-upload/"),
            method=Equals("POST"),
            auth=("Macaroon", MacaroonsVerify(root_key)),
            form_data={
                "name": MatchesStructure.byEquality(
                    name="name", value="test-snap"),
                "updown_id": MatchesStructure.byEquality(
                    name="updown_id", value="1"),
                "series": MatchesStructure.byEquality(
                    name="series", value="rolling")}))
