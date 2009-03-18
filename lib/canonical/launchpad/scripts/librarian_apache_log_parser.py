# Copyright 2009 Canonical Ltd.  All rights reserved.

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
