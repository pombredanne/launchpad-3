# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import argparse
import sys
from lp.services.config import config


class ConfigurationError(Exception):
    pass


def check_circular_fallbacks(queue):
    """Check for curcular fallback queues.

    A circular chain of fallback queues could keep a job forever queued
    if it times out in all queues.
    """
    linked_queues = []
    while config[queue].fallback_queue != '':
        linked_queues.append(queue)
        queue = config[queue].fallback_queue
        if queue in linked_queues:
            raise ConfigurationError(
                'Circular chain of fallback queues: '
                '%s already in %s' % (queue, linked_queues))


def configure():
    """Set the Celery parameters.

    Doing this in a function is convenient for testing.
    """
    global BROKER_HOST
    global BROKER_PORT
    global BROKER_USER
    global BROKER_PASSWORD
    global BROKER_VHOST
    global CELERY_CREATE_MISSING_QUEUES
    global CELERY_DEFAULT_EXCHANGE
    global CELERY_DEFAULT_QUEUE
    global CELERY_IMPORTS
    global CELERY_QUEUES
    global CELERY_RESULT_BACKEND
    global CELERYD_CONCURRENCY
    global CELERYD_TASK_SOFT_TIME_LIMIT
    global FALLBACK

    CELERY_QUEUES = {}
    for queue_name in config.job_runner_queues:
        CELERY_QUEUES[queue_name] = {
            'binding_key': config.job_runner_queues[queue_name],
            }
        check_circular_fallbacks(queue_name)

    parser = argparse.ArgumentParser()
    parser.add_argument('-Q',  '--queues')
    args = parser.parse_known_args(sys.argv)
    queues = args[0].queues
    # A queue must be specified as a command line parameter for each
    # celeryd instance, but this is not required for a Launchpad app server.
    if 'celeryd' in sys.argv[0]:
        if queues is None or queues == '':
            raise ConfigurationError('A queue must be specified.')
        queues = queues.split(',')
        # Allow only one queue per celeryd instance. More than one queue
        # would require a check for consistent timeout values, and especially
        # a better way to specify a fallback queue.
        if len(queues) > 1:
            raise ConfigurationError(
                'A celeryd instance may serve only one queue.')
        queue = queues[0]
        if queue not in CELERY_QUEUES:
            raise ConfigurationError(
                'Queue %s is not configured in schema-lazr.conf' % queue)
        CELERYD_TASK_SOFT_TIME_LIMIT = config[queue].timeout
        if config[queue].fallback_queue != '':
            FALLBACK = config[queue].fallback_queue
        CELERYD_CONCURRENCY = config[queue].concurrency

    host, port = config.rabbitmq.host.split(':')
    BROKER_HOST = host
    BROKER_PORT = port
    BROKER_USER = config.rabbitmq.userid
    BROKER_PASSWORD = config.rabbitmq.password
    BROKER_VHOST = config.rabbitmq.virtual_host
    CELERY_IMPORTS = ("lp.services.job.celeryjob", )
    CELERY_RESULT_BACKEND = "amqp"
    CELERY_DEFAULT_EXCHANGE = "job"
    CELERY_DEFAULT_QUEUE = "job"
    CELERY_CREATE_MISSING_QUEUES = False

try:
    configure()
except ConfigurationError, error:
    print >>sys.stderr, error
    sys.exit(1)
