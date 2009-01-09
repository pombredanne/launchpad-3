/* Copyright (c) 2008, Canonical Ltd. All rights reserved. */
//
// This file contains functions to upadet build statuses on Launchpad
// Archive and PPA pages. There are two functions corresponding to
// the two areas being updated:
//
// * updateArchiveBuildStatusSummary - which updates the Build Status
//   summary table,
// * updatePackageTableBuildStatuses - which updates the build statuses of
//   packages in the source package table.
//
// Both functions are then used with the DynamicDomUpdater plugin, enabling
// the DOM subtrees to update themselves.
//
YUI().use("node", "lazr.anim", "anim", function(Y) {

    /*
     * updateArchiveBuildStatusSummary
     *
     * This function knows how to update an Archive Build Status summary
     * table, when given an object of the form:
     *   {total: 5, failed: 3}
     */
    var updateArchiveBuildStatusSummary = function(table_node, data_object){
        var td_nodelist = table_node.getElementsByTagName('td');

        // For each node of the table's td elements
        td_nodelist.each(function(node){
            // Check whether the node has a class matching the data name
            // of the passed in data, and if so, set the innerHTML to
            // thecorresponding value.
            Y.each(data_object, function(data_value, data_name){
                if (node.hasClass(data_name)){
                    previous_value = node.get("innerHTML");
                    node.set("innerHTML", data_value);
                    // If the value changed, just put a quick anim
                    // on the parent row.
                    if (previous_value != data_value.toString()){
                        var anim = Y.lazr.anim.green_flash({
                            node: node.get("parentNode")
                        });
                        anim.run();
                    }
                }
            });
        });
    };

    /*
     * shouldStopUpdatingStatusSummary
     *
     * This function knows whether the dynamic updating should continue
     * when it is passed the expected data such as {total: 5, pending: 3}.
     */
    var shouldStopUpdatingStatusSummary = function(data_object){
        // Stop updating only when there are zero pending builds:
        return data_object.pending === 0;
    };

    /*
     * Initialization of the build count summary dynamic table updates.
     */
//    Y.on("contentready", function(){
//        // Grab the Archive build count table and tell it how to
//        // update itself:
//        var table = Y.get('table#build-count-table');
//        var config = {
//            dom_update_function: updateArchiveBuildStatusSummary,
//            uri: LP.client.cache.context.self_link,
//            api_method_name: 'getBuildCounters',
//            stop_updates_check: shouldStopUpdatingStatusSummary,
//            interval: 3000
//        };
//        table.plug(LP.DynamicDomUpdater, config);
//    }, "table#build-count-table");

    /*
     * updatePackageTableBuildStatuses
     *
     * This function knows how to update the table on PPA/Archive pages that
     * displays the current batch of source packages with their build
     * statuses.
     */
    var updatePackageTableBuildStatuses = function(table_node, data_object){
        var i = 1;
        // For each source id in the data object:
        Y.each(data_object, function(build_summary, source_id){
            // Grab the related td element (and fail silently if it doesn't
            // exist).
            var td_elem = Y.get("#pubstatus" + source_id);
            // Check and remember the current status (from the class), as
            // we'll flash if it's changed.

            // Remove all anchor links,
            // Add each anchor link for each build...

            // If the status has changed then:
                // Update the class (toggle old, toggle new)
                // delete old image and add new one
                // Add a flash animation.
        })
    }

    /*
     * getSourceIdsRequiringUpdates
     *
     * This function determines which source packages need to be checked
     * when updating the build statuses. (ie. Just those that are
     * in a pending state).
     *
     * The resulting list is returned as a string (the format required
     * for list parameters passed to LP.client.named_get)
     */
    var getSourceIdsRequiringUpdates = function(table_node){
        var td_list = table_node.getElementsByTagName('td').filter(
            '.build_status.NEEDSBUILD');
        if (td_list.length === 0){
            return null;
        }
        var source_ids = Array();
        td_list.each(function(node){
            var elem_id = node.get('id');
            var source_id = elem_id.replace('pubstatus', '');
            source_ids.push(source_id);
        });
        if (source_ids.length === 0){
            return null;
        } else {
            return "[" + source_ids.join(',') + "]";
        }
    }


    /*
     * Initialization of the package build status dynamic table updates.
     */
    Y.on("contentready", function(){
        // Grab the packages table and tell it how to update itself:
        var table = Y.get('table#packages_list');

        // Work out the source package ids that we want to update for this
        // page
        var source_ids = getSourceIdsRequiringUpdates(table);

        // We'll only bother configuring and running the updater if there's
        // something to update:
        if (source_ids !== null){
            var config = {
                dom_update_function: updatePackageTableBuildStatuses,
                uri: LP.client.cache.context.self_link,
                api_method_name: 'getBuildSummariesForSourceIds',
                parameters: {source_ids: source_ids},
                interval: 3000
            };
            table.plug(LP.DynamicDomUpdater, config);
        }
    }, "table#packages_list");
});

