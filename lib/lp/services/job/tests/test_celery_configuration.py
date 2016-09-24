# Copyright 2012-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from contextlib import contextmanager

from testtools.matchers import MatchesRegex

from lp.services.config import config
from lp.testing import TestCase
from lp.testing.layers import RabbitMQLayer


@contextmanager
def changed_config(changes):
    config.push('test_changes', changes)
    yield
    config.pop('test_changes')


class TestCeleryWorkerConfiguration(TestCase):
    layer = RabbitMQLayer

    command = ['celery', 'worker']

    def check_default_common_parameters(self, config):
        # Tests for default config values that are set for app servers
        # and for "celery worker" instances.

        # Four queues are defined; the binding key for each queue is
        # just the queue name.
        queue_names = [
            'branch_write_job', 'branch_write_job_slow',
            'bzrsyncd_job', 'bzrsyncd_job_slow', 'celerybeat',
            'launchpad_job', 'launchpad_job_slow']
        queues = config['CELERY_QUEUES']
        self.assertEqual(queue_names, sorted(queues))
        for name in queue_names:
            self.assertEqual(name, queues[name]['binding_key'])

        # The port changes between test runs.
        self.assertThat(
            config['BROKER_URL'],
            MatchesRegex(r'amqp://guest:guest@localhost:\d+//\Z'))
        self.assertFalse(config['CELERY_CREATE_MISSING_QUEUES'])
        self.assertEqual('job', config['CELERY_DEFAULT_EXCHANGE'])
        self.assertEqual('launchpad_job', config['CELERY_DEFAULT_QUEUE'])
        self.assertEqual(
            ('lp.services.job.celeryjob', ), config['CELERY_IMPORTS'])
        self.assertEqual('amqp', config['CELERY_RESULT_BACKEND'])

    def test_app_server_configuration(self):
        from lp.services.job.celeryconfig import configure
        config = configure([''])
        self.check_default_common_parameters(config)

    def check_job_specific_celery_worker_configuration(self, expected, config):
        self.check_default_common_parameters(config)
        self.assertEqual(
            expected['concurrency'], config['CELERYD_CONCURRENCY'])
        self.assertEqual(
            expected['timeout'], config['CELERYD_TASK_SOFT_TIME_LIMIT'])
        self.assertEqual(
            expected['fallback'], config.get('FALLBACK', None))

    def test_default_celery_worker_configuration_fast_lanes(self):
        from lp.services.job.celeryconfig import configure
        expected = {
            'concurrency': 3,
            'fallback': 'launchpad_job_slow',
            'timeout': 300,
            }
        config = configure(self.command + ['-Q', 'launchpad_job'])
        self.check_default_common_parameters(config)
        self.check_job_specific_celery_worker_configuration(expected, config)
        config = configure(self.command + ['-Q', 'branch_write_job'])
        self.check_default_common_parameters(config)
        expected['fallback'] = 'branch_write_job_slow'
        self.check_job_specific_celery_worker_configuration(expected, config)

    def test_default_celery_worker_configuration_slow_lanes(self):
        from lp.services.job.celeryconfig import configure
        expected = {
            'concurrency': 1,
            'fallback': None,
            'timeout': 86400,
            }
        config = configure(self.command + ['-Q', 'launchpad_job_slow'])
        self.check_default_common_parameters(config)
        self.check_job_specific_celery_worker_configuration(expected, config)
        config = configure(self.command + ['-Q', 'branch_write_job_slow'])
        self.check_default_common_parameters(config)
        self.check_job_specific_celery_worker_configuration(expected, config)

    def test_circular_fallback_lanes(self):
        # Circular fallback lanes are detected.
        # Import late because the RabbitMQ parameters are set during layer
        # setup.
        from lp.services.job.celeryconfig import (
            ConfigurationError,
            configure,
            )
        with changed_config(
            """
            [launchpad_job_slow]
            fallback_queue: launchpad_job
        """):
            error = (
                "Circular chain of fallback queues: launchpad_job already in "
                "['launchpad_job', 'launchpad_job_slow']"
                )
            self.assertRaisesWithContent(
                ConfigurationError, error, configure, [''])

    def test_missing_queue_parameter_for_celery_worker(self):
        # An exception is raised when "celery worker" is started without
        # the parameter -Q.
        # Import late because the RabbitMQ parameters are set during layer
        # setup.
        from lp.services.job.celeryconfig import (
            ConfigurationError,
            configure,
            )
        error = 'A queue must be specified.'
        self.assertRaisesWithContent(
            ConfigurationError, error, configure, self.command)

    def test_two_queues_for_celery_worker(self):
        # An exception is raised when "celery worker" is started for two
        # queues.
        # Import late because the RabbitMQ parameters are set during layer
        # setup.
        from lp.services.job.celeryconfig import (
            ConfigurationError,
            configure,
            )
        error = 'A "celery worker" instance may serve only one queue.'
        self.assertRaisesWithContent(
            ConfigurationError, error, configure,
            self.command + ['--queue=launchpad_job,branch_write_job'])

    def test_unconfigured_queue_for_celery_worker(self):
        # An exception is raised when "celery worker" is started for a queue
        # that is not configured.
        # Import late because the RabbitMQ parameters are set during layer
        # setup.
        from lp.services.job.celeryconfig import (
            ConfigurationError,
            configure,
            )
        error = 'Queue foo is not configured in schema-lazr.conf'
        self.assertRaisesWithContent(
            ConfigurationError, error, configure,
            self.command + ['--queue=foo'])


class TestCelerydConfiguration(TestCeleryWorkerConfiguration):
    """Test behaviour with legacy "celeryd" command name."""

    command = ['celeryd']
