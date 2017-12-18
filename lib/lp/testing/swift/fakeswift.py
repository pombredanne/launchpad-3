# Copyright 2013-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An OpenStack Swift server mock using Twisted.

Not all functionality is provided; just enough to test the client.
"""

__metaclass__ = type

import base64
from datetime import (
    datetime,
    timedelta,
    )
import hashlib
import io
import json
import logging
import os.path
import sys
import time
import uuid

from twisted.web import (
    http,
    resource,
    server,
    static,
    )


logger = logging.getLogger('lp.testing.swift.fakeswift')


KEYSTONE_PATH = "/keystone/v2.0"
DEFAULT_REGION = "region-1"
DEFAULT_TENANT_NAME = "test"
DEFAULT_USERNAME = "test"
DEFAULT_PASSWORD = "test"


class FakeKeystone(resource.Resource):
    """A fake Keystone API endpoint."""

    def __init__(self, root, allow_default_access=True):
        resource.Resource.__init__(self)
        self.root = root
        self.users = {}
        self.tokens = {}
        if allow_default_access:
            self.users[DEFAULT_USERNAME] = {
                "id": uuid.uuid4().hex,
                "name": DEFAULT_USERNAME,
                "roles": [{
                    "name": "swiftaccess"
                    }],
                "roles_links": [],
                "username": DEFAULT_USERNAME,
                }

    def getUser(self, username):
        """Get information about a specific user."""
        return self.users[username]

    def _isValidToken(self, token, tenant_name):
        """Validate a given token for expiration."""
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        if token["expires"] > now and token["tenant"]["name"] == tenant_name:
            return True
        return False

    def getValidToken(self, tenant_name, expected_token=None):
        """Get a valid token for the given tenant name."""
        if expected_token is not None:
            token = self.tokens[expected_token]
            if self._isValidToken(token, tenant_name):
                return token
        else:
            for id, token in self.tokens.iteritems():
                if self._isValidToken(token, tenant_name):
                    return token

    def ensureValidToken(self, tenant_name):
        """Ensure a valid token is created if one doesn't exist."""
        valid_token = self.getValidToken(tenant_name)
        if valid_token is None:
            token_id = uuid.uuid4().hex
            default_expires = datetime.utcnow() + timedelta(hours=24)
            self.tokens[token_id] = {
                "expires": default_expires.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "id": token_id,
                "tenant": self.root.tenants[tenant_name],
                }

    def validateToken(self, request, tenant_name):
        """Validate token from request against valid tokens."""
        token = request.getHeader('x-auth-token')
        valid_token = self.getValidToken(tenant_name, token)
        return valid_token is not None

    def getChild(self, path, request):
        """See `twisted.web.resource.Resource.getChild`."""
        if path in ("v2.0", "tokens"):
            return self
        return resource.NoResource("Not a valid keystone URL.")

    def render_POST(self, request):
        """Validate provided credentials and return service catalog."""
        if "application/json" not in request.getHeader('content-type'):
            request.setResponseCode(http.BAD_REQUEST)
            return ""
        credentials = json.load(request.content)
        if not "auth" in credentials:
            request.setResponseCode(http.FORBIDDEN)
            return ""
        if ((not "tenantName" in credentials["auth"] or
             not "passwordCredentials" in credentials["auth"])):
            request.setResponseCode(http.FORBIDDEN)
            return ""
        tenant_name = credentials["auth"]["tenantName"]
        pw_creds = credentials["auth"]["passwordCredentials"]
        username, password = pw_creds.get("username"), pw_creds.get("password")
        if not tenant_name in self.root.tenants:
            request.setResponseCode(http.FORBIDDEN)
            return ""
        if not username in self.users:
            request.setResponseCode(http.FORBIDDEN)
            return ""
        if password != DEFAULT_PASSWORD:
            request.setResponseCode(http.FORBIDDEN)
            return ""

        self.ensureValidToken(tenant_name)

        request.setResponseCode(200)
        return json.dumps({
            "access": {
                "serviceCatalog": self.root.getCatalog(
                    tenant_name, request),
                "token": self.getValidToken(tenant_name),
                "user": self.getUser(username),
                }
            })


def parse_range_header(range):
    """Modelled after `twisted.web.static.File._parseRangeHeader`."""
    if '=' in range:
        type, value = range.split('=', 1)
    else:
        raise ValueError("Invalid range header, no '='")
    if type != 'bytes':
        raise ValueError("Invalid range header, must be a 'bytes' range")
    raw_ranges = [bytes.strip() for bytes in value.split(',')]
    ranges = []
    for current_range in raw_ranges:
        if '-' not in current_range:
            raise ValueError("Illegal byte range: %r" % current_range)
        begin, end = current_range.split('-')
        if begin:
            begin = int(begin)
        else:
            begin = None
        if end:
            end = int(end)
        else:
            end = None
        ranges.append((begin, end))
    return ranges


class EmptyPage(resource.Resource):
    """Return an empty document."""
    isLeaf = True

    def __init__(self, retcode=http.OK, headers=None, body=""):
        resource.Resource.__init__(self)
        self._retcode = retcode
        self._headers = headers
        self._body = body

    def render(self, request):
        request.setHeader("Content-Type", "text/html")
        request.setHeader("Connection", "close")
        if self._headers:
            for h, v in self._headers.items():
                request.setHeader(h, v)
        request.setResponseCode(self._retcode)
        return self._body


class SwiftObject(resource.Resource):
    """A Swift storage object."""

    isLeaf = True

    content_type = None
    contents = None
    _etag = None

    def __init__(self, container, name, contents=None,
                 content_type="application/octet-stream", content_md5=None):
        resource.Resource.__init__(self)
        self.container = container
        self.name = name
        if contents is not None:
            self.set_contents(
                contents=contents, content_type=content_type,
                content_md5=content_md5)
        self._date = time.asctime()

    def __getstate__(self):
        d = self.__dict__.copy()
        del d["children"]
        return d

    def set_contents(self, contents=None, content_type=None,
                     content_md5=None):
        self.content_type = content_type
        self.contents = contents
        if content_md5:
            if isinstance(content_md5, str):
                self._etag = content_md5
            else:
                self._etag = content_md5.hexdigest()
        else:
            self._etag = hashlib.md5(contents).hexdigest()

    def get_etag(self):
        """Build an ETag value. Extra quotes are mandated by standards."""
        return '"%s"' % self._etag

    def set_date(self, datestr):
        """Set the object's time."""
        self._date = datestr

    def get_date(self):
        """Get the object's time."""
        return self._date

    def get_size(self):
        """Returns size of object's contents."""
        return len(self.contents)

    def render_GET(self, request):
        """Render the response for a GET or HEAD request on this object."""
        request.setHeader("Content-Type", self.content_type)
        request.setHeader("ETag", self._etag)
        range = request.getHeader("Range")
        size = len(self.contents)
        if request.method == 'HEAD':
            request.setHeader("Content-Length", size)
            return ""
        if range:
            ranges = parse_range_header(range)
            length = 0
            if len(ranges)==1:
                begin, end = ranges[0]
                if begin is None:
                    request.setResponseCode(
                        http.REQUESTED_RANGE_NOT_SATISFIABLE)
                    return ''
                if not end:
                    end = size
                elif end < size:
                    end += 1
                if begin >= size:
                    request.setResponseCode(
                        http.REQUESTED_RANGE_NOT_SATISFIABLE)
                    request.setHeader(
                        'content-range', 'bytes */%d' % size)
                    return ''
                else:
                    request.setHeader(
                        'content-range',
                        'bytes %d-%d/%d' % (begin, end-1, size))
                length = (end - begin)
                request.setHeader("Content-Length", length)
                request.setResponseCode(http.PARTIAL_CONTENT)
                contents = io.BytesIO(self.contents[begin:end])
            else:
                # multiple ranges should be returned in a multipart response
                request.setResponseCode(http.REQUESTED_RANGE_NOT_SATISFIABLE)
                return ''

        else:
            request.setHeader("Content-Length", str(size))
            if isinstance(self.contents, io.IOBase):
                contents = self.contents
            else:
                contents = io.BytesIO(self.contents)

        producer = static.NoRangeStaticProducer(request, contents)
        producer.start()
        return server.NOT_DONE_YET

    def render_PUT(self, request):
        """Accept the incoming data for a PUT request."""
        data = request.content.read()
        content_type = request.getHeader("Content-Type")
        content_md5 = request.getHeader("Content-MD5")
        if content_md5: # check if the data is good
            header_md5 = base64.decodestring(content_md5)
            data_md5  = hashlib.md5(data)
            assert (data_md5.digest() == header_md5), "md5 check failed!"
            content_md5 = data_md5
        self.set_contents(
            contents=data, content_type=content_type, content_md5=content_md5)
        date = request.getHeader("Date")
        if not date:
            date = time.ctime()
        self.set_date(date)
        self.container.container_children[self.name] = self
        request.setHeader("ETag", self.get_etag())
        logger.debug("created object container=%s name=%s size=%d" % (
            self.container, self.name, len(data)))
        return ""


class SwiftContainer(resource.Resource):
    """Storage container.

    Containers hold objects with data and receive uploads in case of PUT.
    """
    def __init__(self, name, tenant_name):
        resource.Resource.__init__(self)
        # Can't use children: resource already has that name and it would
        # work as a cache.
        self.container_children = {}
        self._name = name
        self.tenant_name = tenant_name
        self._date = time.time()

    def __len__(self):
        """Returns how many objects are in this container."""
        return len(self.container_children)

    def iter_children(self):
        """Iterator that returns each child object."""
        for key, val in self.container_children.items():
            yield key, val

    def getChild(self, name, request):
        """Get the next object down the chain."""
        # avoid recursion into the key names
        # (which can contain / as a valid char!)
        if name and request.postpath:
            name = os.path.join(*((name,)+tuple(request.postpath)))
        assert (name), "Wrong call stack for name='%s'" % (name,)
        if request.method == "PUT":
            child = SwiftObject(self, name)
        elif request.method in ("GET", "HEAD") :
            child = self.container_children.get(name, None)
        elif request.method == "DELETE":
            child = self.container_children.get(name, None)
            if child is None: # delete unknown object
                return EmptyPage(http.NO_CONTENT)
            del self.container_children[name]
            return EmptyPage(http.NO_CONTENT)
        else:
            logger.error("UNHANDLED request method %s" % request.method)
            return EmptyPage(http.METHOD_NOT_ALLOWED)
        if child is None:
            return EmptyPage(http.NOT_FOUND)
        return child

    def render_GET(self, request):
        """Return list of keys in response to GET on container."""
        if request.args.get('format', [])[0] != "json":
            raise NotImplementedError()

        results = []
        marker = request.args.get('marker', [None])[0]
        end_marker = request.args.get('end_marker', [None])[0]
        prefix = request.args.get('prefix', [None])[0]
        format_ = request.args.get('format', [None])[0]
        delimiter = request.args.get('delimiter', None)
        path = request.args.get('path', None)

        if format_ != 'json' or delimiter or path:
            raise NotImplementedError()

        # According to the docs, limit will be 10000 if no query
        # parameters are passed. However, as we require at least the
        # 'format' query parameter above, the default is always
        # unlimited.
        limit = int(request.args.get('limit', [sys.maxint])[0])

        results = []
        for name, child in sorted(self.iter_children()):
            if prefix and not name.startswith(prefix):
                continue
            if marker and name <= marker:
                continue
            if end_marker and name >= end_marker:
                break
            if limit and len(results) >= limit:
                break

            # Convert the ascii local time to UTC ISO format.
            local_mod_time = time.mktime(time.strptime(child.get_date()))
            mod_time = datetime.utcfromtimestamp(local_mod_time).strftime(
                '%Y-%m-%dT%H:%M:%S.%f')

            results.append({
                'name': name,
                'bytes': child.get_size(),
                'hash': child._etag,
                'content-type': child.content_type,
                'last_modified': mod_time,
                })

        return json.dumps(results)


class FakeContent(io.IOBase):
    """A content that can be sliced or read but will never exist in memory."""

    def __init__(self, char, size):
        """Create the content as char*size."""
        self.char = char
        self.size = size
        self.position = 0

    def __getitem__(self, slice):
        """Get a piece of the content."""
        size = min(slice.stop, self.size) - slice.start
        return self.char*size

    def hexdigest(self):
        """Send a fake hexdigest.

        For big contents this takes too much time to calculate, so we just
        fake it.
        """
        block_size = 2 ** 16
        start = 0
        data = self[start:start+block_size]
        md5calc = hashlib.md5()
        md5calc.update(data)
        return md5calc.hexdigest()

    def __len__(self):
        """The size."""
        return self.size

    def read(self, size):
        """Read a block of data."""
        block = self[self.position:self.position + size]
        self.position = min(self.position + size, self.size)
        return block


class SizeContainer(SwiftContainer):
    """Return fake objects with size = int(objname)."""

    def getChild(self, name, request):
        """Get the next object down the chain."""
        try:
            fake = FakeContent("0", int(name))
            o = SwiftObject(self, name, fake, "text/plain", fake.hexdigest())
            return o
        except ValueError:
            return "this container requires integer named objects"


class FakeSwift(resource.Resource):
    """A fake Swift endpoint."""

    def __init__(self, root):
        resource.Resource.__init__(self)
        self.root = root
        self.containers = {
            "size": SizeContainer("size", DEFAULT_TENANT_NAME),
            }

    def addContainer(self, name):
        """Create a new container."""
        if name in self.containers:
            return self.containers[name]
        container = SwiftContainer(name, DEFAULT_TENANT_NAME)
        self.containers[name] = container
        return container

    def _getResource(self, name, request):
        """Get a fake resource for the given request."""
        container = self.containers.get(name, None)

        # if we operate on a key, pass control
        if (((request.postpath and request.postpath[0]) or
             (not request.postpath and request.method == "GET"))):
            if container is None:
                # container does not exist, yet we attempt operation on
                # an object from that container
                return EmptyPage(http.NOT_FOUND)
            return container

        if request.method == "HEAD":
            if container is None:
                return EmptyPage(http.NOT_FOUND)
            return EmptyPage(http.NO_CONTENT)

        if request.method == "PUT":
            if container is None:
                container = self.addContainer(name)
            return EmptyPage()

        if request.method == "DELETE":
            if container is None:  # delete unknown object
                return EmptyPage(http.NO_CONTENT)
            del self.containers[name]
            return EmptyPage(http.NO_CONTENT)

        return resource.Resource.getChild(self, name, request)

    def getChild(self, name, request):
        """See `twisted.web.resource.Resource.getChild`."""
        if name == "v1" or name.startswith("AUTH_"):
            return self

        resource = self._getResource(name, request)
        tenant_name = getattr(resource, "tenant_name", None)
        if tenant_name is None:
            return resource

        if not self.root.keystone.validateToken(request, tenant_name):
            return EmptyPage(http.FORBIDDEN)

        return resource


class Root(resource.Resource):
    """Site root.

    Handles all the requests.
    On initialization it configures a default "size" container.
    """

    def __init__(self, allow_default_access=True, hostname="localhost"):
        resource.Resource.__init__(self)
        self.hostname = hostname
        self.tenants = {}
        self.tenants[DEFAULT_TENANT_NAME] = {
            "id": uuid.uuid4().hex,
            "enabled": True,
            "description": "Tenant %s" % DEFAULT_TENANT_NAME,
            "name": DEFAULT_TENANT_NAME}

        self.keystone = FakeKeystone(
            self, allow_default_access=allow_default_access)
        self.swift = FakeSwift(self)
        self.putChild("keystone", self.keystone)
        self.putChild("swift", self.swift)

    def getCatalog(self, tenant, request):
        """Compute service catalog for the given request and tenant."""
        port = request.transport.socket.getsockname()[1]
        tenant_id = self.tenants[tenant]["id"]
        base_url = "http://%s:%d/swift/v1" % (self.hostname, port)
        catalog = [
            {"endpoints": [
                {"adminURL": base_url,
                 "id": uuid.uuid4().hex,
                 "internalURL": base_url + "/AUTH_" + tenant_id,
                 "publicURL": base_url + "/AUTH_" + tenant_id,
                 "region": DEFAULT_REGION}
                ],
             "endpoints_links": [],
             "name": "swift",
             "type": "object-store"
             }]
        return catalog
