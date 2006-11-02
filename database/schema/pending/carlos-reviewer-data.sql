SET client_min_messages=ERROR;

ALTER TABLE POSelection ADD COLUMN reviewer integer REFERENCES Person(id);
ALTER TABLE POSelection ADD COLUMN date_reviewed timestamp without time zone;

-- Need to migrate data before apply this.

--ALTER TABLE POSelection ADD CONSTRAINT poselection_has_reviewer CHECK (activesubmission IS NULL OR (activesubmission IS NOT NULL AND reviewer IS NOT NULL));
--ALTER TABLE POSelection ADD CONSTRAINT poselection_has_date_reviewed CHECK (reviewer = date_reviewed OR (reviewer IS NOT NULL AND date_reviewed IS NOT NULL));

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);
