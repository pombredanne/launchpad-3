SET client_min_messages=ERROR;

DELETE FROM WikiName WHERE id NOT IN (
    SELECT min(id) FROM WikiName
        WHERE wiki='http://www.ubuntulinux.com/wiki/'
        GROUP BY person
    );

CREATE UNIQUE INDEX one_launchpad_wikiname ON WikiName(person)
    WHERE wiki='http://www.ubuntulinux.com/wiki/';

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 10, 1);

