set client_min_messages=ERROR;

CREATE TABLE SignedCodeOfConduct(
    id           serial NOT NULL,
    person       integer NOT NULL,
    signingkey   integer,
    datecreated  timestamp without time zone DEFAULT timezone('UTC'::text,
    ('now'::text)::timestamp(6) with time zone) NOT NULL,
    signedcode   text,
    recipient    integer,
    active       boolean NOT NULL DEFAULT FALSE,
    admincomment text
);

ALTER table gpgkey ADD CONSTRAINT gpgkey_person_idx UNIQUE(person,id); 

ALTER TABLE SignedCodeOfConduct
    ADD CONSTRAINT recipient_person_fk FOREIGN KEY (recipient)
    REFERENCES person(id);

ALTER TABLE SignedCodeOfConduct ADD CONSTRAINT person_gpg_fk
    FOREIGN KEY (person, signingkey) references gpgkey(person, id);

INSERT INTO LaunchpadDatabaseRevision VALUES (10,8,0);

