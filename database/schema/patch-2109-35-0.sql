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
UPDATE shippingrequest SET is_admin_request = TRUE
    WHERE recipient = 243601;
-- Requests which had shipit-admins as the recipient will now have Salgado
-- as the recipient.  Note that recipient should probably be renamed to
-- requester, as that's what it really represents.
UPDATE shippingrequest
    SET recipient_account = (SELECT account FROM person WHERE name = 'salgado')
    WHERE recipient = 243601;


-----------  DROP existing COLUMNS  ----------------------------
ALTER TABLE shippingrequest DROP COLUMN recipient;
ALTER TABLE shippingrequest DROP COLUMN whoapproved;
ALTER TABLE shippingrequest DROP COLUMN whocancelled;
ALTER TABLE shipitsurvey DROP COLUMN person;


-----------  RENAME new COLUMNS  ----------------------------
ALTER TABLE shippingrequest RENAME COLUMN recipient_account TO recipient;
ALTER TABLE shippingrequest RENAME COLUMN whoapproved_account TO whoapproved;
ALTER TABLE shippingrequest RENAME COLUMN whocancelled_account TO whocancelled;


----------- Add constraints to new COLUMNS  ----------------------------
ALTER TABLE shippingrequest ALTER COLUMN recipient SET NOT NULL;
ALTER TABLE shipitsurvey ALTER COLUMN account SET NOT NULL;
CREATE UNIQUE INDEX shippingrequest_one_outstanding_request_unique 
    ON shippingrequest USING btree (recipient)
    WHERE ((
	    (shipment IS NULL) AND ((status <> 3) AND (status <> 2))
	   )
           AND (is_admin_request <> TRUE)
          );

INSERT INTO LaunchpADDatabaseRevision VALUES (2109, 35, 0);
