# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A fake server that can lie about Content-Length."""

__metaclass__ = type

import os

from twisted.application import (
    service,
    strports,
    )
from twisted.web import (
    resource,
    server,
    )

from lp.services.daemons import readyservice


class FakeResource(resource.Resource):

    isLeaf = True

    def render_GET(self, request):
        return b"abcdef"


class FakeRequest(server.Request):
    """A Request that can send a Content-Length larger than the content."""

    def __init__(self, *args, **kwargs):
        server.Request.__init__(self, *args, **kwargs)
        if "LP_EXTRA_CONTENT_LENGTH" in os.environ:
            self.extra_content_length = int(
                os.environ["LP_EXTRA_CONTENT_LENGTH"])
        else:
            self.extra_content_length = None

    def setHeader(self, name, value):
        if (name.lower() == b"content-length" and
                self.extra_content_length is not None):
            value = str(int(value) + self.extra_content_length).encode("UTF-8")
        server.Request.setHeader(self, name, value)


application = service.Application("FakeServer")
services = service.IServiceCollection(application)

readyservice.ReadyService().setServiceParent(services)

site = server.Site(FakeResource())
site.requestFactory = FakeRequest
site.displayTracebacks = False
strports.service("tcp:0", site).setServiceParent(services)
