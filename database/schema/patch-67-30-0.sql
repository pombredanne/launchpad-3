SET client_min_messages=ERROR;

ALTER TABLE POSelection ADD COLUMN reviewer integer REFERENCES Person(id);
ALTER TABLE POSelection ADD COLUMN date_reviewed timestamp without time zone;

CREATE INDEX poselection__reviewer__idx ON POSelection(reviewer);

/*
-- Migrate data. We don't have reviewing information, so we use translation
-- credits as the initial data.
UPDATE POSelection
    SET reviewer = person, date_reviewed = datecreated
FROM POSubmission
WHERE poselection.activesubmission = posubmission.id;

-- Adding constraints.
ALTER TABLE POSelection
    ADD CONSTRAINT poselection_has_reviewer
        CHECK (activesubmission IS NULL OR
               (activesubmission IS NOT NULL AND reviewer IS NOT NULL));
ALTER TABLE POSelection
    ADD CONSTRAINT poselection_has_date_reviewed
        CHECK (reviewer = date_reviewed OR
               (reviewer IS NOT NULL AND date_reviewed IS NOT NULL));
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 30, 0);
