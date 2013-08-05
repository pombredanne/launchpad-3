# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Move files from Librarian disk storage into Swift."""

import _pythonpath

__metaclass__ = type
__all__ = ['lfc_to_swift']

import os.path
import sys

from swiftclient import client as swiftclient

from lp.services.config import config
from lp.services.librarianserver.storage import _relFileLocation


def to_swift(log, start_lfc_id=None, end_lfc_id=None, remove=False):
    '''Copy a range of Librarian files from disk into Swift.

    start and end identify the range of LibraryFileContent.id to 
    migrate (inclusive).

    If remove is True, files are removed from disk after being copied into
    Swift.
    '''
    swift_connection = swiftclient.Connection(
        authurl=os.environ.get('OS_AUTH_URL', None),
        user=os.environ.get('OS_USERNAME', None),
        key=os.environ.get('OS_PASSWORD', None),
        tenant_name=os.environ.get('OS_TENANT_NAME', None),
        auth_version='2.0',
        )
    fs_root = os.path.abspath(config.librarian_server.root)

    if start_lfc_id is None:
        start_lfc_id = 1
    if end_lfc_id is None:
        end_lfc_id = sys.maxint
        end_str = 'MAXINT'
    else:
        end_str = str(end_lfc_id)

    log.info("Walking disk store {} from {} to {}, inclusive".format(
        fs_root, start_lfc_id, end_str))

    start_fs_path = _fs_path(start_lfc_id)
    end_fs_path = _fs_path(end_lfc_id)

    # Walk the Librarian on disk file store, searching for matching
    # files that may need to be copied into Swift. We need to follow
    # symlinks as they are being used span disk partitions.
    for dirpath, dirnames, filenames in os.walk(fs_root, followlinks=True):

        # Don't recurse if we know this directory contains no matching
        # files.
        if (start_fs_path[:len(dirpath)] > dirpath
            or end_fs_path[:len(dirpath)] < dirpath):
            dirnames[:] = []
            continue

        log.debug('Scanning {} for matching files'.format(dirpath))

        for filename in sorted(filenames):
            fs_path = os.path.join(dirpath, filename)
            if fs_path < start_fs_path:
                continue
            if fs_path > end_fs_path:
                break
            rel_fs_path = fs_path[len(fs_root) + 1:]

            # Reverse engineer the LibraryFileContent.id from the
            # file's path. Warn about and skip bad filenames.
            hex_lfc = ''.join(rel_fs_path.split('/'))
            if len(hex_lfc) != 8:
                log.warning(
                    'Filename length fail, skipping {}'.format(fs_path))
                continue
            try:
                lfc = int(hex_lfc, 16)
            except ValueError:
                log.warning('Invalid hex fail, skipping {}'.format(fs_path))
                continue

            log.debug('Found {} ({})'.format(lfc, filename))

            container, obj_name = swift_location(lfc)

            swift_connection.put_container(container)
            swift_connection.put_object(
                container, obj_name,
                open(fs_path, 'rb'), os.path.getsize(fs_path))


def swift_location(lfc_id):
    '''Return the (container, obj_name) used to store a file.

    Per https://answers.launchpad.net/swift/+question/181977, we can't
    simply stuff everything into one container.
    '''
    assert isinstance(lfc_id, (int, long)), 'Not a LibraryFileContent.id'

    # Don't change this unless you are also going to rebuild the Swift
    # storage, as objects will no longer be found in the expected
    # container. This value and the container prefix are deliberatly
    # hard coded to avoid cockups with values specified in config files.
    max_objects_per_container = 1000000

    container_num = lfc_id // max_objects_per_container

    return ('librarian_{}'.format(container_num), str(lfc_id))


def _fs_path(lfc_id):
    return os.path.join(
        config.librarian_server.root, _relFileLocation(lfc_id))
