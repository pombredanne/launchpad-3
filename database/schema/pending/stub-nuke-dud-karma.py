#!/usr/env python
'''
Remove Karma that should never have been assigned to users.
Lots and lots of rows, so we can't run this as a db patch
'''
import _pythonpath

# /*  Delete any Karma that has been assigned to a team */
# DELETE FROM Karma WHERE person IN (
#     SELECT id FROM Person WHERE teamowner IS NOT NULL
#     );
# 
# /* Delete any Karma that has been assigned to an invalid person */
# DELETE FROM Karma WHERE person NOT IN (
#     SELECT id FROM ValidPersonOrTeamCache
#     );

from canonical.database.sqlbase import connect

BATCHSIZE = 3000

def main():
    con = connect('postgres')
    con.set_isolation_level(0)
    cur = con.cursor()
    count = 0
    num_deleted = BATCHSIZE
    while num_deleted == BATCHSIZE:
        cur.execute("""
            DELETE FROM Karma WHERE id IN (
                SELECT Karma.id
                FROM Karma, Person
                LEFT OUTER JOIN ValidPersonOrTeamCache
                    ON Person.id = ValidPersonOrTeamCache.id
                WHERE Karma.person = Person.id
                    AND (Person.teamowner IS NOT NULL
                        OR ValidPersonOrTeamCache.id IS NULL)
                LIMIT %d
                )
            """ % BATCHSIZE)
        num_deleted = cur.rowcount
        assert num_deleted != -1, "No delete count returned"
        assert num_deleted is not None, "No delete count returned (got None)"
        count += num_deleted
        print count

if __name__ == '__main__':
    main()
