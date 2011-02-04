# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Miscelaneous functions for publisher."""

__metaclass__ = type

__all__ = [
    'PublishingTunableLoop',
    'RepositoryIndexFile',
    'get_ppa_reference',
    'process_in_batches',
    ]


import bz2
import gc
import gzip
from operator import itemgetter
import os
import stat
import tempfile

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import LoopTuner
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.mem import resident
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.archive import (
    default_name_by_purpose,
    )


def get_ppa_reference(ppa):
    """Return a text reference for the given PPA.

    * '<owner_name>' for default PPAs (the ones named 'ppa');
    * '<owner_name>-<ppa_name>' for named-PPAs.
    """
    assert ppa.purpose == ArchivePurpose.PPA, (
        'Only PPAs can use reference name.')

    if ppa.name != default_name_by_purpose.get(ArchivePurpose.PPA):
        return '%s-%s' % (ppa.owner.name, ppa.name)

    return ppa.owner.name


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
# 4 stormCache + store.invalidate(obj)  [references left behind];
# 5 No batches [memory exhausted].

# XXX JeroenVermeulen 2011-02-03 bug=244328: That was mid-2008.  We have
# the GenerationalCache now.  We may not need any of this any more.

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
        # cannot very it's size using 'count' (see bug #217644 and note
        # that it was fixed in storm but not SQLObjectResultSet). However,
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


class PlainTempFile:

    # Filename suffix.
    suffix = ''
    # File path built on initialization.
    path = None

    def __init__(self, temp_root, filename):
        self.filename = filename + self.suffix

        fd, self.path = tempfile.mkstemp(
            dir=temp_root, prefix='%s_' % filename)

        self._fd = self._buildFile(fd)

    def _buildFile(self, fd):
        return os.fdopen(fd, 'wb')

    def write(self, content):
        self._fd.write(content)

    def close(self):
        self._fd.close()

    def __del__(self):
        """Remove temporary file if it was left behind. """
        if self.path is not None and os.path.exists(self.path):
            os.remove(self.path)


class GzipTempFile(PlainTempFile):
    suffix = '.gz'

    def _buildFile(self, fd):
        return gzip.GzipFile(fileobj=os.fdopen(fd, "wb"))


class Bzip2TempFile(PlainTempFile):
    suffix = '.bz2'

    def _buildFile(self, fd):
        os.close(fd)
        return bz2.BZ2File(self.path, mode='wb')


class RepositoryIndexFile:
    """Facilitates the publication of repository index files.

    It allows callsites to publish index files in different medias
    (plain, gzip and bzip2) transparently and atomically.
    """

    def __init__(self, root, temp_root, filename):
        """Store repositories destinations and filename.

        The given 'temp_root' needs to exist, on the other hand, 'root'
        will be created on `close` if it doesn't exist.

        Additionally creates the needs temporary files in the given
        'temp_root'.
        """
        self.root = root
        assert os.path.exists(temp_root), (
            'Temporary root does not exist.')

        self.index_files = (
            PlainTempFile(temp_root, filename),
            GzipTempFile(temp_root, filename),
            Bzip2TempFile(temp_root, filename),
            )

    def write(self, content):
        """Write contents to all target medias."""
        for index_file in self.index_files:
            index_file.write(content)

    def close(self):
        """Close temporary media and atomically publish them.

        If necessary the given 'root' destination is created at this point.

        It also fixes the final files permissions making them readable and
        writable by their group and readable by others.
        """
        if os.path.exists(self.root):
            assert os.access(
                self.root, os.W_OK), "%s not writeable!" % self.root
        else:
            os.makedirs(self.root)

        for index_file in self.index_files:
            index_file.close()
            root_path = os.path.join(self.root, index_file.filename)
            os.rename(index_file.path, root_path)
            # XXX julian 2007-10-03
            # This is kinda papering over a problem somewhere that causes the
            # files to get created with permissions that don't allow
            # group/world read access.
            # See https://bugs.launchpad.net/soyuz/+bug/148471
            mode = stat.S_IMODE(os.stat(root_path).st_mode)
            os.chmod(root_path,
                     mode | stat.S_IWGRP | stat.S_IRGRP | stat.S_IROTH)
