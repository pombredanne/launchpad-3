SET client_min_messages=ERROR;

ALTER TABLE Branch
    DROP CONSTRAINT branch_robotic_control;

ALTER TABLE Branch
    ADD CONSTRAINT branch_merge_control
        CHECK(merge_robot IS NULL OR merge_control_status IN (3,4));

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 69, 0);
