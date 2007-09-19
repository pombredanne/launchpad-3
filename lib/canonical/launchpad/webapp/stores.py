
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from storm.database import register_scheme
from storm.databases.postgres import Postgres

from canonical.config import config


class LaunchpadSessionDatabase(Postgres):

    def _connect(self):
        raw_connection = psycopg2.connect(
            user=config.launchpad.session.dbuser,
            #host=config.launchpad.session.dbhost or '',
            database=config.launchpad.session.dbname)

        raw_connection.set_client_encoding("UTF8")
        raw_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return raw_connection


register_scheme('launchpad-session', LaunchpadSessionDatabase)
