# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from contextlib import contextmanager
import sys

from lp.services.config import config
from lp.testing import TestCase
from lp.testing.layers import RabbitMQLayer


def get_celery_configuration():
    """Return the current celeryconfiguration"""
    # Import late because the RabbitMQ parameters are set during layer setup.
    from lp.services.job import celeryconfig
    celeryconfig.configure()
    return celeryconfig


@contextmanager
def faked_command_line(argv):
    """Fake sys.argv to pretend that celeryd is started."""
    real_argv = sys.argv
    sys.argv = argv
    yield
    sys.argv = real_argv


@contextmanager
def changed_config(changes):
    config.push('test_changes', changes)
    yield
    config.pop('test_changes')


class TestCeleryConfiguration(TestCase):
    layer = RabbitMQLayer

    def tearDown(self):
        # celeryconfig.configure() defines celeryconfig.FALLBACK in some
        # tests but subsequent tests may assume that this variable does
        # not exist, so remove this variable, if it has been created
        # by a test.
        from lp.services.job import celeryconfig
        try:
            del celeryconfig.FALLBACK
        except AttributeError:
            pass
        super(TestCeleryConfiguration, self).tearDown()

    def check_default_common_parameters(self, config):
        # Tests for default config values that are set for app servers
        # and for celeryd instances.

        # Four queues are defined; the binding key for each queue is
        # just the queue name.
        queue_names = [
            'branch_write_job', 'branch_write_job_slow', 'job', 'job_slow']
        queues = config.CELERY_QUEUES
        self.assertEqual(queue_names, sorted(queues))
        for name in queue_names:
            self.assertEqual(name, config.CELERY_QUEUES[name]['binding_key'])

        self.assertEqual('localhost', config.BROKER_HOST)
        # BROKER_PORT changes between test runs, so just check that it
        # is defined.
        config.BROKER_PORT
        self.assertEqual('guest', config.BROKER_USER)
        self.assertEqual('guest', config.BROKER_PASSWORD)
        self.assertEqual('/', config.BROKER_VHOST)
        self.assertFalse(config.CELERY_CREATE_MISSING_QUEUES)
        self.assertEqual('job', config.CELERY_DEFAULT_EXCHANGE)
        self.assertEqual('job', config.CELERY_DEFAULT_QUEUE)
        self.assertEqual(
            ('lp.services.job.celeryjob', ), config.CELERY_IMPORTS)
        self.assertEqual('amqp', config.CELERY_RESULT_BACKEND)

    def test_app_server_configuration(self):
        self.check_default_common_parameters(get_celery_configuration())

    def check_job_specific_celeryd_configutartion(self, expected, config):
        self.check_default_common_parameters(config)
        self.assertEqual(expected['concurrency'], config.CELERYD_CONCURRENCY)
        self.assertEqual(
            expected['timeout'], config.CELERYD_TASK_SOFT_TIME_LIMIT)
        self.assertEqual(
            expected['fallback'], getattr(config, 'FALLBACK', None))

    def test_default_celeryd_configuration_fast_lanes(self):
        expected = {
            'concurrency': 3,
            'fallback': 'job_slow',
            'timeout': 600,
            }
        with faked_command_line(['celeryd', '-Q', 'job']):
            config = get_celery_configuration()
            self.check_default_common_parameters(config)
            self.check_job_specific_celeryd_configutartion(expected, config)
        with faked_command_line(['celeryd', '-Q', 'branch_write_job']):
            config = get_celery_configuration()
            self.check_default_common_parameters(config)
            expected['fallback'] = 'branch_write_job_slow'
            self.check_job_specific_celeryd_configutartion(expected, config)

    def test_default_celeryd_configuration_slow_lanes(self):
        expected = {
            'concurrency': 1,
            'fallback': None,
            'timeout': 86400,
            }
        with faked_command_line(['celeryd', '-Q', 'job_slow']):
            config = get_celery_configuration()
            self.check_default_common_parameters(config)
            self.check_job_specific_celeryd_configutartion(expected, config)
        with faked_command_line(['celeryd', '-Q', 'branch_write_job_slow']):
            config = get_celery_configuration()
            self.check_default_common_parameters(config)
            self.check_job_specific_celeryd_configutartion(expected, config)

    def test_circular_fallback_lanes(self):
        # Circular fallback lanes are detected.
        # Import late because the RabbitMQ parameters are set during layer
        # setup.
        from lp.services.job.celeryconfig import ConfigurationError
        with changed_config(
            """
            [job_slow]
            fallback_queue: job
        """):
            error = (
                "Circular chain of fallback queues: job already in "
                "['job', 'job_slow']"
                )
            self.assertRaisesWithContent(
                ConfigurationError, error, get_celery_configuration)

    def test_missing_queue_parameter_for_celeryd(self):
        # An exception is raised when celeryd is started without
        # the parameter -Q.
        # Import late because the RabbitMQ parameters are set during layer
        # setup.
        from lp.services.job.celeryconfig import ConfigurationError
        with faked_command_line(['celeryd']):
            error = 'A queue must be specified.'
            self.assertRaisesWithContent(
                ConfigurationError, error, get_celery_configuration)

    def test_two_queues_for_celeryd(self):
        # An exception is raised when celeryd is started for two queues.
        # Import late because the RabbitMQ parameters are set during layer
        # setup.
        from lp.services.job.celeryconfig import ConfigurationError
        with faked_command_line(['celeryd', '--queue=job,branch_write_job']):
            error = 'A celeryd instance may serve only one queue.'
            self.assertRaisesWithContent(
                ConfigurationError, error, get_celery_configuration)

    def test_unconfigured_queue_for_celeryd(self):
        # An exception is raised when celeryd is started for a queue that
        # is not configured.
        # Import late because the RabbitMQ parameters are set during layer
        # setup.
        from lp.services.job.celeryconfig import ConfigurationError
        with faked_command_line(['celeryd', '--queue=foo']):
            error = 'Queue foo is not configured in schema-lazr.conf'
            self.assertRaisesWithContent(
                ConfigurationError, error, get_celery_configuration)
