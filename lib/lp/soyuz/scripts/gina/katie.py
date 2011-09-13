# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

"""Katie database handler.

Class to handle and query the katie db properly.
"""
__all__ = ['Katie']

from canonical.config import config
from canonical.database.sqlbase import connect
from canonical.launchpad.scripts import log


class Katie:
    def __init__(self, dbname, suite):
        self.suite = suite
        self.dbname = dbname
        log.info("Connecting to %s as %s" % (dbname, config.gina.dbuser))
        self.db = connect(user=config.gina.dbuser, dbname=dbname)

    #
    # Database convenience methods
    #

    def ensure_string_format(self, name):
        assert isinstance(name, basestring), repr(name)
        try:
            # check that this is unicode data
            name.decode("utf-8").encode("utf-8")
            return name
        except UnicodeError:
            # check that this is latin-1 data
            s = name.decode("latin-1").encode("utf-8")
            s.decode("utf-8")
            return s

    def commit(self):
        log.debug("Committing")
        return self.db.commit()

    def close(self):
        log.info("Closing connection")
        return self.db.close()

    def _get_dicts(self, cursor):
        names = [x[0] for x in cursor.description]
        ret = []
        for item in cursor.fetchall():
            res = {}
            for i in range(len(names)):
                res[names[i]] = item[i]
            ret.append(res)
        return ret

    def _query_to_dict(self, query, args=None):
        cursor = self._exec(query, args)
        return self._get_dicts(cursor)

    def _query(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        results = cursor.fetchall()
        return results

    def _query_single(self, query, args=None):
        q = self._query(query, args)
        if len(q) == 1:
            return q[0]
        elif not q:
            return None
        else:
            raise AssertionError(
                "%s killed us on %s %s" % (len(q), query, args))

    def _exec(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        return cursor

    #
    # Katie domain-specific bits
    #

    def getSourcePackageRelease(self, name, version):
        log.debug("Hunting for release %s / %s" % (name, version))
        ret = self._query_to_dict("""
            SELECT *
            FROM source, fingerprint
            WHERE
                source = %s AND
                source.sig_fpr = fingerprint.id AND
                version = %s""",
            (name, version))
        if not ret:
            log.debug(
                "that spr didn't turn up. Attempting to find via ubuntu")
        else:
            return ret

        # XXX kiko 2005-10-21: what to do when the ubuntu lookup fails?
        return self._query_to_dict("""SELECT * FROM source, fingerprint
                                      WHERE  source = %s
                                      AND    source.sig_fpr = fingerprint.id
                                      AND    version like '%subuntu%s'""" %
                                      ("%s", version, "%"), name)

    def getBinaryPackageRelease(self, name, version, arch):
        return self._query_to_dict("""SELECT * FROM binaries, architecture,
                                                    fingerprint
                                      WHERE  package = %s
                                      AND    version = %s
                                      AND    binaries.sig_fpr = fingerprint.id
                                      AND    binaries.architecture =
                                                architecture.id
                                      AND    arch_string = %s""",
                                        (name, version, arch))

    def getSections(self):
        return self._query("""SELECT section FROM section""")

    def getSourceSection(self, sourcepackage):
        return self._query_single("""
        SELECT section.section
          FROM section,
               override,
               suite

         WHERE override.section = section.id
           AND suite.id = override.suite
           AND override.package = %s
           AND suite.suite_name = %s
        """, (sourcepackage, self.suite))[0]
