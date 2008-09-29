SET client_min_messages=ERROR;

CREATE TABLE TranslationRelicensingAgreement (
    id serial PRIMARY KEY,
    person integer NOT NULL
        CONSTRAINT translationrelicensingagreement__person__fk
            REFERENCES Person
        CONSTRAINT translationrelicensingagreement__person__key
            UNIQUE,
    allow_relicensing boolean DEFAULT TRUE NOT NULL,
    date_decided timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

--CREATE INDEX translationrelicensingagreement__person__idx
--    ON TranslationRelicensingAgreement(person);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 23, 0);
