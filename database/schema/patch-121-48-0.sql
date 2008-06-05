SET client_min_messages=ERROR;

--
-- Create and populate the Account table
--
CREATE TABLE Account (
    id serial NOT NULL PRIMARY KEY,
    date_created timestamp WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    creation_rationale integer NOT NULL,
    status integer NOT NULL,
    date_status_set timestamp WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    displayname text NOT NULL,
    openid_identifier text UNIQUE NOT NULL
        DEFAULT (generate_openid_identifier()),
    status_comment text
    );

INSERT INTO Account(
    id, date_created, creation_rationale, status, date_status_set,
    status_comment, openid_identifier, displayname)
SELECT id, datecreated, COALESCE(creation_rationale, 1),
    account_status, datecreated, account_status_comment,
    openid_identifier, displayname
    FROM Person
    WHERE teamowner IS NULL; -- Not teams


-- Add a trigger to update the date_status_set on status change
CREATE TRIGGER set_date_status_set_t BEFORE UPDATE ON Account
FOR EACH ROW EXECUTE PROCEDURE set_date_status_set();

--
-- Create and populate the AccountPassword table.
--
CREATE TABLE AccountPassword (
    id serial PRIMARY KEY,
    account integer NOT NULL UNIQUE REFERENCES Account ON DELETE CASCADE,
    password text NOT NULL
    );

INSERT INTO AccountPassword(id, account, password)
SELECT id, id, password FROM Person
WHERE password IS NOT NULL AND teamowner IS NULL;


-- We just inserted a load of records without using the primary key
-- sequences. Update the sequences so nextval() gives the new correct value.
CREATE FUNCTION update_seq(tname text) RETURNS boolean LANGUAGE plpgsql AS $$
DECLARE
    max_id integer;
BEGIN
    EXECUTE 'SELECT max(id) FROM ' || tname INTO max_id;
    IF max_id IS NOT NULL THEN
        EXECUTE 'ALTER SEQUENCE ' || tname || '_id_seq RESTART WITH '
            || max_id + 1;
    END IF;
    RETURN TRUE;
END;
$$;
SELECT update_seq('account'), update_seq('accountpassword');
DROP FUNCTION update_seq(text);


--
-- Update the Person table, dropping the columns migrated to new tables.
--
DROP TRIGGER set_openid_identifier_t ON Person;
DROP TRIGGER temp_t_set_openid_identifier ON Person;
ALTER TABLE Person
    DROP COLUMN account_status,
    DROP COLUMN account_status_comment,
    DROP COLUMN openid_identifier,
    DROP COLUMN password,
    -- account FK constraint will go with replication
    ADD COLUMN account integer REFERENCES Account ON DELETE SET NULL,
    ADD CONSTRAINT teams_have_no_account CHECK (
        account IS NULL OR teamowner IS NULL);

    -- This index for EmailAddress foreign key constraint, ensuring
    -- all EmailAddresses for a given Account reference the same Person.
ALTER TABLE Person
    ADD CONSTRAINT person__account__id__key UNIQUE(account, id);

UPDATE Person SET account=Account.id
    FROM Account WHERE Person.id = Account.id;

--
-- Update the EmailAddress table.
--
ALTER TABLE EmailAddress
    ALTER COLUMN person DROP NOT NULL,
    ADD COLUMN account integer;
UPDATE EmailAddress SET account=Person.account
FROM Person WHERE EmailAddress.person = Person.id;
ALTER TABLE EmailAddress
    ADD CONSTRAINT emailaddress__account__fk
        FOREIGN KEY (account) REFERENCES Account ON DELETE SET NULL,
    ADD CONSTRAINT emailaddress__account__person__fk
        FOREIGN KEY (account, person) REFERENCES Person(account, id)
        ON DELETE SET NULL
        DEFERRABLE INITIALLY DEFERRED,
    ADD CONSTRAINT emailaddress__is_linked__chk
        CHECK (person IS NOT NULL OR account IS NOT NULL);

-- Rebuild this index with a better name
DROP INDEX idx_emailaddress_email;
CREATE INDEX emailaddress__lower_email__key ON EMailAddress(lower(email));

-- And this index is just crack. Only one PREFERRED emailaddress per person.
-- Might as well enforce one per account too, which also speeds up some
-- queries.
DROP INDEX emailaddress_person_key;
CREATE UNIQUE INDEX emailaddress__person__key ON EmailAddress(person)
    WHERE status=4 AND person IS NOT NULL;
CREATE UNIQUE INDEX emailaddress__account__key ON EmailAddress(account)
    WHERE status=4 AND account IS NOT NULL;

-- ValidPersonOrTeamCache can no longer be a materialized view, as we want
-- Person and Account to be on seperate physical databases. We replace it
-- with a view. We can't drop it, as it is required to allow Person.is_valid
-- lookups to not hit the DB by preloading the SQLObject
-- ValidPersonCache objects.
DROP TABLE ValidPersonOrTeamCache;
DROP TRIGGER mv_validpersonorteamcache_person_t ON Person;
DROP TRIGGER mv_validpersonorteamcache_emailaddress_t ON EmailAddress;

CREATE VIEW ValidPersonCache AS
    SELECT EmailAddress.person AS id
    FROM EmailAddress, Account
    WHERE
        EmailAddress.account = Account.id
        AND EmailAddress.person IS NOT NULL
        AND EmailAddress.status = 4
        AND Account.status = 20;

CREATE VIEW ValidPersonOrTeamCache AS
    SELECT id FROM ValidPersonCache
    UNION ALL
    SELECT id FROM Person WHERE teamowner IS NOT NULL;

-- Person.account_status has not been maintained :-( Fix the data, as we
-- now need this to be correct.
UPDATE Account SET status=20
FROM EmailAddress, AccountPassword
WHERE EmailAddress.account = Account.id
    AND AccountPassword.account = Account.id
    AND Account.status=10 AND EmailAddress.status=4;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 48, 0);
