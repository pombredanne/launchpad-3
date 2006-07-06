SET client_min_messages=ERROR;

/*  Create an eager materialized view of 'valid' people and teams.
    Valid people have a password, have not been merged and have a preferred
    email address. All non-merged teams are valid (not that teams can be
    merged yet...).

    CREATE VIEW ValidPersonOrTeamCache AS
        SELECT id FROM Person LEFT OUTER JOIN EmailAddress
            ON Person.id = EmailAddress.person AND EmailAddress.status = 4
        WHERE teamowner IS NOT NULL OR (
            EmailAddress.id IS NOT NULL
            AND merged IS NULL AND password IS NOT NULL
            )
 */

-- Create the table to store the materialized view
CREATE TABLE ValidPersonOrTeamCache (
    id integer PRIMARY KEY REFERENCES Person ON DELETE CASCADE
    ) WITHOUT OIDS;

-- Populate the table with initial data
INSERT INTO ValidPersonOrTeamCache
    SELECT Person.id
    FROM Person
    LEFT OUTER JOIN EmailAddress
        ON Person.id = EmailAddress.person AND EmailAddress.status = 4
    WHERE
        teamowner IS NOT NULL OR (
            EmailAddress.id IS NOT NULL
            AND merged IS NULL AND password IS NOT NULL
            );

CREATE TRIGGER mv_validpersonorteamcache_person_t
AFTER INSERT OR UPDATE ON Person
FOR EACH ROW EXECUTE PROCEDURE mv_validpersonorteamcache_person();

CREATE TRIGGER mv_validpersonorteamcache_emailaddress_t
AFTER INSERT OR UPDATE OR DELETE ON EmailAddress
FOR EACH ROW EXECUTE PROCEDURE mv_validpersonorteamcache_emailaddress();

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 1, 0);

