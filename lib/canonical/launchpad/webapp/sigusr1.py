# Copyright 2006 Canonical Ltd.  All rights reserved.
"""The SIGUSR1 handler."""

import threading
import signal
import logging


def sigusr1_handler(signum, frame):
    """Log status of running threads in response to SIGUSR1"""
    message = ['Thread summary:']
    for thread in threading.enumerate():
        message.append('\t%s' % thread.getName())
        message.append('\t\tLast Request: %s' %
                       getattr(thread, 'lp_last_request', None))
        message.append('\t\tLast five OOPS IDs: %s' %
                       ', '.join(getattr(thread, 'lp_last_oops', [])))
        message.append('\t\tLast SQL statement: %s' %
                       getattr(thread, 'lp_last_sql_statement', None))
    logging.getLogger('sigusr1').info('\n'.join(message))

def setup_sigusr1(event):
    """Configure the SIGUSR1 handler.  Called at startup."""
    signal.signal(signal.SIGUSR1, sigusr1_handler)

def before_traverse(event):
    """Record the request URL (provided that the request has a URL)"""
    request = event.request
    threading.currentThread().lp_last_request = str(
        getattr(request, 'URL', ''))

def end_request(event):
    """Record the OOPS ID in the thread, if one occurred."""
    request = event.request
    if request.oopsid is not None:
        thread = threading.currentThread()
        last_oops_ids = getattr(thread, 'lp_last_oops', [])
        # trim to at most four elements and append new ID
        thread.lp_last_oops = last_oops_ids[-4:] + [request.oopsid]
