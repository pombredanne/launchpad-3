SET client_min_messages=ERROR;

/* Product milestone support */
CREATE TABLE Milestone (
    id SERIAL PRIMARY KEY,
    product INT NOT NULL,
    name TEXT NOT NULL,
    title TEXT NOT NULL,

    CONSTRAINT milestone_product_fk FOREIGN KEY (product)
        REFERENCES Product (id),
    CONSTRAINT milestone_product_key UNIQUE (product, name),
    CONSTRAINT valid_name CHECK (valid_name(name))
);
ALTER TABLE BugTask ADD COLUMN milestone INT NULL;
ALTER TABLE BugTask ADD CONSTRAINT bugtask_milestone_fk
    FOREIGN KEY (milestone) REFERENCES Milestone(id);
CREATE INDEX bugtask_milestone_idx ON BugTask (milestone);


/* Indexes for soyuz */
CREATE INDEX packagepublishing_status_idx ON packagepublishing(status);
CREATE INDEX distroarchrelease_architecturetag_idx
    ON distroarchrelease(architecturetag);
DROP INDEX build_component_idx;
CREATE INDEX build_sourcepackagerelease_idx ON Build(sourcepackagerelease);

UPDATE LaunchpadDatabaseRevision SET major=6, minor=23, patch=0;

