# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for running Launchpad in read-only mode.

To switch an app server to read-only mode, all you need to do is create a file
named read-only.txt in the root of the Launchpad tree.
"""

__metaclass__ = type
__all__ = [
    'is_read_only',
    'read_only_file_exists',
    'read_only_file_path',
    ]

import logging
import os
import threading

from lazr.restful.utils import get_current_browser_request
from zope.security.management import queryInteraction


root = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
read_only_file_path = os.path.join(root, 'read-only.txt')
READ_ONLY_MODE_ANNOTATIONS_KEY = 'launchpad.read_only_mode'


def read_only_file_exists():
    """Does a read-only.txt file exists in the root of our tree?"""
    return os.path.isfile(read_only_file_path)


_lock = threading.Lock()
_currently_in_read_only = False


def is_read_only():
    """Are we in read-only mode?

    If called as part of the processing of a request, we'll look in the
    request's annotations for a read-only key
    (READ_ONLY_MODE_ANNOTATIONS_KEY), and if it exists we'll just return its
    value.

    If there's no request or the key doesn't exist, we check for the presence
    of a read-only.txt file in the root of our tree, set the read-only key in
    the request's annotations (when there is a request), update
    _currently_in_read_only (in case it changed, also logging the change)
    and return it.
    """
    # pylint: disable-msg=W0603
    global _currently_in_read_only
    request = None
    # XXX: salgado, 2010-01-14, bug=507447: Only call
    # get_current_browser_request() when we have an interaction, or else
    # it will raise an AttributeError.
    if queryInteraction() is not None:
        request = get_current_browser_request()
    if request is not None:
        if READ_ONLY_MODE_ANNOTATIONS_KEY in request.annotations:
            return request.annotations[READ_ONLY_MODE_ANNOTATIONS_KEY]

    read_only = read_only_file_exists()
    if request is not None:
        request.annotations[READ_ONLY_MODE_ANNOTATIONS_KEY] = read_only

    log_change = False
    with _lock:
        if _currently_in_read_only != read_only:
            _currently_in_read_only = read_only
            log_change = True

    if log_change:
        logging.warning(
            'Read-only mode change detected; now read-only is %s' % read_only)

    return read_only


_currently_in_read_only = is_read_only()
