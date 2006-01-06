SET client_min_messages=ERROR;

CREATE INDEX bugattachment_message_idx ON BugAttachment(message);

ALTER TABLE Milestone DROP COLUMN title;
ALTER TABLE Milestone ALTER COLUMN product DROP NOT NULL;
ALTER TABLE Milestone ADD COLUMN distribution
    integer CONSTRAINT milestone_distribution_fk REFERENCES Distribution;
ALTER TABLE Milestone ADD COLUMN dateexpected
    timestamp WITHOUT TIME ZONE;
ALTER TABLE Milestone ADD COLUMN visible boolean;
UPDATE Milestone SET visible = true;
ALTER TABLE Milestone ALTER COLUMN visible SET NOT NULL;
ALTER TABLE Milestone ALTER COLUMN visible SET DEFAULT true;
ALTER TABLE Milestone ADD CONSTRAINT milestone_product_id_key
    UNIQUE (product, id);
ALTER TABLE Milestone ADD CONSTRAINT milestone_distribution_id_key
    UNIQUE (distribution, id);
ALTER TABLE Milestone DROP CONSTRAINT milestone_product_key;
ALTER TABLE Milestone ADD CONSTRAINT milestone_name_product_key
    UNIQUE (name, product);
ALTER TABLE Milestone ADD CONSTRAINT milestone_name_distribution_key
    UNIQUE (name, distribution);
ALTER TABLE Milestone ADD CONSTRAINT valid_target CHECK (
    NOT (product IS NULL AND distribution IS NULL));

-- Nuke dud milestones. Product changed after milestone assigned (?)
UPDATE BugTask SET milestone=NULL
    FROM Milestone
    WHERE bugtask.milestone = milestone.id
        AND bugtask.product <> milestone.product;


ALTER TABLE BugTask DROP CONSTRAINT bugtask_milestone_fk;
ALTER TABLE BugTask ADD CONSTRAINT bugtask_product_milestone_fk
    FOREIGN KEY (product, milestone)
    REFERENCES Milestone (product, id);
ALTER TABLE BugTask ADD CONSTRAINT bugtask_distribution_milestone_fk
    FOREIGN KEY (distribution, milestone)
    REFERENCES Milestone (distribution, id);

--- XXX MarkShuttleworth - I don't think you can require product or distro
/*
ALTER TABLE BugTask ADD CONSTRAINT valid_milestone
    CHECK (milestone IS NULL OR
        (milestone IS NOT NULL AND
            (product IS NOT NULL OR distribution IS NOT NULL)));
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (25,10,0);

