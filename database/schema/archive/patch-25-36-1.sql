set client_min_messages=error;

alter table productrelease
    add constraint productrelease_productseries_version_key
    unique (productseries, version);

insert into launchpaddatabaserevision values (25, 36, 1);

