# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Miscelaneous functions for publisher."""

__metaclass__ = type

__all__ = [
    'PublishingTunableLoop',
    'process_in_batches',
    'RepositoryIndexFile',
    ]


import bz2
import gc
import gzip
from operator import itemgetter
import os
import stat
import tempfile

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import LoopTuner
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.mem import resident


def count_alive(store, logger):
    """Print counts of how many alive objects the store knows about."""
    counts = {}
    for obj_info in store._iter_alive():
        name = obj_info.cls_info.cls.__name__
        counts[name] = counts.get(name, 0) + 1

    sorted_items = sorted(counts.items(), key=itemgetter(0), reverse=True)
    for (name, count) in sorted_items:
        logger.debug('%-20s %d' % (name, count))


# Here begins the hack. Storm + StupidCache are not helping us iterating
# huge sets of records. The best result was produced by performing the
# task in small batches with StupidCache enabled and clearing caches with
# gc and clear_current_connection_cache. All other tested variations were
# slower and consumed more memory.
#
# 1 StupidCache + clear_current_connection_caches() [this];
# 2 storm.Cache + clear_current_connection_caches() [no difference];
# 3 StupidCache + store.invalidate(obj) [references left behind];
# 4 stormCache + store.invlaidate(obj)  [references left behind];
# 5 No batches [memory exhausted].

# XXX cprov 20080630: If we decide to keep this code/functionality, which
# I think we should, independently of the need to cleanup the cache after
# processing each batch, we should generalize and test it as suggested in
# bug #244328.

class PublishingTunableLoop(object):
    """An `ITunableLoop` for dealing with huge publishing result sets."""

    implements(ITunableLoop)

    def __init__(self, input, task, logger):
        self.input = input
        self.task = task
        self.logger = logger
        self.total_updated = 0
        self.offset = 0
        self.done = False

    def isDone(self):
        """See `ITunableLoop`."""
        return self.done

    def __call__(self, chunk_size):
        """Run the initialized 'task' with a limited batch of 'input'.

        See `ITunableLoop`.
        """
        chunk_size = int(chunk_size)
        start = self.offset
        end = start + chunk_size

        # The reason why we listify the sliced ResultSet is because we
        # cannot very it's size using 'count' (see bug #217644). However,
        # It's not exactly a problem considering non-empty set will be
        # iterated anyway.
        batch = list(self.input[start:end])
        if len(batch) == 0:
            self.done = True
            return

        for pub in batch:
            self.offset += 1
            self.task(pub)
            self.total_updated += 1

        mem_size = resident() / (2 ** 20)
        self.logger.debug(
            "Batch [%d..%d) [%d MiB]" % (start, self.offset, mem_size))

        # Invalidate the whole cache for the main store, this we we will also
        # get rid of all the foreign keys referred by the publishing records.
        main_store = getUtility(IStoreSelector).get(
                MAIN_STORE, DEFAULT_FLAVOR)
        main_store.invalidate()
        gc.collect()

        # Extra debug not necessary (unwanted, in fact) in production.
        # Print the number of 'alive' cache items.
        # count_alive(getUtility(IZStorm).get('main'), self.logger)


def process_in_batches(input, task, logger, goal_seconds=60,
                       minimum_chunk_size=10000):
    """Use `LoopTuner` to run the given task in smaller batches.

    Run callable 'task' for item of 'input', but do it in small batches
    cleaning up the cache after each one is processed.

    See `PublishingTunableLoop` for further details.

    :param input: `SelectResult` to be treated;
    :param task: callable to be executed for each batch;
    :param logger: `Logger` intance used to print information
        (debug level);
    :param goal_seconds: ideal time to spend processing each batch,
        defaults to 60 s;
    :param minimum_chunk_size: minimum number of items to be processed in
        each batch, defaults to 10000
    """
    loop = PublishingTunableLoop(input, task, logger)
    loop_tuner = LoopTuner(loop, goal_seconds=goal_seconds,
                           minimum_chunk_size=minimum_chunk_size)
    loop_tuner.run()


class RepositoryIndexFile:
    """Facilitates the publication of repository index files.

    It allows callsites to publish index files in different medias
    (plain, gzip and bzip) transparently and atomically.
    """

    def __init__(self, root, temp_root, filename):
        """Store repositories destinations and filename.

        The given 'temp_root' needs to exist, on the other hand, 'root'
        will be created on `close` if it doesn't exist.

        Additionally creates the needs temporary files in the given
        'temp_root'.
        """
        self.root = root
        self.temp_root = temp_root
        self.filename = filename

        self.temp_plain_path = None
        self.temp_gz_path = None
        self.temp_bz2_path = None

        assert os.path.exists(self.temp_root), (
            'Temporary root does not exist.')

        fd_bz2, self.temp_bz2_path = tempfile.mkstemp(
            dir=self.temp_root, prefix='%s-bz2_' % filename)
        os.close(fd_bz2)
        self.bz2_fd = bz2.BZ2File(self.temp_bz2_path, mode='wb')

        fd_gz, self.temp_gz_path = tempfile.mkstemp(
            dir=self.temp_root, prefix='%s-gz_' % filename)
        self.gz_fd = gzip.GzipFile(fileobj=os.fdopen(fd_gz, "wb"))

        fd, self.temp_plain_path = tempfile.mkstemp(
            dir=self.temp_root, prefix='%s_' % filename)
        self.plain_fd = os.fdopen(fd, "wb")

    def __del__(self):
        """Remove temporary files if they were left behind. """
        file_paths = (
            self.temp_plain_path, self.temp_gz_path, self.temp_bz2_path)
        for file_path in file_paths:
            if file_path is not None and os.path.exists(file_path):
                os.remove(file_path)

    def write(self, content):
        """Write contents to all target medias."""
        self.plain_fd.write(content)
        self.gz_fd.write(content)
        self.bz2_fd.write(content)

    def close(self):
        """Close both temporary medias and atomically publish them.

        It also fixes the final files permissions making them readable and
        writable by their group and readable by others.

        If necessary the given 'root' destination is created at this point.
        """
        self.plain_fd.close()
        self.gz_fd.close()
        self.bz2_fd.close()

        if os.path.exists(self.root):
            assert os.access(
                self.root, os.W_OK), "%s not writeable!" % self.root
        else:
            os.makedirs(self.root)

        # XXX julian 2007-10-03
        # This is kinda papering over a problem somewhere that causes the
        # files to get created with permissions that don't allow group/world
        # read access.  See https://bugs.launchpad.net/soyuz/+bug/148471
        def makeFileGroupWriteableAndWorldReadable(file_path):
            mode = stat.S_IMODE(os.stat(file_path).st_mode)
            os.chmod(
                file_path, mode | stat.S_IWGRP | stat.S_IRGRP | stat.S_IROTH)

        root_plain_path = os.path.join(self.root, self.filename)
        os.rename(self.temp_plain_path, root_plain_path)
        makeFileGroupWriteableAndWorldReadable(root_plain_path)

        root_gz_path = os.path.join(self.root, "%s.gz" % self.filename)
        os.rename(self.temp_gz_path, root_gz_path)
        makeFileGroupWriteableAndWorldReadable(root_gz_path)

        root_bz2_path = os.path.join(self.root, "%s.bz2" % self.filename)
        os.rename(self.temp_bz2_path, root_bz2_path)
        makeFileGroupWriteableAndWorldReadable(root_bz2_path)
