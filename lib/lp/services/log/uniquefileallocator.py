# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create uniquely named log files on disk."""


__all__ = ['UniqueFileAllocator']

__metaclass__ = type


import datetime
import errno
import os.path
import stat
import threading

import pytz


UTC = pytz.utc

# the section of the ID before the instance identifier is the
# days since the epoch, which is defined as the start of 2006.
epoch = datetime.datetime(2006, 01, 01, 00, 00, 00, tzinfo=UTC)


class UniqueFileAllocator:
    """Assign unique file names to logs being written from an app/script.

    UniqueFileAllocator causes logs written from one process to be uniquely
    named. It is not safe for use in multiple processes with the same output
    root - each process must have a unique output root.
    """

    def __init__(self, output_root, log_type, log_subtype):
        """Create a UniqueFileAllocator.

        :param output_root: The root directory that logs should be placed in.
        :param log_type: A string to use as a prefix in the ID assigned to new
            logs. For instance, "OOPS".
        :param log_subtype: A string to insert in the generate log filenames
            between the day number and the serial. For instance "T" for
            "Testing".
        """
        self._lock = threading.Lock()
        self._output_root = output_root
        self._last_serial = 0
        self._last_output_dir = None
        self._log_type = log_type
        self._log_subtype = log_subtype
        self._log_token = ""

    def _findHighestSerialFilename(self, directory=None, time=None):
        """Find details of the last log present in the given directory.

        This function only considers logs with the currently
        configured log_subtype.

        One of directory, time must be supplied.

        :param directory: Look in this directory.
        :param time: Look in the directory that a log written at this time
            would have been written to. If supplied, supercedes directory.
        :return: a tuple (log_serial, log_filename), which will be (0,
            None) if no logs are found. log_filename is a usable path, not
            simply the basename.
        """
        if directory is None:
            directory = self.output_dir(time)
        prefix = self.get_log_infix()
        lastid = 0
        lastfilename = None
        for filename in os.listdir(directory):
            logid = filename.rsplit('.', 1)[1]
            if not logid.startswith(prefix):
                continue
            logid = logid[len(prefix):]
            if logid.isdigit() and (lastid is None or int(logid) > lastid):
                lastid = int(logid)
                lastfilename = filename
        if lastfilename is not None:
            lastfilename = os.path.join(directory, lastfilename)
        return lastid, lastfilename

    def _findHighestSerial(self, directory):
        """Find the last serial actually applied to disk in directory.

        The purpose of this function is to not repeat sequence numbers
        if the logging application is restarted.

        This method is not thread safe, and only intended to be called
        from the constructor (but it is called from other places in
        integration tests).
        """
        return self._findHighestSerialFilename(directory)[0]

    def getFilename(self, log_serial, time):
        """Get the filename for a given log serial and time."""
        log_subtype = self.get_log_infix()
        # TODO: Calling output_dir causes a global lock to be taken and a
        # directory scan, which is bad for performance. It would be better
        # to have a split out 'directory name for time' function which the
        # 'want to use this directory now' function can call.
        output_dir = self.output_dir(time)
        second_in_day = time.hour * 3600 + time.minute * 60 + time.second
        return os.path.join(
            output_dir, '%05d.%s%s' % (
            second_in_day, log_subtype, log_serial))

    def get_log_infix(self):
        """Return the current log infix to use in ids and file names."""
        return self._log_subtype + self._log_token

    def newId(self, now=None):
        """Returns an (id, filename) pair for use by the caller.

        The ID is composed of a short string to identify the Launchpad
        instance followed by an ID that is unique for the day.

        The filename is composed of the zero padded second in the day
        followed by the ID.  This ensures that reports are in date order when
        sorted lexically.
        """
        if now is not None:
            now = now.astimezone(UTC)
        else:
            now = datetime.datetime.now(UTC)
        # We look up the error directory before allocating a new ID,
        # because if the day has changed, errordir() will reset the ID
        # counter to zero.
        self.output_dir(now)
        self._lock.acquire()
        try:
            self._last_serial += 1
            newid = self._last_serial
        finally:
            self._lock.release()
        subtype = self.get_log_infix()
        day_number = (now - epoch).days + 1
        log_id = '%s-%d%s%d' % (self._log_type, day_number, subtype, newid)
        filename = self.getFilename(newid, now)
        return log_id, filename

    def output_dir(self, now=None):
        """Find or make the directory to allocate log names in.

        Log names are assigned within subdirectories containing the date the
        assignment happened.
        """
        if now is not None:
            now = now.astimezone(UTC)
        else:
            now = datetime.datetime.now(UTC)
        date = now.strftime('%Y-%m-%d')
        result = os.path.join(self._output_root, date)
        if result != self._last_output_dir:
            self._lock.acquire()
            try:
                self._last_output_dir = result
                # make sure the directory exists
                try:
                    os.makedirs(result)
                except OSError, e:
                    if e.errno != errno.EEXIST:
                        raise
                # Make sure the directory permission is set to: rwxr-xr-x
                permission = (
                    stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)
                os.chmod(result, permission)
                # TODO: Note that only one process can do this safely: its not
                # cross-process safe, and also not entirely threadsafe:
                # another # thread that has a new log and hasn't written it
                # could then use that serial number. We should either make it
                # really safe, or remove the contention entirely and log
                # uniquely per thread of execution.
                self._last_serial = self._findHighestSerial(result)
            finally:
                self._lock.release()
        return result

    def listRecentReportFiles(self):
        now = datetime.datetime.now(UTC)
        yesterday = now - datetime.timedelta(days=1)
        directories = [self.output_dir(now), self.output_dir(yesterday)]
        for directory in directories:
            report_names = os.listdir(directory)
            for name in sorted(report_names, reverse=True):
                yield directory, name

    def setToken(self, token):
        """Append a string to the log subtype in filenames and log ids.

        :param token: a string to append..
            Scripts that run multiple processes can use this to create a
            unique identifier for each process.
        """
        self._log_token = token
