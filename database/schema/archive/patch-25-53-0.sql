
SET client_min_messages=ERROR;

-- Rename table
ALTER TABLE SpecificationReview RENAME TO SpecificationFeedback;

-- Rename sequence
ALTER TABLE specificationreview_id_seq RENAME TO specificationfeedback_id_seq;
ALTER TABLE SpecificationFeedback
    ALTER COLUMN id SET DEFAULT nextval('public.specificationfeedback_id_seq');

-- Fix primary key
ALTER TABLE SpecificationFeedback DROP CONSTRAINT specificationreview_pkey;
ALTER TABLE SpecificationFeedback ADD CONSTRAINT specificationfeedback_pkey
    PRIMARY KEY (id);

-- Recreate indexes
DROP INDEX specificationreview_reviewer_idx;
DROP INDEX specificationreview_specification_idx; -- Redundant. No recreate.
CREATE INDEX specificationfeedback_reviewer_idx
    ON SpecificationFeedback(reviewer);

-- Fix spelink
ALTER TABLE SpecificationFeedback RENAME requestor TO requester;

-- Recreate foreign key constraints
ALTER TABLE SpecificationFeedback
    ADD CONSTRAINT specificationfeedback_requester_fk
    FOREIGN KEY (requester) REFERENCES Person;
ALTER TABLE SpecificationFeedback
    DROP CONSTRAINT specificationreview_requestor_fk;

ALTER TABLE SpecificationFeedback
    ADD CONSTRAINT specificationfeedback_provider_fk
    FOREIGN KEY (reviewer) REFERENCES Person;
ALTER TABLE SpecificationFeedback
    DROP CONSTRAINT specificationreview_reviewer_fk;

ALTER TABLE SpecificationFeedback
    ADD CONSTRAINT specificationfeedback_specification_fk
    FOREIGN KEY (specification) REFERENCES Specification;
ALTER TABLE SpecificationFeedback
    DROP CONSTRAINT specificationreview_specification_fk;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 53, 0);


