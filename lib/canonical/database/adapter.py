# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from psycopgda.adapter import PsycopgAdapter

from canonical.config import config


class LaunchpadDatabaseAdapter(PsycopgAdapter):
    """A subclass of PsycopgAdapter that performs some additional
    connection setup.
    """

    def _connection_factory(self):
        connection = PsycopgAdapter._connection_factory(self)

        if config.launchpad.db_statement_timeout is not None:
            print 'setting timeout to %d' % config.launchpad.db_statement_timeout
            cursor = connection.cursor()
            cursor.execute('SET statement_timeout TO %d' %
                           config.launchpad.db_statement_timeout)
            connection.commit()

        return connection
