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

-- Create a function that refreshes a person's or team's entry in
-- ValidPersonOrTeamCache whenever the Person table is updated.
CREATE OR REPLACE FUNCTION mv_validpersonorteamcache_person() RETURNS TRIGGER
VOLATILE SECURITY DEFINER AS $$
    # This trigger function could be simplified by simply issuing
    # one DELETE followed by one INSERT statement. However, we want to minimize
    # expensive writes so we use this more complex logic.

    if not SD.has_key("delete_plan"):
        param_types = ["int4"]
        SD["old_is_valid"] = plpy.prepare("""
            SELECT COUNT(*) > 0 AS is_valid
            FROM ValidPersonOrTeamCache WHERE id = $1
            """, param_types)

        SD["delete_plan"] = plpy.prepare("""
            DELETE FROM ValidPersonOrTeamCache WHERE id = $1
            """, param_types)

        SD["insert_plan"] = plpy.prepare("""
            INSERT INTO ValidPersonOrTeamCache (id) VALUES ($1)
            """, param_types)

    new = TD["new"]
    old = TD["old"]

    # We should always have new, as this is not a DELETE trigger
    assert new is not None, 'New is None'

    person_id = new["id"]
    query_params = [person_id] # All the same

    # Short circuit if this is a new person (not team), as it cannot
    # be valid until a status == 4 EmailAddress entry has been created
    if old is None:
        if new["teamowner"] is not None:
            plpy.execute(SD["insert_plan"], query_params)
        return

    # Short circuit if there are no relevant changes
    if (new["teamowner"] == old["teamowner"]
        and new["password"] == old["password"]
        and new["merged"] == old["merged"]):
        return

    # This function is only dealing with updates to the Person table.
    # This means we do not have to worry about EmailAddress changes here

    if (new["merged"] is not None
        or (new["teamowner"] is None and new["password"] is None)
        ):
        plpy.execute(SD["delete_plan"], query_params)

    else:
        old_is_valid = plpy.execute(
            SD["old_is_valid"], query_params, 1
            )[0]["is_valid"]
        if not old_is_valid:
            plpy.execute(SD["insert_plan"], query_params)
$$ LANGUAGE plpythonu;

CREATE TRIGGER mv_validpersonorteamcache_person_t
AFTER INSERT OR UPDATE ON Person
FOR EACH ROW EXECUTE PROCEDURE mv_validpersonorteamcache_person();

-- Create a function that refreshes a person's or team's entry in
-- ValidPersonOrTeamCache whenever the EmailAddress table is updated.
CREATE FUNCTION mv_validpersonorteamcache_emailaddress() RETURNS TRIGGER
VOLATILE SECURITY DEFINER AS $$
    # This trigger function keeps the ValidPersonOrTeamCache materialized
    # view in sync when updates are made to the EmailAddress table.
    # Note that if the corresponding person is a team, changes to this table
    # have no effect.
    if not SD.has_key("delete_plan"):
        param_types = ["int4"]

        SD["is_team"] = plpy.prepare("""
            SELECT teamowner IS NOT NULL AS is_team FROM Person WHERE id = $1
            """, param_types)

        SD["delete_plan"] = plpy.prepare("""
            DELETE FROM ValidPersonOrTeamCache WHERE id = $1
            """, param_types)

        SD["insert_plan"] = plpy.prepare("""
            INSERT INTO ValidPersonOrTeamCache (id) VALUES ($1)
            """, param_types)

        SD["maybe_insert_plan"] = plpy.prepare("""
            INSERT INTO ValidPersonOrTeamCache (id)
            SELECT Person.id FROM Person, EmailAddress
            WHERE Person.id = $1
                AND EmailAddress.person = $1
                AND status = 4
                AND merged IS NULL
                AND password IS NOT NULL
            """, param_types)

    def is_team(person_id):
        """Return true if person_id corresponds to a team"""
        if person_id is None:
            return False
        return plpy.execute(SD["is_team"], [person_id], 1)[0]["is_team"]

    class NoneDict:
        def __getitem__(self, key):
            return None

    old = TD["old"] or NoneDict()
    new = TD["new"] or NoneDict()

    PREF = 4

    # Short circuit if neither person nor status has changed
    if old["person"] == new["person"] and old["status"] == new["status"]:
        return

    # Short circuit if we are not mucking around with preferred email
    # addresses
    if old["status"] != PREF and new["status"] != PREF:
        return

    # Note that we have a constraint ensuring that there is only one
    # status == PREF email address per person at any point in time.
    # This simplifies our logic, as we know that if old.status == PREF,
    # old.person does not have any other preferred email addresses.
    # Also if new.status == PREF, we know new.person previously did not
    # have a preferred email address.

    if old["person"] != new["person"]:
        if old["status"] == PREF and not is_team(old["person"]):
            # old.person is no longer valid, unless they are a team
            plpy.execute(SD["delete_plan"], [old["person"]])
        if new["status"] == PREF and not is_team(new["person"]):
            # new["person"] is now valid, or unchanged if they are a team
            plpy.execute(SD["insert_plan"], [new["person"]])

    elif old["status"] == PREF and not is_team(old["person"]):
        # No longer valid, or unchanged if they are a team
        plpy.execute(SD["delete_plan"], [old["person"]])

    elif new["status"] == PREF and not is_team(new["person"]):
        # May now be valid, or unchanged if they are a team.
        plpy.execute(SD["maybe_insert_plan"], [new["person"]])

$$ LANGUAGE plpythonu;

CREATE TRIGGER mv_validpersonorteamcache_emailaddress_t
AFTER INSERT OR UPDATE OR DELETE ON EmailAddress
FOR EACH ROW EXECUTE PROCEDURE mv_validpersonorteamcache_emailaddress();

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 1, 0);

