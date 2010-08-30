# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from datetime import datetime
import gzip
import os

from contrib import apachelog
from lazr.uri import URI
import pytz
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.geoip import IGeoIP
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.services.apachelogparser.model.parsedapachelog import ParsedApacheLog


parser = apachelog.parser(apachelog.formats['extended'])


def get_files_to_parse(root, file_names):
    """Return an iterator of file and position where reading should start.

    The lines read from that position onwards will be the ones that have not
    been parsed yet.

    :param root: The directory where the files are stored.
    :param file_names: The names of the files.
    """
    store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    for file_name in file_names:
        file_path = os.path.join(root, file_name)
        fd, file_size = get_fd_and_file_size(file_path)
        first_line = unicode(fd.readline())
        parsed_file = store.find(ParsedApacheLog, first_line=first_line).one()
        position = 0
        if parsed_file is not None:
            # This file has been parsed already; we'll now check if there's
            # anything in it that hasn't been parsed yet.
            if parsed_file.bytes_read >= file_size:
                # There's nothing new in it for us to parse, so just skip it.
                fd.close()
                continue
            else:
                # This one has stuff we haven't parsed yet, so we'll just
                # parse what's new.
                position = parsed_file.bytes_read

        yield fd, position


def get_fd_and_file_size(file_path):
    """Return a file descriptor and the file size for the given file path.

    The file descriptor will have the default mode ('r') and will be seeked to
    the beginning.

    The file size returned is that of the uncompressed file, in case the given
    file_path points to a gzipped file.
    """
    if file_path.endswith('.gz'):
        fd = gzip.open(file_path)
        # There doesn't seem to be a better way of figuring out the
        # uncompressed size of a file, so we'll read the whole file here.
        file_size = len(fd.read())
        # Seek back to the beginning of the file as if we had just opened
        # it.
        fd.seek(0)
    else:
        fd = open(file_path)
        file_size = os.path.getsize(file_path)
    return fd, file_size


def parse_file(fd, start_position, logger, get_download_key):
    """Parse the given file starting on the given position.

    Return a dictionary mapping file_ids (from the librarian) to days to
    countries to number of downloads.
    """
    # Seek file to given position, read all lines.
    fd.seek(start_position)
    next_line = fd.readline()

    parsed_bytes = start_position

    geoip = getUtility(IGeoIP)
    downloads = {}
    parsed_lines = 0

    # Check for an optional max_parsed_lines config option.
    max_parsed_lines = getattr(
        config.launchpad, 'logparser_max_parsed_lines', None)

    while next_line:
        if max_parsed_lines is not None and parsed_lines >= max_parsed_lines:
            break

        line = next_line

        # Always skip the last line as it may be truncated since we're
        # rsyncing live logs, unless there is only one line for us to
        # parse, in which case This probably means we're dealing with a
        # logfile that has been rotated already, so it should be safe to
        # parse its last line.
        try:
            next_line = fd.next()
        except StopIteration:
            if parsed_lines > 0:
                break

        try:
            parsed_lines += 1
            parsed_bytes += len(line)
            host, date, status, request = get_host_date_status_and_request(
                line)

            if status != '200':
                continue

            method, path = get_method_and_path(request)

            if method != 'GET':
                continue

            download_key = get_download_key(path)

            if download_key is None:
                # Not a file or request that we care about.
                continue

            # Get the dict containing this file's downloads.
            if download_key not in downloads:
                downloads[download_key] = {}
            file_downloads = downloads[download_key]

            # Get the dict containing these day's downloads for this file.
            day = get_day(date)
            if day not in file_downloads:
                file_downloads[day] = {}
            daily_downloads = file_downloads[day]

            country_code = None
            geoip_record = geoip.getRecordByAddress(host)
            if geoip_record is not None:
                country_code = geoip_record['country_code']
            if country_code not in daily_downloads:
                daily_downloads[country_code] = 0
            daily_downloads[country_code] += 1
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, e:
            # Update parsed_bytes to the end of the last line we parsed
            # successfully, log this as an error and break the loop so that
            # we return.
            parsed_bytes -= len(line)
            logger.error('Error (%s) while parsing "%s"' % (e, line))
            break


    if parsed_lines > 0:
        logger.info('Parsed %d lines resulting in %d download stats.' % (
            parsed_lines, len(downloads)))

    return downloads, parsed_bytes


def create_or_update_parsedlog_entry(first_line, parsed_bytes):
    """Create or update the ParsedApacheLog with the given first_line."""
    first_line = unicode(first_line)
    store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    parsed_file = store.find(ParsedApacheLog, first_line=first_line).one()
    if parsed_file is None:
        ParsedApacheLog(first_line, parsed_bytes)
    else:
        parsed_file.bytes_read = parsed_bytes
        parsed_file.date_last_parsed = datetime.now(pytz.UTC)


def get_day(date):
    """Extract the day from the given date and return it as a datetime."""
    date, offset = apachelog.parse_date(date)
    # After the call above, date will be in the 'YYYYMMDD' format, but we need
    # to break it into pieces that can be fed to datetime().
    year, month, day = date[0:4], date[4:6], date[6:8]
    return datetime(int(year), int(month), int(day))


def get_host_date_status_and_request(line):
    """Extract the host, date, status and request from the given line."""
    # The keys in the 'data' dictionary below are the Apache log format codes.
    data = parser.parse(line)
    return data['%h'], data['%t'], data['%>s'], data['%r']


def get_method_and_path(request):
    """Extract the method of the request and path of the requested file."""
    L = request.split()
    # HTTP 1.0 requests might omit the HTTP version so we must cope with them.
    if len(L) == 2:
        method, path = L
    else:
        method, path, protocol = L

    if path.startswith('http://') or path.startswith('https://'):
        uri = URI(path)
        path = uri.path

    return method, path
