-- This script ensures that every Person has a Wikiname for
-- http://www.ubuntulinux.com/wiki/, using the displayname as the basis for the
-- default wikiname.

CREATE OR REPLACE FUNCTION generate_wikinames() RETURNS integer AS '
    import re

    existing_wikinames = set(
        [row["wikiname"].decode("utf-8")
            for row
            in plpy.execute("""
            SELECT wikiname FROM WikiName
            WHERE wiki = \'http://www.ubuntulinux.com/wiki/\'""")]
        )

    target_people = plpy.execute("""
        SELECT Person.id, Person.name, Person.displayname
            FROM Person LEFT OUTER JOIN WikiName
                ON Person.id = WikiName.person
            WHERE WikiName.person IS NULL
        """)

    num = 0
    for row in target_people:
        person, displayname = row["id"], row["displayname"].decode("UTF-8")

        wikinameparts = re.split(r"(?u)\\W+", displayname)
        base_wikiname = "".join([part.capitalize() for part in wikinameparts])
        wikiname = base_wikiname

        counter = 2
        while wikiname in existing_wikinames:
            wikiname = base_wikiname + str(counter)
            counter += 1

        existing_wikinames.add(wikiname)
        
        p = plpy.prepare("""
            INSERT INTO WikiName(person, wiki, wikiname)
            VALUES ($1, ''http://www.ubuntulinux.com/wiki/'', $2)
            """, ["numeric", "text"])
        plpy.execute(p, [person, wikiname.encode("UTF-8")])
        num += 1
    return num
' LANGUAGE plpythonu;

SELECT generate_wikinames();
 
DROP FUNCTION generate_wikinames();

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 34, 0);

