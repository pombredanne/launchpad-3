# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
from __future__ import with_statement

"""Helpers for running Launchpad in read-only mode.

To switch an app server to read-only mode, all you need to do is create a file
named read-only.txt in the root of the Launchpad tree.
"""

__metaclass__ = type
__all__ = [
    'IIsReadOnly',
    'IsReadOnlyUtility'
    'read_only_file_exists',
    'read_only_file_path',
    ]

import logging
import os
import threading

from zope.interface import implements, Interface
from zope.security.management import queryInteraction

from lazr.restful.utils import get_current_browser_request


root = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
read_only_file_path = os.path.join(root, 'read-only.txt')
READ_ONLY_MODE_ANNOTATIONS_KEY = 'launchpad.read_only_mode'


def read_only_file_exists():
    """Are we in read-only mode?

    Use with caution as this function will hit the filesystem to check for the
    presence of a file.
    """
    return os.path.isfile(read_only_file_path)


class IIsReadOnly(Interface):
    """A utility which tells us whether or not in read-only mode.

    Implemented as a utility because we need a global register of the mode
    we're on, so that we can log mode changes.
    """

    # pylint: disable-msg=E0211
    def isReadOnly():
        """Are we in read-only mode?

        If called as part of the processing of a request, we'll look in the
        request's annotations for a read-only key
        (READ_ONLY_MODE_ANNOTATIONS_KEY), and if it exists we'll just return
        its value.
        
        If there's no request or the key doesn't exist, we check for the
        presence of a read-only.txt file in the root of our tree, set the
        read-only key in the request's annotations (when there is a request),
        update self._currently_in_read_only (in case it changed, also logging
        the change) and return it.
        """


class IsReadOnlyUtility:

    implements(IIsReadOnly)
    _currently_in_read_only = False

    def __init__(self):
        self._lock = threading.Lock()
        self._currently_in_read_only = self.isReadOnly()

    def isReadOnly(self):
        """See `IIsReadOnly`."""
        request = None
        # Only call get_current_browser_request() when we have an interaction,
        # or else it will choke.
        if queryInteraction() is not None:
            request = get_current_browser_request()
        if request is not None:
            if READ_ONLY_MODE_ANNOTATIONS_KEY in request.annotations:
                return request.annotations[READ_ONLY_MODE_ANNOTATIONS_KEY]

        read_only = read_only_file_exists()
        if request is not None:
            request.annotations[READ_ONLY_MODE_ANNOTATIONS_KEY] = read_only

        log_change = False
        with self._lock:
            if self._currently_in_read_only != read_only:
                self._currently_in_read_only = read_only
                log_change = True

        if log_change:
            logging.warning(
                'Read-only mode change detected; now read-only is %s'
                % read_only)

        return read_only
