set client_min_messages=ERROR;

/* Attach Milestones to ProductSeries / DistroRelease

   In future we want milestones to live in the more detailed part of the
   data model. In this first step, we will add the links to series /
   distrorelease, and we will try and update all the ones we can
   automatically where there is only one series / distrorelease. In a future
   patch, after we have manually fixed up all the remaining milestones, we
   will lock down the links to series / distrorelease and remove the product
   / distro ones.
*/

 -- First link to ProductSeries and make sure its consistent with the
 -- Product

ALTER TABLE Milestone ADD COLUMN productseries integer;
ALTER TABLE Milestone ADD CONSTRAINT milestone_productseries_fk
    FOREIGN KEY (productseries) REFERENCES ProductSeries(id);
ALTER TABLE Milestone ADD CONSTRAINT milestone_product_series_fk
    FOREIGN KEY (product, productseries)
    REFERENCES ProductSeries(product, id);

 -- Now do the same for Distribution milestones

ALTER TABLE Milestone ADD COLUMN distrorelease integer;
ALTER TABLE Milestone ADD CONSTRAINT milestone_distrorelease_fk
    FOREIGN KEY (distrorelease) REFERENCES DistroRelease(id);
ALTER TABLE Milestone ADD CONSTRAINT milestone_distribution_release_fk
    FOREIGN KEY (distribution, distrorelease)
    REFERENCES DistroRelease(distribution, id);

 -- Now, for all the Milestone's on a Product which has only one series,
 -- record that as the Series for the Milestone

UPDATE Milestone
    SET productseries = ProductSeries.id
    FROM ProductSeries
    WHERE
        ProductSeries.product = Milestone.product AND
        (SELECT count(*)
            FROM ProductSeries
            WHERE product=Milestone.product) = 1;

 -- And do the same for Distribution Milestones

UPDATE Milestone
    SET distrorelease = DistroRelease.id
    FROM DistroRelease
    WHERE
        DistroRelease.distribution = Milestone.distribution AND
        (SELECT count(*)
            FROM DistroRelease
            WHERE distribution=Milestone.distribution) = 1;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 49, 0);

