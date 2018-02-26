# Copyright 2013-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Move files from Librarian disk storage into Swift."""

__metaclass__ = type
__all__ = [
    'SWIFT_CONTAINER_PREFIX',
    'connection',
    'connection_pool',
    'filesystem_path',
    'quiet_swiftclient',
    'swift_location',
    'to_swift',
    ]

from contextlib import contextmanager
import hashlib
import os.path
import re
import time
import urllib

from swiftclient import client as swiftclient

from lp.services.config import config
from lp.services.database.interfaces import ISlaveStore
from lp.services.librarian.model import LibraryFileContent


SWIFT_CONTAINER_PREFIX = 'librarian_'
MAX_SWIFT_OBJECT_SIZE = 5 * 1024 ** 3  # 5GB Swift limit.

ONE_DAY = 24 * 60 * 60


def quiet_swiftclient(func, *args, **kwargs):
    # XXX cjwatson 2018-01-02: swiftclient has some very rude logging
    # practices: the low-level API calls `logger.exception` when a request
    # fails, without considering whether the caller might handle it and
    # recover.  This was introduced in 1.6.0 and removed in 3.2.0; until
    # we're on a new enough version not to need to worry about this, we shut
    # up the noisy logging around calls whose failure we can handle.
    # Messier still, logging.getLogger('swiftclient') doesn't necessarily
    # refer to the Logger instance actually being used by swiftclient, so we
    # have to use swiftclient.logger directly.
    old_disabled = swiftclient.logger.disabled
    try:
        swiftclient.logger.disabled = True
        return func(*args, **kwargs)
    finally:
        swiftclient.logger.disabled = old_disabled


def to_swift(log, start_lfc_id=None, end_lfc_id=None, remove_func=False):
    '''Copy a range of Librarian files from disk into Swift.

    start and end identify the range of LibraryFileContent.id to
    migrate (inclusive).

    If remove_func is set, it is called for every file after being copied into
    Swift.
    '''
    swift_connection = connection_pool.get()
    fs_root = os.path.abspath(config.librarian_server.root)

    if start_lfc_id is None:
        start_lfc_id = 1
    if end_lfc_id is None:
        # Maximum id capable of being stored on the filesystem - ffffffff
        end_lfc_id = 0xffffffff

    log.info("Walking disk store {0} from {1} to {2}, inclusive".format(
        fs_root, start_lfc_id, end_lfc_id))

    start_fs_path = filesystem_path(start_lfc_id)
    end_fs_path = filesystem_path(end_lfc_id)

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
        else:
            # We need to descend in order, making it possible to resume
            # an aborted job.
            dirnames.sort()

        log.debug('Scanning {0} for matching files'.format(dirpath))

        _filename_re = re.compile('^[0-9a-f]{2}$')

        for filename in sorted(filenames):
            fs_path = os.path.join(dirpath, filename)

            # Skip any files with names that are not two hex digits.
            # This is noise in the filesystem database.
            if _filename_re.match(filename) is None:
                log.debug('Skipping noise %s' % fs_path)
                continue

            if fs_path < start_fs_path:
                continue
            if fs_path > end_fs_path:
                break

            # Skip files which have been modified recently, as they
            # may be uploads still in progress.
            if os.path.getmtime(fs_path) > time.time() - ONE_DAY:
                log.debug('Skipping recent upload %s' % fs_path)
                continue

            # Reverse engineer the LibraryFileContent.id from the
            # file's path. Warn about and skip bad filenames.
            rel_fs_path = fs_path[len(fs_root) + 1:]
            hex_lfc = ''.join(rel_fs_path.split('/'))
            if len(hex_lfc) != 8:
                log.warning(
                    'Filename length fail, skipping {0}'.format(fs_path))
                continue
            try:
                lfc = int(hex_lfc, 16)
            except ValueError:
                log.warning('Invalid hex fail, skipping {0}'.format(fs_path))
                continue

            log.debug('Found {0} ({1})'.format(lfc, filename))

            if ISlaveStore(LibraryFileContent).get(
                    LibraryFileContent, lfc) is None:
                log.info("{0} exists on disk but not in the db".format(
                    lfc))
                continue

            container, obj_name = swift_location(lfc)

            try:
                quiet_swiftclient(swift_connection.head_container, container)
                log.debug2('{0} container already exists'.format(container))
            except swiftclient.ClientException as x:
                if x.http_status != 404:
                    raise
                log.info('Creating {0} container'.format(container))
                swift_connection.put_container(container)

            try:
                headers = quiet_swiftclient(
                    swift_connection.head_object, container, obj_name)
                log.debug(
                    "{0} already exists in Swift({1}, {2})".format(
                        lfc, container, obj_name))
                if ('X-Object-Manifest' not in headers and
                        int(headers['content-length'])
                        != os.path.getsize(fs_path)):
                    raise AssertionError(
                        '{0} has incorrect size in Swift'.format(lfc))
            except swiftclient.ClientException as x:
                if x.http_status != 404:
                    raise
                log.info('Putting {0} into Swift ({1}, {2})'.format(
                    lfc, container, obj_name))
                _put(log, swift_connection, lfc, container, obj_name, fs_path)

            if remove_func:
                remove_func(fs_path)


def rename(path):
    # It would be nice to move the file out of the tree entirely, but we
    # need to keep the backup on the same filesystem as the original
    # file.
    os.rename(path, path + '.migrated')


def _put(log, swift_connection, lfc_id, container, obj_name, fs_path):
    fs_size = os.path.getsize(fs_path)
    fs_file = HashStream(open(fs_path, 'rb'))

    db_md5_hash = ISlaveStore(LibraryFileContent).get(
        LibraryFileContent, lfc_id).md5

    assert hasattr(fs_file, 'tell') and hasattr(fs_file, 'seek'), '''
        File not rewindable
        '''

    if fs_size <= MAX_SWIFT_OBJECT_SIZE:
        swift_md5_hash = swift_connection.put_object(
            container, obj_name, fs_file, fs_size)
        disk_md5_hash = fs_file.hash.hexdigest()
        if not (disk_md5_hash == db_md5_hash == swift_md5_hash):
            log.error(
                "LibraryFileContent({0}) corrupt. "
                "disk md5={1}, db md5={2}, swift md5={3}".format(
                    lfc_id, disk_md5_hash, db_md5_hash, swift_md5_hash))
            try:
                swift_connection.delete_object(container, obj_name)
            except Exception:
                log.exception('Failed to delete corrupt file from Swift')
            raise AssertionError('md5 mismatch')
    else:
        # Large file upload. Create the segments first, then the
        # manifest. This order prevents partial downloads, and lets us
        # detect interrupted uploads and clean up.
        segment = 0
        while fs_file.tell() < fs_size:
            assert segment <= 9999, 'Insane number of segments'
            seg_name = '%s/%04d' % (obj_name, segment)
            seg_size = min(fs_size - fs_file.tell(), MAX_SWIFT_OBJECT_SIZE)
            md5_stream = HashStream(fs_file, length=seg_size)
            swift_md5_hash = swift_connection.put_object(
                container, seg_name, md5_stream, seg_size)
            segment_md5_hash = md5_stream.hash.hexdigest()
            assert swift_md5_hash == segment_md5_hash, (
                "LibraryFileContent({0}) segment {1} upload corrupted".format(
                    lfc_id, segment))
            segment = segment + 1

        disk_md5_hash = fs_file.hash.hexdigest()
        if disk_md5_hash != db_md5_hash:
            # We don't have to delete the uploaded segments, as Librarian
            # Garbage Collection handles this for us.
            log.error(
                "Large LibraryFileContent({0}) corrupt. "
                "disk md5={1}, db_md5={2}".format(
                    lfc_id, disk_md5_hash, db_md5_hash))
            raise AssertionError('md5 mismatch')

        manifest = '{0}/{1}/'.format(
            urllib.quote(container), urllib.quote(obj_name))
        manifest_headers = {'X-Object-Manifest': manifest}
        swift_connection.put_object(
            container, obj_name, '', 0, headers=manifest_headers)


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
    # While the suggested number is 'under a million', the rare large files
    # will take up multiple slots so we choose a more conservative number.
    max_objects_per_container = 500000

    container_num = lfc_id // max_objects_per_container

    return (SWIFT_CONTAINER_PREFIX + str(container_num), str(lfc_id))


def filesystem_path(lfc_id):
    from lp.services.librarianserver.storage import _relFileLocation
    return os.path.join(
        config.librarian_server.root, _relFileLocation(lfc_id))


class SwiftStream:
    def __init__(self, swift_connection, chunks):
        self._swift_connection = swift_connection
        self._chunks = chunks  # Generator from swiftclient.get_object()

        self.closed = False
        self._offset = 0
        self._chunk = None

    def read(self, size):
        if self.closed:
            raise ValueError('I/O operation on closed file')

        if self._swift_connection is None:
            return ''

        if size == 0:
            return ''

        return_chunks = []
        return_size = 0

        while return_size < size:
            if not self._chunk:
                self._chunk = self._next_chunk()
                if not self._chunk:
                    # If we have drained the data successfully,
                    # the connection can be reused saving on auth
                    # handshakes.
                    connection_pool.put(self._swift_connection)
                    self._swift_connection = None
                    self._chunks = None
                    break
            split = size - return_size
            return_chunks.append(self._chunk[:split])
            self._chunk = self._chunk[split:]
            return_size += len(return_chunks[-1])

        self._offset += return_size
        return ''.join(return_chunks)

    def _next_chunk(self):
        try:
            return self._chunks.next()
        except StopIteration:
            return None

    def close(self):
        self.closed = True
        self._swift_connection = None

    def seek(self, offset):
        if offset < self._offset:
            raise NotImplementedError('rewind')  # Rewind not supported
        else:
            self.read(offset - self._offset)

    def tell(self):
        return self._offset


class HashStream:
    """Read a file while calculating a checksum as we go."""
    def __init__(self, stream, length=None, hash_factory=hashlib.md5):
        self._stream = stream
        self._length = self._remaining = length
        self.hash_factory = hash_factory
        self.hash = hash_factory()

    def read(self, size=-1):
        if self._remaining is not None:
            if self._remaining <= 0:
                return ''
            size = min(size, self._remaining)
        chunk = self._stream.read(size)
        if self._remaining is not None:
            self._remaining -= len(chunk)
        self.hash.update(chunk)
        return chunk

    def tell(self):
        return self._stream.tell()

    def seek(self, offset):
        """Seek to offset, and reset the hash."""
        self.hash = self.hash_factory()
        if self._remaining is not None:
            self._remaining = self._length - offset
        return self._stream.seek(offset)


class ConnectionPool:
    MAX_POOL_SIZE = 10

    def __init__(self):
        self.clear()

    def clear(self):
        self._pool = []

    def get(self):
        '''Return a conection from the pool, or a fresh connection.'''
        try:
            return self._pool.pop()
        except IndexError:
            return self._new_connection()

    def put(self, swift_connection):
        '''Put a connection back in the pool for reuse.

        Only call this if the connection is in a usable state. If an
        exception has been raised (apart from a 404), don't trust the
        swift_connection and throw it away.
        '''
        if not isinstance(swift_connection, swiftclient.Connection):
            raise AssertionError(
                "%r is not a swiftclient Connection." % swift_connection)
        if swift_connection not in self._pool:
            self._pool.append(swift_connection)
            while len(self._pool) > self.MAX_POOL_SIZE:
                self._pool.pop(0)

    def _new_connection(self):
        return swiftclient.Connection(
            authurl=config.librarian_server.os_auth_url,
            user=config.librarian_server.os_username,
            key=config.librarian_server.os_password,
            tenant_name=config.librarian_server.os_tenant_name,
            auth_version='2.0',
            )


connection_pool = ConnectionPool()


@contextmanager
def connection():
    global connection_pool
    con = connection_pool.get()
    yield con

    # We can safely put the connection back in the pool, as this code is
    # only reached if the contextmanager block exited normally (no
    # exception raised).
    connection_pool.put(con)
