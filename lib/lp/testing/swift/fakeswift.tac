# -*- python -*-
# Copyright 2013-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

'''Launch a mock Swift service.'''

__metaclass__ = type
__all__ = []

import os.path
import logging

import twisted.web.server
from twisted.application import internet, service

logging.basicConfig()

from lp.testing.swift.fakeswift import Root

storedir = os.environ['SWIFT_ROOT']
assert os.path.exists(storedir)

application = service.Application('fakeswift')
root = Root(hostname='localhost')
site = twisted.web.server.Site(root)

port = int(os.environ['SWIFT_PORT'])

sc = service.IServiceCollection(application)
internet.TCPServer(port, site).setServiceParent(sc)
