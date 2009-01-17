// Functionality for updating the Launchpad Archive and PPA pages.
YUI.add('soyuz.update_archive_repository_size', function(Y){

    /*
     * updateArchiveRepositorySizeSummary
     *
     * This function knows how to update an Archive Repository Size
     * section, when given an object of the form:
     *   {sources_size: 100, binaries_size: 2, estimated_size: 103}
     */
     var updateRepositorySizeSummary = function(section_node, data_object){
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

         // XXX cprov 20090117: cannot make it work, it doesn't work either
         // for upload_archive_build_status.
         //var anim = Y.lazr.anim.green_flash({
         //   node: section_node
         //    });
         //anim.run();
    };

    var updateOnce = function(data_object){
        // Only update the repository section once.
        return true;
    };

    /*
     * Initialization of the dynamic table updates.
     */
    Y.on("contentready", function(){
        // Grab the Archive build count table and tell it how to
        // update itself:
        var size_summary_node = Y.get('#package_counters');
        var config = {
            owner: size_summary_node,
            dom_update_function: updateRepositorySizeSummary,
            uri: LP.client.cache.context.self_link,
            api_method_name: 'getRepositorySizeSummary',
            interval: 1000,
            stop_updates_check: updateOnce
        };
        size_summary_node.plug(LP.DynamicDomUpdater, config);
    }, "#package_counters");
}, '0.1', {requires:['node', 'lazr.anim', 'lazr.dynamic_dom_updater']});
