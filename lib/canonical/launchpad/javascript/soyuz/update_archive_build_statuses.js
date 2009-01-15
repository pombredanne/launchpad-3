// Functionality for updating the Launchpad Archive and PPA pages.
YUI.add('soyuz.update_archive_build_statuses', function(Y){

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
     * shouldStopUpdating
     *
     * This function knows whether the dynamic updating should continue
     * when it is passed the expected data such as {total: 5, pending: 3}.
     */
    var shouldStopUpdating = function(data_object){
        // Stop updating only when there are zero pending builds:
        return data_object.pending === 0;
    };

    /*
     * Initialization of the dynamic table updates.
     */
    Y.on("contentready", function(){
        // Grab the Archive build count table and tell it how to
        // update itself:
        var table = Y.get('table#build-count-table');
        var config = {
            owner: table,
            dom_update_function: updateArchiveBuildStatusSummary,
            uri: LP.client.cache.context.self_link,
            api_method_name: 'getBuildCounters',
            stop_updates_check: shouldStopUpdating
        };
        table.plug(LP.DynamicDomUpdater, config);
    }, "table#build-count-table");
}, '0.1', {requires:['node', 'lazr.anim', 'lazr.dynamic_dom_updater']});
