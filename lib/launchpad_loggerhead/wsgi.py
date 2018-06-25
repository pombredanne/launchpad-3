# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'LoggerheadApplication',
    ]

import atexit
import logging
from optparse import OptionParser
import os.path
import signal
import sys
import time
import traceback

from gunicorn.app.base import Application
from gunicorn.glogging import Logger
from openid import oidutil
from paste.deploy.config import PrefixMiddleware
from paste.httpexceptions import HTTPExceptionHandler
from paste.request import construct_url
from paste.wsgilib import catch_errors

from launchpad_loggerhead.app import (
    oops_middleware,
    RootApp,
    )
from launchpad_loggerhead.session import SessionHandler
import lp.codehosting
from lp.services.config import config
from lp.services.pidfile import (
    pidfile_path,
    remove_pidfile,
    )
from lp.services.scripts import (
    logger,
    logger_options,
    )
from lp.services.scripts.logger import LaunchpadFormatter


log = logging.getLogger("loggerhead")


SESSION_VAR = "lh.session"


def log_request_start_and_stop(app):
    def wrapped(environ, start_response):
        url = construct_url(environ)
        log.info("Starting to process %s", url)
        start_time = time.time()

        def request_done_ok():
            log.info(
                "Processed ok %s [%0.3f seconds]",
                url, time.time() - start_time)

        def request_done_err(exc_info):
            log.info(
                "Processed err %s [%0.3f seconds]: %s",
                url, time.time() - start_time,
                traceback.format_exception_only(*exc_info[:2]))

        return catch_errors(
            app, environ, start_response, request_done_err, request_done_ok)

    return wrapped


class LoggerheadLogger(Logger):

    def setup(self, cfg):
        super(LoggerheadLogger, self).setup(cfg)
        formatter = LaunchpadFormatter(datefmt=None)
        for handler in self.error_log.handlers:
            handler.setFormatter(formatter)

        # Force Launchpad's logging machinery to set up the root logger the
        # way we want it.
        parser = OptionParser()
        logger_options(parser)
        log_options, _ = parser.parse_args(
            ['-q', '--ms', '--log-file=DEBUG:%s' % cfg.errorlog])
        logger(log_options)

        # Make the OpenID library use proper logging rather than writing to
        # stderr.
        oidutil.log = lambda message, level=0: log.debug(message)


def _on_starting_hook(arbiter):
    # Normally lp.services.pidfile.make_pidfile does this, but in this case
    # we have to do it ourselves since gunicorn creates the pidfile.
    atexit.register(remove_pidfile, "codebrowse")
    # Register a trivial SIGTERM handler so that the atexit hook is called
    # on SIGTERM.
    signal.signal(
        signal.SIGTERM, lambda signum, frame: sys.exit(-signal.SIGTERM))


class LoggerheadApplication(Application):

    def __init__(self, **kwargs):
        self.options = kwargs
        super(LoggerheadApplication, self).__init__()

    def init(self, parser, opts, args):
        top = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.pardir, os.pardir))
        listen_host = config.codebrowse.listen_host
        log_folder = config.codebrowse.log_folder or os.path.join(top, "logs")
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        cfg = {
            "accesslog": os.path.join(log_folder, "access.log"),
            "bind": [
                "%s:%s" % (listen_host, config.codebrowse.port),
                "%s:%s" % (listen_host, config.codebrowse.private_port),
                ],
            "capture_output": True,
            "errorlog": os.path.join(log_folder, "debug.log"),
            # Trust that firewalls only permit sending requests to
            # loggerhead via a frontend.
            "forwarded_allow_ips": "*",
            "logger_class": "launchpad_loggerhead.wsgi.LoggerheadLogger",
            "loglevel": "debug",
            "on_starting": _on_starting_hook,
            "pidfile": pidfile_path("codebrowse"),
            "preload_app": True,
            # XXX cjwatson 2018-05-15: These are gunicorn defaults plus
            # X-Forwarded-Scheme: https, which we use in staging/production.
            # We should switch the staging/production configuration to
            # something that gunicorn understands natively and then drop
            # this.
            "secure_scheme_headers": {
                "X-FORWARDED-PROTOCOL": "ssl",
                "X-FORWARDED-PROTO": "https",
                "X-FORWARDED-SCHEME": "https",
                "X-FORWARDED-SSL": "on",
                },
            # Kill threads after 300 seconds of inactivity.  This is
            # insanely high, but loggerhead is often pretty slow.
            "timeout": 300,
            "threads": 10,
            "worker_class": "gthread",
            }
        cfg.update(self.options)
        return cfg

    def _load_bzr_plugins(self):
        from bzrlib.plugin import load_plugins
        load_plugins()

        import bzrlib.plugins
        if getattr(bzrlib.plugins, "loom", None) is None:
            log.error("Loom plugin loading failed.")

    def load(self):
        self._load_bzr_plugins()

        with open(os.path.join(
                config.root, config.codebrowse.secret_path)) as secret_file:
            secret = secret_file.read()

        app = RootApp(SESSION_VAR)
        app = HTTPExceptionHandler(app)
        app = SessionHandler(app, SESSION_VAR, secret)
        app = log_request_start_and_stop(app)
        app = PrefixMiddleware(app)
        app = oops_middleware(app)

        return app
