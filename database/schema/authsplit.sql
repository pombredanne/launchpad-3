\pset pager off
ABORT; BEGIN;

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
    id, person, date_created, creation_rationale, status,
    status_comment, openid_identifier, displayname)
SELECT id, id, datecreated, COALESCE(creation_rationale, 0),
    account_status, account_status_comment, openid_identifier, displayname
    FROM Person;

--CREATE TRIGGER set_openid_identifier_t
--    BEFORE INSERT ON Account
--    FOR EACH ROW EXECUTE PROCEDURE set_openid_identifier();


--
-- Create and populate the AccountPassword table.
--
CREATE TABLE AccountPassword (
    id serial PRIMARY KEY,
    account integer NOT NULL UNIQUE REFERENCES Account,
    password text NOT NULL
    );

INSERT INTO AccountPassword(id, account, password)
SELECT id, id, password FROM Person WHERE password IS NOT NULL;


-- We just inserted a load of records without using the primary key
-- sequences. Update the sequences so nextval() gives the new correct value.
CREATE FUNCTION update_seq(tname text) RETURNS boolean LANGUAGE plpgsql AS $$
DECLARE
    max_id integer;
BEGIN
    EXECUTE 'SELECT max(id) FROM ' || tname INTO max_id;
    EXECUTE 'ALTER SEQUENCE ' || tname || '_id_seq RESTART WITH '
        || max_id + 1;
    RETURN TRUE;
END;
$$;
SELECT update_seq('account'), update_seq('accountpassword');
DROP FUNCTION update_seq(text);

DROP TRIGGER mv_validpersonorteamcache_person_t ON Person; -- XXX: Replace


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
ALTER TABLE EmailAddress
    ADD CONSTRAINT emailaddress__account__fk
        FOREIGN KEY (account) REFERENCES Account,
    ADD CONSTRAINT emailaddress__account__person__fk
        FOREIGN KEY (account, person) REFERENCES Account(id, person);

-- Rebuild this index with a better name
DROP INDEX idx_emailaddress_email;
CREATE INDEX emailaddress__lower_email__key ON EMailAddress(lower(email));

/*
-- We are losing the ensure-emailaddress-belongs-to-that-person constraint.
-- Because MailingListSubscription and EmailAddress will be
-- in seperate replication sets, there will be a window when a
-- MailingListSubscription points to a non-existant EmailAddress and we
-- need to cope. We also need to ensure that code that changes EmailAddres
-- records updates the MailingListSubscription records - the constraint
-- currently is ON UPDATE CASADE so we haven't had to do this manually.
ALTER TABLE MailingListSubscription
    DROP CONSTRAINT mailinglistsubscription__person__email_address__fk;

ALTER TABLE EmailAddress DROP CONSTRAINT emailaddress__person__id__key;
ALTER TABLE EmailAddress RENAME person TO account;
ALTER TABLE EmailAddress DROP CONSTRAINT emailaddress_person_fk;
ALTER TABLE EmailAddress ADD CONSTRAINT emailaddress__account__fk
    FOREIGN KEY (account) REFERENCES Account;

DROP INDEX emailaddress_person_key;
CREATE UNIQUE INDEX emailaddress__account_preferred__key
    ON EmailAddress(account) WHERE status = 4;
DROP INDEX idx_emailaddress_email;
CREATE UNIQUE INDEX emailaddress__lower_email__idx
    ON EmailAddress(lower(email));
DROP INDEX emailaddress_person_status_idx;
CREATE INDEX emailaddress__account__status__idx
    ON EmailAddress(account, status);


-- Recreate BranchWithSortKeys view
SELECT
    branch.id, branch.title, branch.summary, branch.owner, branch.product,
    branch.author, branch.name, branch.home_page, branch.url,
    branch.whiteboard, branch.lifecycle_status, branch.last_mirrored,
    branch.last_mirror_attempt, branch.mirror_failures, branch.pull_disabled,
    branch.mirror_status_message, branch.last_scanned, branch.last_scanned_id,
    branch.last_mirrored_id, branch.date_created, branch.revision_count,
    branch.next_mirror_time, branch.private, branch.branch_type,
    branch.reviewer, branch.merge_robot, branch.merge_control_status,
    branch.date_last_modified, branch.registrant,
    product.name AS product_name, author.displayname AS author_name,
    owner.displayname AS owner_name
    FROM branch
    JOIN person AS owner ON branch.owner = owner.id
    LEFT JOIN product ON branch.product = product.id
    LEFT JOIN person AS author ON branch.author = author.id
    LEFT JOIN emailaddress AS owneremailaddress
        ON owner.primary_email = owneremailaddress.id
    LEFT JOIN account AS owneraccount
        ON owneremailaddress.account = account.id
    LEFT JOIN emailaddress AS authoremailaddress
        ON author.primary_email = authoremailaddress.id
    LEFT JOIN authoraccount
        ON authoremailaddress.account = account.id




-- TODO: Add trigger to Person for validpersonorteamcache
DROP TRIGGER mv_validpersonorteamcache_emailaddress_t ON EmailAddress;
*/

\d Account
\d EmailAddress
\d Person
