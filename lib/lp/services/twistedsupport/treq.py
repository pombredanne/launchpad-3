# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for HTTP request handling with Twisted and treq."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'check_status',
    ]

import treq
from twisted.internet import defer
from twisted.web.error import Error


# This can be removed once something like
# https://github.com/twisted/treq/pull/159 is merged into treq.
def check_status(response):
    """Fail with an error if the response has an error status.

    An error status is a 4xx or 5xx code (RFC 7231).

    :rtype: A `Deferred` that fires with the response itself if the status
        is a known non-error code, or that fails it with
        :exc:`twisted.web.error.Error` otherwise.
    """
    if 100 <= response.code < 400:
        d = defer.succeed(response)
    else:
        def raise_error(body):
            raise Error(response.code, response=body)

        d = treq.content(response).addCallback(raise_error)

    return d
