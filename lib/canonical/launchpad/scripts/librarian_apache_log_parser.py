# Copyright 2009 Canonical Ltd.  All rights reserved.

from datetime import datetime
import os

from zope.component import getUtility

from contrib import apachelog

from canonical.launchpad.database.librarian import ParsedApacheLog
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


parser = apachelog.parser(apachelog.formats['extended'])


def get_files_to_parse(root, file_names):
    """Return a dict mapping files to the position where reading should start.

    The lines read from that position onwards will be the ones that have not
    been parsed yet.

    :param root: The directory where the files are stored.
    :param file_names: The names of the files.
    """
    files_to_parse = {}
    store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    for file_name in file_names:
        file_path = os.path.join(root, file_name)
        file_size = os.path.getsize(file_path)
        fd = open(file_path)
        first_line = unicode(fd.readline().strip())
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

        files_to_parse[fd] = position
    return files_to_parse


def parse_file(fd, start_position):
    """Parse the given file starting on the given position.

    Return a dictionary mapping days and file_ids (from the librarian) to
    number of downloads.
    """
    # Seek file to given position, read all lines.
    fd.seek(start_position)
    lines = fd.readlines()
    # Always skip the last line as it may be truncated since we're rsyncing
    # live logs.
    last_line = lines.pop(-1)
    parsed_bytes = fd.tell() - len(last_line)
    if len(lines) == 0:
        # This probably means we're dealing with a logfile that has been
        # rotated already, so it should be safe to parse its last line.
        lines = [last_line]
        parsed_bytes = fd.tell()

    downloads = {}
    for line in lines:
        date, status, request = get_date_status_and_request(line)

        if status != '200':
            continue

        method, file_id = get_method_and_file_id(request)
        if method != 'GET':
            # We're only interested in counting downloads.
            continue

        day = get_day(date)
        if day not in downloads:
            downloads[day] = {}
        daily_downloads = downloads[day]

        if file_id not in daily_downloads:
            daily_downloads[file_id] = 0
        daily_downloads[file_id] += 1

    return downloads, parsed_bytes


def get_day(date):
    """Extract the day from the given date and return it as a datetime."""
    date, offset = apachelog.parse_date(date)
    # After the call above, date will be in the 'YYYYMMDD' format, but we need
    # to break it into pieces that can be fed to datetime().
    year, month, day = date[0:4], date[4:6], date[6:8]
    return datetime(int(year), int(month), int(day))


def get_date_status_and_request(line):
    """Extract the date, status and request from the given line of log."""
    # The keys in the 'data' dictionary below are the Apache log format codes.
    data = parser.parse(line)
    return data['%t'], data['%>s'], data['%r']


def get_method_and_file_id(request):
    """Extract the method of the request and the ID of the requested file."""
    method, path, protocol = request.split(' ')
    file_id = path.split('/')[1]
    return method, file_id
