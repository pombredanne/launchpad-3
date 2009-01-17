/** Copyright (c) 2008, Canonical Ltd. All rights reserved.
 *
 * The soyuz update_archive_repository_size module uses the LP
 * DynamicDomUpdater plugin for  ...
 */

YUI.add('soyuz.update_archive_repository_size', function(Y){

    /**
     * Create one Launchpad client to be used by both dynamic tables.
     */
    var lp_client = new LP.client.Launchpad();

    var shouldUpdate = true;

    /**
     * Configuration for the dynamic update of the build summary table
     */
    var repository_size_dynamic_update_config = {
        uri: null, // Note: we have to defer setting the uri until later as
                   // the LP.client.cache is not initialized until the end
                   // of the page.

        api_method_name: 'getRepositorySizeSummary',

        lp_client: lp_client,

        /**
         * This function knows how to update an Archive repository section
         * when given an object of the form:
         *   {estimated_size: 1001, sources_size: 1000, binaries_size: 1}
         *
         * @config domUpdateFunction
         */
        domUpdateFunction: function(section_node, data_object){
            var ul = Y.Node.create("<ul>");
            section_node.replaceChild(ul, section_node.query('p'));

            var li_sources = Y.Node.create("<li>");
            text = data_object.number_of_sources.toString() +
                ' source packages (' +
                data_object.sources_size.toString() + ' bytes)';
            li_sources.set('innerHTML', text);
            ul.appendChild(li_sources);

            var li_binaries = Y.Node.create("<li>");
            text = data_object.number_of_binaries.toString() +
                  ' binary packages (' +
                  data_object.binaries_size.toString() + ' bytes)' ;
            li_binaries.set('innerHTML', text);
            ul.appendChild(li_binaries);

            var li_estimated = Y.Node.create("<li>");
            text = 'Estimated repository size: ' +
                data_object.estimated_size.toString() + ' bytes';
            li_estimated.set('innerHTML', text);
            ul.appendChild(li_estimated);

            var anim = Y.lazr.anim.green_flash({
                node: section_node
                });
            anim.run();
        },

        interval: 1000,

        stopUpdatesCheckFunction: function(section_node){
            // Only update the repository section once.
            if (shouldUpdate) {
                shouldUpdate = false;
                return false;
            }
            return !shouldUpdate;
        },

    };

    /*
     * Initialization of the build count summary dynamic table updates.
     */
    Y.on("domready", function(){
        // Grab the Archive repository size section and tell it how to
        // update itself:
        var size_section = Y.get('#package_counters');
        repository_size_dynamic_update_config.uri =
            LP.client.cache.context.self_link;
        size_section.plug(LP.DynamicDomUpdater,
                          repository_size_dynamic_update_config);
    });

}, '0.1', {requires:['node', 'lazr.anim', 'anim', 'soyuz.dynamic_dom_updater']});
