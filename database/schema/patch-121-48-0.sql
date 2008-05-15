--\pset pager off
--ABORT; BEGIN;

SET client_min_messages=ERROR;

--
-- Create and populate the Account table
--
CREATE TABLE Account (
    id serial NOT NULL PRIMARY KEY,
                            -- person FK constraint will go with replication
    person integer UNIQUE REFERENCES Person,
    date_created timestamp WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    creation_rationale integer NOT NULL,
    status integer NOT NULL,
    date_status_set timestamp WITHOUT TIME ZONE -- XXX: trigger maint
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    status_comment text, -- XXX: Or just whiteboard for admin only?
    displayname text NOT NULL,
    openid_identifier text UNIQUE NOT NULL
        DEFAULT (generate_openid_identifier()),

        -- This index for EmailAddress foreign key constraint, ensuring
        -- all EmailAddresses for a given Account reference the same Person.
    CONSTRAINT account__id__person__key UNIQUE (id, person)
    );

INSERT INTO Account(
    id, person, date_created, creation_rationale, status, date_status_set,
    status_comment, openid_identifier, displayname)
SELECT id, id, datecreated, COALESCE(creation_rationale, 0),
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
WHERE password IS NOT NULL AND account_status <> 10; -- Not 'No account'


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
ALTER TABLE Person
    DROP COLUMN account_status,
    DROP COLUMN account_status_comment,
    DROP COLUMN openid_identifier,
    DROP COLUMN password;
DROP TRIGGER set_openid_identifier_t ON Person;
DROP TRIGGER temp_t_set_openid_identifier ON Person;

--
-- Update the EmailAddress table.
--
ALTER TABLE EmailAddress
    ALTER COLUMN person DROP NOT NULL,
    ADD COLUMN account integer;
UPDATE EmailAddress SET account=Account.id
FROM Account WHERE EmailAddress.person = Account.person;
ALTER TABLE EmailAddress
    ADD CONSTRAINT emailaddress__account__fk
        FOREIGN KEY (account) REFERENCES Account ON DELETE SET NULL,
    ADD CONSTRAINT emailaddress__account__person__fk
        FOREIGN KEY (account, person) REFERENCES Account(id, person);

-- Rebuild this index with a better name
DROP INDEX idx_emailaddress_email;
CREATE INDEX emailaddress__lower_email__key ON EMailAddress(lower(email));

-- ValidPersonOrTeamCache becomes a view for now. It should be removed
-- completely. We can't maintain a materialized view accross databases.
/*DROP TABLE ValidPersonOrTeamCache;
CREATE VIEW ValidPersonOrTeamCache AS
    SELECT Person.id
    FROM Person
    WHERE merged IS NULL AND teamowner IS NOT NULL
    UNION ALL
    SELECT Person.id
    FROM Person, EmailAddress, Account, AccountPassword
    WHERE Person.id = EmailAddress.person
        AND Person.id = Account.person
        AND EmailAddress.account = Account.id
        AND AccountPassword.account = Account.id
        AND Person.merged IS NULL AND Person.teamowner IS NULL
        AND EmailAddress.status

    FROM Person, EmailAddress, Account
    WHERE Person.id = EmailAddress.person
        AND Person.id = Account.person
        AND Account.id = EmailAddress.account
        AND EmailAddress.status = 4*/


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 48, 0);
