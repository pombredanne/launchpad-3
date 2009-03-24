# Copyright 2009 Canonical Ltd.  All rights reserved.


from contrib import apachelog


parser = apachelog.parser(apachelog.formats['extended'])


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
