SET client_min_messages=ERROR;

CREATE TABLE POFileTranslator (
    id serial PRIMARY KEY,
    person int NOT NULL
        CONSTRAINT pofiletranslator__person__fk REFERENCES Person,
    pofile int NOT NULL
        CONSTRAINT pofiletranslator__pofile__fk REFERENCES POFile,
    latest_posubmission int NOT NULL
        CONSTRAINT personpofile__latest_posubmission__fk
        REFERENCES POSubmission INITIALLY DEFERRED,
    date_last_touched timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT pofiletranslator__person__pofile__key UNIQUE (person, pofile)
    );

INSERT INTO POFileTranslator (
    person, pofile, latest_posubmission, date_last_touched
    )
    SELECT DISTINCT ON (POSubmission.person, POMsgSet.pofile)
        POSubmission.person, POMsgSet.pofile,
        POSubmission.id, POSubmission.datecreated
    FROM
        POSubmission, POMsgSet
    WHERE
        POSubmission.pomsgset = POMsgSet.id
    ORDER BY POSubmission.person, POMsgSet.pofile,
        POSubmission.datecreated DESC, POSubmission.id DESC;
        

CREATE TRIGGER mv_pofiletranslator_posubmission
AFTER INSERT OR UPDATE OR DELETE ON POSubmission FOR EACH ROW
EXECUTE PROCEDURE mv_pofiletranslator_posubmission();

CREATE TRIGGER mv_pofiletranslator_pomsgset
BEFORE UPDATE OR DELETE ON POMsgSet FOR EACH ROW
EXECUTE PROCEDURE mv_pofiletranslator_pomsgset();

CREATE INDEX pofiletranslator__date_last_touched__idx
    ON pofiletranslator(date_last_touched);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 19, 0);
