SET client_min_messages=ERROR;

-- ShipitSurvey needs to reference Account. No actual foreign key
-- here because Account will be in a seperate replication set - loosely
-- consistent. 
ALTER TABLE ShipitSurvey DROP CONSTRAINT shipitsurvey_person_fkey;
DROP INDEX shipitsurvey__person__idx;
ALTER TABLE ShipitSurvey RENAME person TO account;
UPDATE ShipitSurvey SET account=Person.account
FROM Person
WHERE ShipitSurvey.account = Person.id;
CREATE INDEX shipitsurvey__account__idx ON ShipitSurvey(account);


-- Drop unwanted index
DROP INDEX shippingrequest_one_outstanding_request_unique;

-- Drop the Person foreign key constraints. We will replace these values
-- with links to account instead.
ALTER TABLE ShippingRequest
    DISABLE TRIGGER set_normalized_address,
    DISABLE TRIGGER tsvectorupdate,
    DROP CONSTRAINT shippingrequest_recipient_fk,
    DROP CONSTRAINT shippingrequest_whoapproved_fk,
    DROP CONSTRAINT shippingrequest_whocancelled_fk,
    ADD COLUMN is_admin_request boolean;

----------- Migrate data ----------------------------

-- Flag requests where the recipient is shipit-admins to be admin-made
-- requests.
UPDATE ShippingRequest SET
    is_admin_request = TRUE,
    recipient = (SELECT account FROM Person WHERE name = 'marilize')
WHERE recipient = (SELECT id FROM Person WHERE name='shipit-admins');


/*
launchpad_prod=# select count(*), whoapproved is null, whocancelled is null
launchpad_prod-# from shippingrequest
launchpad_prod-# group by whoapproved is null, whocancelled is null;
  count  | ?column? | ?column? 
---------+----------+----------
 2977876 | t        | t
  163676 | f        | t
  225091 | t        | f
      21 | f        | f
*/

UPDATE ShippingRequest SET
    recipient = RecipientPerson.account,
    is_admin_request = False
FROM
    Person AS RecipientPerson
WHERE
    ShippingRequest.recipient = RecipientPerson.id
    AND ShippingRequest.whoapproved IS NULL
    AND ShippingRequest.whocancelled IS NULL
    AND RecipientPerson.account IS NOT NULL;

UPDATE ShippingRequest SET
    recipient = RecipientPerson.account,
    whoapproved = WhoApprovedPerson.account,
    is_admin_request = False
FROM
    Person AS RecipientPerson,
    Person AS WhoApprovedPerson
WHERE
    ShippingRequest.whoapproved = WhoApprovedPerson.id
    AND ShippingRequest.recipient = RecipientPerson.id
    AND RecipientPerson.account IS NOT NULL;

UPDATE ShippingRequest SET
    recipient = RecipientPerson.account,
    whocancelled = WhoCancelledPerson.account,
    is_admin_request = False
FROM
    Person AS RecipientPerson,
    Person AS WhoCancelledPerson
WHERE
    ShippingRequest.whocancelled = WhoCancelledPerson.id
    AND ShippingRequest.recipient = RecipientPerson.id
    AND RecipientPerson.account IS NOT NULL;



----------- Add constraints to new COLUMNS  ----------------------------
ALTER TABLE shippingrequest
    ALTER COLUMN is_admin_request SET NOT NULL,
    ALTER COLUMN is_admin_request SET DEFAULT FALSE,
    ENABLE TRIGGER set_normalized_address,
    ENABLE TRIGGER tsvectorupdate;

CREATE UNIQUE INDEX shippingrequest_one_outstanding_request_unique 
    ON shippingrequest(recipient)
    WHERE (
        shipment IS NULL
        AND is_admin_request IS NOT TRUE
        AND status NOT IN (2,3));

-- Autovacuum is going to take a while, so better analyze now to
-- avoid any potential performance issues until the post-rollout autovacuum
-- run has completed.
-- ANALYZE shippingrequest;
-- ANALYZE shipitsurvey;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 40, 0);
