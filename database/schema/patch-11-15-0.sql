SET client_min_messages=ERROR;

ALTER TABLE GPGKey DROP CONSTRAINT "$1";
ALTER TABLE GPGKey ADD CONSTRAINT gpgkey_owner_fk 
    FOREIGN KEY ("owner") REFERENCES Person;

ALTER TABLE SignedCodeOfConduct
    DROP CONSTRAINT signedcodeofconduct_signingkey_fk;
ALTER TABLE SignedCodeOfConduct ADD CONSTRAINT
    signedcodeofconduct_signingkey_fk FOREIGN KEY ("owner", signingkey)
    REFERENCES GPGKey("owner", id) ON UPDATE CASCADE;

-- Add a flag to Person so we can tell what accounts have been merged

ALTER TABLE Person ADD COLUMN merged integer
    CONSTRAINT person_merged_fk REFERENCES Person;

INSERT INTO LaunchpadDatabaseRevision VALUES (11, 15, 0);
