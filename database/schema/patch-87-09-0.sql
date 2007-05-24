SET client_min_messages=ERROR;

ALTER TABLE Specification ADD COLUMN private boolean NOT NULL DEFAULT FALSE;

CREATE TABLE SpecificationMessage (
    id serial PRIMARY KEY,
    specification integer CONSTRAINT specificationmessage__specification__fk
        REFERENCES Specification,
    message integer CONSTRAINT specificationmessage__message__fk
        REFERENCES Message
    );

CREATE UNIQUE INDEX specificationmessage__specification__message__idx
    ON SpecificationMessage(specification, message);


-- New column: "don't accept PO imports for this release just now"
ALTER TABLE DistroRelease ADD COLUMN defer_translation_imports boolean
    NOT NULL DEFAULT TRUE;

UPDATE DistroRelease SET defer_translation_imports = FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 9, 0);

