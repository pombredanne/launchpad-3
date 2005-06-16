SET client_min_messages=ERROR;

-- Rename sequence on backup table, attempting to work around restore bug
alter table potranslationsighting_id_seq rename to
    potranslationsightingbackup_id_seq;
alter table potranslationsightingbackup alter column id
    set default nextval('potranslationsightingbackup_id_seq');

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 21, 1);

