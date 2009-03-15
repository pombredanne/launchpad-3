SET client_min_messages=ERROR;

----------- Create new COLUMNS  ----------------------------
ALTER TABLE shippingrequest ADD COLUMN recipient_account integer;
ALTER TABLE shippingrequest ADD COLUMN whoapproved_account integer;
ALTER TABLE shippingrequest ADD COLUMN whocancelled_account integer;
ALTER TABLE shipitsurvey ADD COLUMN account integer;
ALTER TABLE shippingrequest 
    ADD COLUMN is_admin_request boolean DEFAULT FALSE;
DROP INDEX shippingrequest_one_outstanding_request_unique;


----------- Populate new COLUMNS  ----------------------------
UPDATE shippingrequest SET recipient_account = person.account
    FROM PERSON
    WHERE shippingrequest.recipient = person.id;
UPDATE shippingrequest SET whoapproved_account = person.account
    FROM PERSON
    WHERE shippingrequest.whoapproved = person.id;
UPDATE shippingrequest SET whocancelled_account = person.account
    FROM PERSON
    WHERE shippingrequest.whocancelled = person.id;
UPDATE shipitsurvey SET account = person.account
    FROM PERSON
    WHERE shipitsurvey.person = person.id;
-- Flag requests where the recipient is shipit-admins to be admin-made
-- requests.
UPDATE shippingrequest
SET is_admin_request = TRUE
WHERE recipient = (SELECT id FROM person WHERE name='shipit-admins');
-- Requests which had shipit-admins as the recipient will now have Marilize
-- as the recipient.  Note that recipient should probably be renamed to
-- requester, as that's what it really represents.
UPDATE shippingrequest
SET recipient_account = (SELECT account FROM person WHERE name = 'marilize')
WHERE recipient = (SELECT id FROM person WHERE name='shipit-admins');


-----------  DROP existing COLUMNS  ----------------------------
ALTER TABLE shippingrequest DROP COLUMN recipient;
ALTER TABLE shippingrequest DROP COLUMN whoapproved;
ALTER TABLE shippingrequest DROP COLUMN whocancelled;
ALTER TABLE shipitsurvey DROP COLUMN person;


-----------  RENAME new COLUMNS  ----------------------------
ALTER TABLE shippingrequest RENAME COLUMN recipient_account TO recipient;
ALTER TABLE shippingrequest RENAME COLUMN whoapproved_account TO whoapproved;
ALTER TABLE shippingrequest RENAME COLUMN whocancelled_account TO whocancelled;

----------- Repack the now severely bloated tables -----------
CLUSTER shippingrequest USING shippingrequest_pkey;
CLUSTER shipitsurvey USING shipitsurvey_pkey;

----------- Create needed indexes ---------------------------
CREATE INDEX shippingrequest__recipient__idx
    ON ShippingRequest(recipient);
CREATE INDEX shippingrequest__whoapproved__idx
    ON ShippingRequest(whoapproved)
    WHERE whoapproved IS NOT NULL;
CREATE INDEX shippingrequest__whocancelled__idx
    ON ShippingRequest(whocancelled)
    WHERE whocancelled IS NOT NULL;

----------- Add constraints to new COLUMNS  ----------------------------
ALTER TABLE shippingrequest ALTER COLUMN recipient SET NOT NULL;
ALTER TABLE shipitsurvey ALTER COLUMN account SET NOT NULL;
CREATE UNIQUE INDEX shippingrequest_one_outstanding_request_unique 
    ON shippingrequest(recipient)
    WHERE (
        shipment IS NULL
        AND is_admin_request IS NOT TRUE
        AND status NOT IN (2,3));

INSERT INTO LaunchpADDatabaseRevision VALUES (2109, 40, 0);
