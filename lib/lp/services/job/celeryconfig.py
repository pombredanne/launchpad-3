from lp.services.config import config
BROKER_URL = "amqplib://%s" % config.rabbitmq.host
CELERY_IMPORTS = ("lp.services.job.celeryjob", )
CELERY_RESULT_BACKEND = "amqp"
CELERY_QUEUES = {
    "branch_write": {"binding_key": "branch_write"},
    "standard": {"binding_key": "standard"},
}
CELERY_DEFAULT_EXCHANGE = "standard"
CELERY_DEFAULT_QUEUE = "standard"
CELERY_CREATE_MISSING_QUEUES = False
