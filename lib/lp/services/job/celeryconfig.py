from lp.services.config import config
host, port = config.rabbitmq.host.split(':')
BROKER_HOST = host
BROKER_PORT = port
BROKER_USER = config.rabbitmq.userid
BROKER_PASSWORD = config.rabbitmq.password
BROKER_VHOST = config.rabbitmq.virtual_host
CELERY_IMPORTS = ("lp.services.job.celeryjob", )
CELERY_RESULT_BACKEND = "amqp"
CELERY_QUEUES = {
    "branch_write_job": {"binding_key": "branch_write_job"},
    "job": {"binding_key": "job"},
}
CELERY_DEFAULT_EXCHANGE = "job"
CELERY_DEFAULT_QUEUE = "job"
CELERY_CREATE_MISSING_QUEUES = False
