#!/usr/bin/env python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from datetime import datetime
from canonical.database.sqlbase import connect


def main():
    con = connect(user='postgres')

    cur = con.cursor()
    cur.execute("""
        SELECT POSelection.id, person, datecreated
        INTO TEMPORARY TABLE PoUp
        FROM POSelection, POSubmission
        WHERE activesubmission = posubmission.id
        """)
    cur.execute("""
        CREATE UNIQUE INDEX poup__id__key ON PoUp(id)
        """)
    count = 0
    while True:
        try:
            cur = con.cursor()
            cur.execute("""
                UPDATE POSelection
                SET reviewer=person, date_reviewed=datecreated
                FROM (
                    SELECT id, person, datecreated FROM PoUp
                    ORDER BY id LIMIT 10000
                    ) AS PoUp2
                WHERE reviewer IS NULL AND POSelection.id = PoUp2.id;
                """)
            count += cur.rowcount
            print '%s UTC Updated %d rows' % (datetime.utcnow().ctime(), count)
            cur.execute("""
                DELETE FROM PoUp
                WHERE id IN (SELECT id FROM PoUp ORDER BY id LIMIT 10000)
                """)
            if cur.rowcount == 0:
                break
        finally:
            con.commit()
    con.close()

if __name__ == '__main__':
    main()
