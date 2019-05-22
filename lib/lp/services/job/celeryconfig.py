# Copyright 2012-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from datetime import timedelta
import sys

import argparse

from lp.services.config import config


class ConfigurationError(Exception):
    """Errors raised due to misconfiguration."""


def check_circular_fallbacks(queue):
    """Check for circular fallback queues.

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


def configure(argv):
    """Set the Celery parameters.

    Doing this in a function is convenient for testing.
    """
    result = {}
    CELERY_BEAT_QUEUE = 'celerybeat'
    celery_queues = {}
    queue_names = config.job_runner_queues.queues
    queue_names = queue_names.split(' ')
    for queue_name in queue_names:
        celery_queues[queue_name] = {
            'routing_key': queue_name,
            }
        check_circular_fallbacks(queue_name)

    parser = argparse.ArgumentParser()
    parser.add_argument('-Q',  '--queues')
    args = parser.parse_known_args(argv)
    queues = args[0].queues
    # A queue must be specified as a command line parameter for each
    # "celery worker" instance, but this is not required for a Launchpad app
    # server.
    if 'celery' in argv[0] and argv[1] == 'worker':
        if queues is None or queues == '':
            raise ConfigurationError('A queue must be specified.')
        queues = queues.split(',')
        # Allow only one queue per "celery worker" instance. More than one
        # queue would require a check for consistent timeout values, and
        # especially a better way to specify a fallback queue.
        if len(queues) > 1:
            raise ConfigurationError(
                'A "celery worker" instance may serve only one queue.')
        queue = queues[0]
        if queue not in celery_queues:
            raise ConfigurationError(
                'Queue %s is not configured in schema-lazr.conf' % queue)
        # XXX wgrant 2015-08-03: This should be set in the apply_async
        # now that we're on Celery 3.1.
        result['task_soft_time_limit'] = config[queue].timeout
        if config[queue].fallback_queue != '':
            # XXX wgrant 2015-08-03: lazr.jobrunner actually looks for
            # FALLBACK_QUEUE; this probably isn't doing anything.
            result['FALLBACK'] = config[queue].fallback_queue
        # XXX wgrant 2015-08-03: This is mostly per-queue because we
        # can't run *_job and *_job_slow in the same worker, which will be
        # fixed once the CELERYD_TASK_SOFT_TIME_LIMIT override is gone.
        result['worker_concurrency'] = config[queue].concurrency

    # Don't spend too long failing when RabbitMQ isn't running.  We can fall
    # back to waiting for the job to be run via cron.
    result['broker_transport_options'] = {
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.1,
        'interval_max': 0.1,
        }
    result['broker_url'] = 'amqp://%s:%s@%s/%s' % (
        config.rabbitmq.userid, config.rabbitmq.password,
        config.rabbitmq.host, config.rabbitmq.virtual_host)
    result['beat_schedule'] = {
        'schedule-missing': {
            'task': 'lp.services.job.celeryjob.run_missing_ready',
            'schedule': timedelta(seconds=600),
            'options': {
                'routing_key': CELERY_BEAT_QUEUE,
                },
            }
        }
    result['enable_utc'] = True
    result['imports'] = ("lp.services.job.celeryjob", )
    result['result_backend'] = 'amqp'
    result['task_acks_late'] = True
    result['task_create_missing_queues'] = False
    result['task_default_exchange'] = 'job'
    result['task_default_queue'] = 'launchpad_job'
    result['task_queues'] = celery_queues
    # See http://ask.github.com/celery/userguide/optimizing.html:
    # The AMQP message of a job should stay in the RabbitMQ server
    # until the job has been finished. This allows to simply kill
    # a "celery worker" instance while a job is executed; when another
    # instance is started later, it will run the aborted job again.
    result['worker_prefetch_multiplier'] = 1

    return result

try:
    globals().update(configure(getattr(sys, 'argv', [''])))
except ConfigurationError as error:
    print >>sys.stderr, error
    sys.exit(1)
