-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Create the todelete schema. We can no longer just DROP TABLE, because
-- tables will first need to be removed from any replication sets. Instead,
-- we just rename then. upgrade.py can then detect our intentions and
-- do the labour.
CREATE SCHEMA ToDrop;

/*
Drop foreign key constraints between EmailAddress and Person, and between
Person and Account, and between MailingListSubscription and EmailAddress.
We cannot have foreign key constraints across replication
sets, and code will just have to cope if it tries to access a row that
no longer exists or has not yet been replicated.
*/

ALTER TABLE MailingListSubscription
    DROP CONSTRAINT mailinglistsubscription__person__email_address__fk;

ALTER TABLE EmailAddress
    DROP CONSTRAINT emailaddress__account__person__fk,
    DROP CONSTRAINT emailaddress_person_fk,
    DROP CONSTRAINT emailaddress__person__id__key;

CREATE INDEX emailaddress__person__status__idx ON EmailAddress(person, status);
DROP INDEX emailaddress_person_status_idx;

DROP INDEX person_name_key;
ALTER TABLE Person
    DROP CONSTRAINT person_account_fkey,
    DROP CONSTRAINT person__account__id__key,
    ADD CONSTRAINT person__account__key UNIQUE (account),
    ADD CONSTRAINT person__name__key UNIQUE (name);

-- Fix some bugs in the schema that replication picked up. Neither of these
-- tables is in use yet.
ALTER TABLE PackageBugSupervisor
    ADD CONSTRAINT packagebugsupervisor__bug_supervisor__fk
        FOREIGN KEY (bug_supervisor) REFERENCES Person;
ALTER SEQUENCE sourcepackagereleasefile_id_seq
    OWNED BY SourcePackageReleaseFile.id;
ALTER SEQUENCE binarypackagefile_id_seq OWNED BY BinaryPackageFile.id;
ALTER SEQUENCE packaging_id_seq OWNED BY Packaging.id;
ALTER SEQUENCE spokenin_id_seq OWNED BY SpokenIn.id;
ALTER SEQUENCE productreleasefile_id_seq OWNED BY ProductReleaseFile.id;
DROP SEQUENCE sourcepackagerelationship_id_seq;
DROP SEQUENCE branchrelationship_id_seq;
DROP SEQUENCE distributionrole_id_seq;
DROP SEQUENCE projectbugtracker_id_seq;

-- Can't use is_team as a constraint as the result is mutable.
ALTER TABLE Poll DROP CONSTRAINT is_team;

-- Drop the foreign key constraint on OAuthNonce so it can live in the
-- authdb replication set. This constraint should be reinstated if
-- the OAuthAccessToken table is moved too.
ALTER TABLE OauthNonce DROP CONSTRAINT oauthnonce_access_token_fkey;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 1, 0);

