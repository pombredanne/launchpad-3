from lp.services.config import config
BROKER_URL = "amqplib://%s" % config.rabbitmq.host
CELERY_RESULT_BACKEND = "amqp"
