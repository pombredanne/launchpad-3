
alter index bug_fti rename to bug_fti_gist;
create index concurrently bug_fti on bug using gin(fti);

alter index bugtask_fti rename to bugtask_fti_gist;
create index concurrently bugtask_fti on bugtask using gin(fti);

alter index binarypackagerelease_fti rename to binarypackagerelease_fti_gist;
create index concurrently binarypackagerelease_fti on binarypackagerelease using gin(fti);

alter index cve_fti rename to cve_fti_gist;
create index concurrently cve_fti on cve using gin(fti);

alter index distribution_fti rename to distribution_fti_gist;
create index concurrently distribution_fti on distribution using gin(fti);

alter index distributionsourcepackagecache_fti rename to distributionsourcepackagecache_fti_gist;
create index concurrently distributionsourcepackagecache_fti on distributionsourcepackagecache using gin(fti);

alter index distroreleasepackagecache_fti rename to distroreleasepackagecache_fti_gist;
create index concurrently distroreleasepackagecache_fti on distroreleasepackagecache using gin(fti);

alter index message_fti rename to message_fti_gist;
create index concurrently message_fti on message using gin(fti);

alter index person_fti rename to person_fti_gist;
create index concurrently person_fti on message using gin(fti);


alter index messagechunk_fti rename to messagechunk_fti_gist;
create index concurrently messagechunk_fti on messagechunk using gin(fti);

alter index product_fti rename to product_fti_gist;
create index concurrently product_fti on product using gin(fti);

alter index project_fti rename to project_fti_gist;
create index concurrently project_fti on project using gin(fti);

alter index shippingrequest_fti rename to shippingrequest_fti_gist;
create index concurrently shippingrequest_fti on shippingrequest using gin(fti);

alter index specification_fti rename to specification_fti_gist;
create index concurrently specification_fti on specification using gin(fti);

alter index ticket_fti rename to ticket_fti_gist;
create index concurrently ticket_fti on ticket using gin(fti);



drop index bug_fti_gist;
drop index bugtask_fti_gist;
drop index binarypakagerelease_fti_gist;
drop index cve_fti_gist;
drop index distribution_fti_gist;
drop index distributionsourcepackagecache_fti_gist;
drop index distroreleasepackagecache_fti_gist;
drop index message_fti_gist;
drop index messagechunk_fti_gist;
drop index person_fti_gist;
drop index product_fti_gist;
drop index project_fti_gist;
drop index shippingrequest_fti_gist;
drop index specification_fti_gist;
drop index ticket_fti_gist;

