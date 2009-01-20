/** Copyright (c) 2008, Canonical Ltd. All rights reserved.
 *
 * The soyuz update_archive_repository_size module uses the LP
 * DynamicDomUpdater plugin for  ...
 */

YUI.add('soyuz.update_archive_repository_size', function(Y){

    _updates = 0;
    function updateOnce (ignore) {
        _updates += 1;
        if (_updates == 1) {
            return false;
        }
        return true;
    }

    /**
     * Configuration for the dynamic update of the repository size section.
     */
    var repository_size_dynamic_update_config = {
        uri: '+repository-size',

        interval: 1000,

        stopUpdatesCheckFunction: updateOnce,

        updateFailed: function (size_section) {
            var notice = Y.Node.create(
	        "<p style=\"line-height: 3em;\">" +
                "<img src=\"/@@/no\" style=\"padding-right: 5px;\"/>" +
                "Failed to fetch information.</p>");
	    var retry_link = Y.Node.create(
                "<a href=\"\" style=\"padding-left: 5px;\">Retry</a>");
            retry_link.on(
                "click", function (e) {
		    e.preventDefault();
		    dispatchUpdate();
		});
            notice.appendChild(retry_link);
	    size_section.replaceChild(notice, size_section.query('p'));

            var anim = Y.lazr.anim.red_flash({
                node: size_section
                });
            anim.run();
	},

        domUpdateFunction: function(size_section, response){
            size_section.set("innerHTML", response.responseText);
            var anim = Y.lazr.anim.green_flash({
                node: size_section
                });
            anim.run();
        }
    };

    /*
     * Initialization of the repository size section update.
     */
    function dispatchUpdate () {
        _updates = 0;
        var size_section = Y.get('#package_counters');
	var notice = Y.Node.create(
	    "<p style=\"line-height: 3em;\">" +
            "<img src=\"/@@/spinner\" style=\"padding-right: 5px;\"/>" +
            "Updating archive size information ...</p>");
	size_section.replaceChild(notice, size_section.query('p'));
        size_section.plug(LP.DynamicDomUpdater,
                          repository_size_dynamic_update_config);
    };

    Y.on("domready", dispatchUpdate);

}, '0.1', {requires:['node', 'lazr.anim', 'anim', 'soyuz.dynamic_dom_updater']});
