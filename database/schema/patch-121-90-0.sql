SET client_min_messages=ERROR;

CREATE TABLE RelicensingTranslations (
    id integer NOT NULL,
    person integer NOT NULL,
    allow_relicensing boolean DEFAULT true NOT NULL,
    date_decided timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL
);

CREATE SEQUENCE relicensingtranslations_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE relicensingtranslations_id_seq OWNED BY relicensingtranslations.id;

ALTER TABLE ONLY RelicensingTranslations
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES person(id);

CREATE INDEX relicensingtranslations__person__idx ON RelicensingTranslations USING btree (person);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 90, 0);
