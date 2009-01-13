/* Copyright (c) 2008, Canonical Ltd. All rights reserved. */
//
// This file uses the LP.DynamicDomUpdater plugin for two separate tables
// on the archive/ppa page.
//
// The first is the Archive/PPA Build Summary table, the configuration of
// which is set in build_summary_table_dynamic_update_config.
//
// The second is the Archive/PPA source package table, the configuration of
// which is set in source_package_table_dynamic_update_config.
//
YUI().use("node", "lazr.anim", "anim", function(Y) {

    var build_summary_table_dynamic_update_config = {
        uri: null, // Note: we have to defer setting the uri until later as
                   // the LP.client.cache is not initialized until the end
                   // of the page.
        api_method_name: 'getBuildCounters',
        interval: 3000,
        /*
         * dom_update_function
         *
         * This function knows how to update an Archive Build Status summary
         * table, when given an object of the form:
         *   {total: 5, failed: 3}
         */
        dom_update_function: function(table_node, data_object){
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
        },

        /*
         * stop_updates_check
         *
         * This function knows whether the Archive Build Summary status
         * table should stop dynamic updating. It checks whether there are
         * any pending builds.
         */
        stop_updates_check: function(table_node){
            // Stop updating only when there are zero pending builds:
            var pending_elem = table_node.query("td.pending");
            if (pending_elem == null){
                return true;
            }
            var pending_val = pending_elem.get("innerHTML");
            return pending_val == "0";
        }

    }


    /*
     * Initialization of the build count summary dynamic table updates.
     */
    Y.on("contentready", function(){
        // Grab the Archive build count table and tell it how to
        // update itself:
        var table = Y.get('table#build-count-table');
        build_summary_table_dynamic_update_config.uri = 
            LP.client.cache.context.self_link;
        table.plug(LP.DynamicDomUpdater, build_summary_table_dynamic_update_config);
    }, "table#build-count-table");

    var source_package_table_dynamic_update_config = {
        uri: null, // Note: we have to defer setting the uri until later as
                   // the LP.client.cache is not initialized until the end
                   // of the page.
        api_method_name: 'getBuildSummariesForSourceIds',
        interval: 3000,

        /*
         * dom_update_function
         *
         * This custom function knows how to update the table on PPA/Archive
         * pages that displays the current batch of source packages with their
         * build statuses.
         */
        dom_update_function: function(table_node, data_object){
            // For each source id in the data object:
            Y.each(data_object, function(build_summary, source_id){
                // Grab the related td element (and fail silently if it doesn't
                // exist).
                var td_elem = Y.get("#pubstatus" + source_id);
                if (td_elem == null){
                    return;
                }

                // We'll need to remember whether we've change the UI so that
                // we can add a flash at the end if we do:
                var td_ui_changed = false;

                // If the status has changed then we need to update the td
                // element's class and image:
                if (!td_elem.hasClass(build_summary.status)){
                    td_ui_changed = true;

                    // Update the class on the td element
                    td_elem.setAttribute("class", "build_status");
                    td_elem.addClass(build_summary.status);

                    // Change the src and title etc of the image
                    // The following seems to return one node when only one
                    // is present, contrary to :
                    var img_node = td_elem.getElementsByTagName('img');
                    if (img_node !== null){
                        var new_src = null;
                        var new_title = '';
                        switch(build_summary.status){
                        case 'BUILDING':
                            new_src = '/@@/build-building';
                            new_title = 'There are some builds currently ' + 
                                        'building.';
                            break;
                        case 'NEEDSBUILD':
                            new_src = '/@@/build-needed';
                            new_title = 'There are some builds waiting to ' + 
                                        'be built.';
                            break;
                        case 'FAILEDTOBUILD':
                            new_src = '/@@/no';
                            new_title = 'There were build failures.';
                            break;
                        default:
                            new_src = '/@@/yes';
                            new_title = 'All builds were built successfully.';
                        };
                        img_node.setAttribute("src", new_src);
                        img_node.setAttribute("title", new_title);
                        img_node.setAttribute("alt", new_title);
                    }

                    // Delete all the links for builds for the old status
                    // (forcing the new ones to be linked in below):
                    td_elem.getElementsByTagName('a').each(function(link){
                        var removed_node = td_elem.removeChild(link);
                        removed_node = null;
                    })
                }

                // If the length of the builds linked has changed, then assume
                // the ui has changed, otherwise
                var current_build_links = td_elem.getElementsByTagName('a');
                if (current_build_links == null){
                    num_current_links = 0;
                } else {
                    num_current_links = current_build_links.size();
                }
                if (build_summary.builds.length != num_current_links){
                    td_ui_changed = true;

                    // Remove the old links if there are any:
                    if (current_build_links !== null){
                        current_build_links.each(function(current_link){
                            var removed_node = td_elem.removeChild(current_link);
                            removed_node = null;
                        })
                    }

                    // Add the new links, unless the status summary is
                    // fullybuilt:
                    if (build_summary.status != "FULLYBUILT"){
                        Y.each(build_summary.builds, function(build){
                            var build_href = build.self_link.replace(
                                /\/api\/[^\/]*\//, '/');
                            var new_link = Y.Node.create(
                                "<a>" + build.arch_tag + "</a>");
                            new_link.setAttribute("href", build_href);
                            new_link.setAttribute("title", build.title);
                            td_elem.appendChild(new_link);
                        })
                    }
                }

                // Finally, add an animation if we've changed...
                if (td_ui_changed){
                    var anim = Y.lazr.anim.green_flash({node: td_elem});
                    anim.run();
                }

            })
        },

        /*
         * getBuildSummaryParameters
         *
         * This function determines which source packages need to be checked
         * when updating the build statuses. (ie. Just those that are
         * in a pending state).
         *
         * The resulting list is returned as an object.containing the
         * 'source_ids' parameter.
         */
        parameter_evaluator_function: function(table_node){
            // Grab all the td's with the class 'build_status' and an additional
            // class of either 'NEEDSBUILD' or 'BUILDING':
            // Note: filter('.NEEDSBUILD, .BUILDING') returns []
            var td_list = table_node.queryAll('td.build_status');
            var tds_needsbuild = td_list.filter(".NEEDSBUILD");
            var tds_building = td_list.filter(".BUILDING");

            if (tds_needsbuild == null && tds_building == null){
                return null;
            }

            var source_ids = Array();
            var appendSourceIdForTD = function(node){
                var elem_id = node.get('id');
                var source_id = elem_id.replace('pubstatus', '');
                source_ids.push(source_id);
            }
            Y.each(tds_needsbuild, appendSourceIdForTD);
            Y.each(tds_building, appendSourceIdForTD);

            if (source_ids.length === 0){
                return null;
            } else {
                return { source_ids: "[" + source_ids.join(',') + "]"};
            }
        },

        /*
         * shouldStopUpdatingSourcePkgsTable
         *
         * This function knows whether the dynamic updating should continue
         * when it is passed the expected data such as {total: 5, pending: 3}.
         */
        stop_updates_check: function(table_node){
            // Stop updating only when there aren't any sources to update:
            var td_list = table_node.queryAll('td.build_status');
            return (td_list.filter(".NEEDSBUILD") == null &&
                    td_list.filter(".BUILDING") == null)
        }
    }

    /*
     * Initialization of the package build status dynamic table updates.
     */
    Y.on("contentready", function(){
        // Grab the packages table and tell it how to update itself:
        var table = Y.get('table#packages_list');
        source_package_table_dynamic_update_config.uri =
            LP.client.cache.context.self_link;
        table.plug(LP.DynamicDomUpdater,
                   source_package_table_dynamic_update_config);
    }, "table#packages_list");
});

