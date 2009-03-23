/** Copyright (c) 2008, Canonical Ltd. All rights reserved.
 *
 * The soyuz update_archive_build_statuses module uses the LP
 * DynamicDomUpdater plugin for two separate tables on the archive/ppa
 * pages.
 *
 * The first is the Archive/PPA Build Summary table, the configuration of
 * which is set in build_summary_table_dynamic_update_config.
 *
 * The second is the Archive/PPA source package table, the configuration of
 * which is set in source_package_table_dynamic_update_config.
 */
YUI.add('soyuz.update_archive_build_statuses', function(Y){

    /**
     * Create one Launchpad client to be used by both dynamic tables.
     */
    var lp_client = new LP.client.Launchpad();

    /**
     * Configuration for the dynamic update of the build summary table
     */
    var build_summary_table_dynamic_update_config = {
        uri: null, // Note: we have to defer setting the uri until later as
                   // the LP.client.cache is not initialized until the end
                   // of the page.
        api_method_name: 'getBuildCounters',
        lp_client: lp_client,

        /**
         * This function knows how to update an Archive Build Status summary
         * table, when given an object of the form:
         *   {total: 5, failed: 3}
         *
         * @config domUpdateFunction
         */
        domUpdateFunction: function(table_node, data_object){
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

        /**
         * This function knows whether the Archive Build Summary status
         * table should stop dynamic updating. It checks whether there are
         * any pending builds.
         *
         * @config stopUpdatesCheckFunction
         */
        stopUpdatesCheckFunction: function(table_node){
            // Stop updating only when there are zero pending builds:
            var pending_elem = table_node.query("td.pending");
            if (pending_elem === null){
                return true;
            }
            var pending_val = pending_elem.get("innerHTML");
            return pending_val == "0";
        }
    };


    /*
     * Initialization of the build count summary dynamic table updates.
     */
    Y.on("domready", function(){
        // Grab the Archive build count table and tell it how to
        // update itself:
        var table = Y.get('table#build-count-table');
        build_summary_table_dynamic_update_config.uri = 
            LP.client.cache.context.self_link;
        table.plug(LP.DynamicDomUpdater, build_summary_table_dynamic_update_config);
    });

    /**
     * Configuration for the dynamic update of the source package table.
     */
    var source_package_table_dynamic_update_config = {
        uri: null, // Note: we have to defer setting the uri until later as
                   // the LP.client.cache is not initialized until the end
                   // of the page.
        api_method_name: 'getBuildSummariesForSourceIds',
        lp_client: lp_client,
        /**
         * This custom function knows how to update the table on PPA/Archive
         * pages that displays the current batch of source packages with their
         * build statuses.
         *
         * @config domUpdateFunction
         */
        domUpdateFunction: function(table_node, data_object){
            // For each source id in the data object:
            Y.each(data_object, function(build_summary, source_id){
                // Grab the related td element (and fail silently if it doesn't
                // exist).
                var td_elem = Y.get("#pubstatus" + source_id);
                if (td_elem === null){
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
                    var img_node = td_elem.query('img');
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
                        }
                        img_node.setAttribute("src", new_src);
                        img_node.setAttribute("title", new_title);
                        img_node.setAttribute("alt", new_title);
                    }

                    // Delete all the links for builds for the old status
                    // (forcing the new ones to be linked in below):
                    td_elem.getElementsByTagName('a').each(function(link){
                        td_elem.removeChild(link);
                    });
                }

                // If the length of the builds has changed, then assume
                // the ui has changed, otherwise we don't update them.
                var current_build_links = td_elem.getElementsByTagName('a');
                if (current_build_links === null){
                    num_current_links = 0;
                } else {
                    num_current_links = current_build_links.size();
                }
                if (build_summary.builds.length != num_current_links){
                    td_ui_changed = true;

                    // Remove the old links if there are any:
                    if (current_build_links !== null){
                        current_build_links.each(function(current_link){
                            td_elem.removeChild(current_link);
                        });
                    }

                    // Add the new links, unless the status summary is
                    // fullybuilt:
                    if (build_summary.status != "FULLYBUILT"){
                        Y.each(build_summary.builds, function(build){
                            // Create the web-link href from the api link:
                            var build_href = build.self_link.replace(
                                /\/api\/[^\/]*\//, '/');
                            var new_link = Y.Node.create(
                                "<a>" + build.arch_tag + " </a>");
                            new_link.setAttribute("href", build_href);
                            new_link.setAttribute("title", build.title);
                            td_elem.appendChild(new_link);
                        });
                    }
                }

                // Finally, add an animation if we've changed...
                if (td_ui_changed){
                    var anim = Y.lazr.anim.green_flash({node: td_elem});
                    anim.run();
                }

            });
        },

        /**
         * This function evaluates the parameters required for the 
         * getBuildSummariesForSourceIds api function, using the current
         * state of the DOM subtree (ie. It finds the ids of builds in the
         * subtree that are have a class of either NEEDSBUILD or BUILDING.)
         *
         * @config parameterEvaluatorFunction
         */
        parameterEvaluatorFunction: function(table_node){
            // Grab all the td's with the class 'build_status' and an additional
            // class of either 'NEEDSBUILD' or 'BUILDING':
            // Note: filter('.NEEDSBUILD, .BUILDING') returns []
            var td_list = table_node.queryAll('td.build_status');
            var tds_needsbuild = td_list.filter(".NEEDSBUILD");
            var tds_building = td_list.filter(".BUILDING");

            if (tds_needsbuild.length === 0 && tds_building.length === 0){
                return null;
            }

            var source_ids = [];
            var appendSourceIdForTD = function(node){
                var elem_id = node.get('id');
                var source_id = elem_id.replace('pubstatus', '');
                source_ids.push(source_id);
            };
            Y.each(tds_needsbuild, appendSourceIdForTD);
            Y.each(tds_building, appendSourceIdForTD);

            if (source_ids.length === 0){
                return null;
            } else {
                return { source_ids: "[" + source_ids.join(',') + "]"};
            }
        },

        /**
         * This function knows whether the dynamic updating should continue
         * or not, by examining the DOM subtree.
         */
        stopUpdatesCheckFunction: function(table_node){
            // Stop updating only when there aren't any sources to update:
            var td_list = table_node.queryAll('td.build_status');
            return (td_list.filter(".NEEDSBUILD").length === 0 &&
                    td_list.filter(".BUILDING").length === 0);
        }
    };

    /*
     * Initialization of the source package table dynamic updater.
     */
    Y.on("domready", function(){
        // Grab the packages table and tell it how to update itself.
        // Note: there are situations, such as displaying empty result
        // sets, when the table will not be on the page.
        var table = Y.get('table#packages_list');
        if (table !== null){
           source_package_table_dynamic_update_config.uri =
                LP.client.cache.context.self_link;
            table.plug(LP.DynamicDomUpdater,
                       source_package_table_dynamic_update_config);
        }
    });
}, '0.1', {requires:['node', 'lazr.anim', 'anim', 'soyuz.dynamic_dom_updater']});
