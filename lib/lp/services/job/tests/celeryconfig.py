import os
BROKER_VHOST = "/"
CELERY_RESULT_BACKEND = "amqp"
CELERY_IMPORTS = ("lp.services.job.celeryjob", )
CELERYD_LOG_LEVEL = 'INFO'
CELERYD_CONCURRENCY = 1
BROKER_URL = os.environ['BROKER_URL']
