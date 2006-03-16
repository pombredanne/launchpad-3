update Bug set description = summary || '\n\n' || description where summary is not null;
alter table Bug drop column summary;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);
