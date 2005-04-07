SET client_min_messages=ERROR;

/* Add Distribution.members as per DistributionMembership */

ALTER TABLE Distribution ADD COLUMN members integer REFERENCES Person;
UPDATE Distribution SET members=owner;
ALTER TABLE Distribution ALTER COLUMN members SET NOT NULL ;

/* Change GPGKey.person -> GPGKey.owner and 
    SignedCodeOfConduct.person -> SignedCodeOfConduct.owner */

ALTER TABLE SignedCodeOfConduct DROP CONSTRAINT person_gpg_fk;
ALTER TABLE SignedCodeOfConduct DROP CONSTRAINT recipient_person_fk;
ALTER TABLE GPGKey DROP CONSTRAINT gpgkey_person_idx;

ALTER TABLE GPGKey RENAME person TO owner;
ALTER TABLE GPGKey ADD CONSTRAINT gpgkey_owner_key
    UNIQUE (owner, id);

ALTER TABLE SignedCodeOfConduct RENAME person TO owner;
ALTER TABLE SignedCodeOfConduct ADD CONSTRAINT signedcodeofconduct_owner_fk
    FOREIGN KEY (owner) REFERENCES Person;
ALTER TABLE SignedCodeOfConduct ADD CONSTRAINT
    signedcodeofconduct_signingkey_fk
    FOREIGN KEY (owner, signingkey) REFERENCES GPGKey(owner, id);

/* POFile.owner should be NOT NULL */
UPDATE POFile SET owner=Person.id
    FROM Person WHERE Person.name='rosetta-admins' AND POFile.owner IS NULL;
ALTER TABLE POFile ALTER COLUMN owner SET NOT NULL;

/* Tidy some more constraints */
ALTER TABLE POFile DROP CONSTRAINT "$1";
ALTER TABLE POFile ADD CONSTRAINT pofile_potemplate_fk
    FOREIGN KEY (potemplate) REFERENCES POTemplate;
ALTER TABLE POFile DROP CONSTRAINT "$2";
ALTER TABLE POFile ADD CONSTRAINT pofile_language_fk
    FOREIGN KEY (language) REFERENCES Language;
ALTER TABLE POFile DROP CONSTRAINT "$3";
ALTER TABLE POFile ADD CONSTRAINT pofile_lasttranslator_fk
    FOREIGN KEY (lasttranslator) REFERENCES Person;
ALTER TABLE POFile DROP CONSTRAINT "$4";
ALTER TABLE POFile ADD CONSTRAINT pofile_license_fk
    FOREIGN KEY (license) REFERENCES License;
ALTER TABLE POFile DROP CONSTRAINT "$5";
ALTER TABLE POFile ADD CONSTRAINT pofile_owner_fk
    FOREIGN KEY (owner) REFERENCES Person;
ALTER TABLE POFile DROP CONSTRAINT "$6";
ALTER TABLE POFile ADD CONSTRAINT pofile_rawimporter_fk
    FOREIGN KEY (rawimporter) REFERENCES Person;

INSERT INTO LaunchpadDatabaseRevision VALUES (11, 12, 0);

