/**
 * Launchpad utilities for manipulating links.
 *
 * @module app
 * @submodule links
 */

function harvest_links(Y, links_holder, link_class, link_type) {
    // Get any links of the specified link_class and put store them as the
    // specified link_type in the specified links_holder
    var link_info = new Array();
    Y.all('.'+link_class).each(function(link) {
        var href = link.getAttribute('href');
        if( link_info.indexOf(href)<0 ) {
            link_info.push(href);
        }
    });
    if( link_info.length > 0 ) {
        links_holder[link_type] = link_info;
    }
}

function process_invalid_links(Y, link_info, link_class, link_type, title) {
    // We have a collection of invalid links possibly containing links of
    // type link_type, so we need to remove the existing link_class, replace
    // it with an invalid-link class, and set the link title.
    var invalid_links = Y.Array(link_info['invalid_'+link_type]);

    if( invalid_links.length > 0) {
        Y.all('.'+link_class).each(function(link) {
            var href = link.getAttribute('href');
            if( invalid_links.indexOf(href)>=0 ) {
                var msg = title + href;
                link.removeClass(link_class);
                link.addClass('invalid-link');
                link.title = msg
                link.on('click', function(e) {
                    e.halt();
                    alert(msg);
                });
            }
        });
    }
}

YUI.add('lp.app.links', function(Y) {

    var links = Y.namespace('lp.app.links');

    links.check_valid_lp_links = function() {
        // Grabs any lp: style links on the page and checks that they are
        // valid. Invalid ones have their class changed to "invalid-link".
        // ATM, we only handle +branch links.

        var links_to_check = {}

        // We get all the links with defined css classes.
        // At the moment, we just handle branch links, but in future...
        harvest_links(Y, links_to_check, 'branch-short-link', 'branch_links');

        // Do we have anything to do?
        if( Y.Object.size(links_to_check) == 0 ) {
            return;
        }

        // Get the final json to send
        var json_link_info = Y.JSON.stringify(links_to_check);
        var qs = '';
        qs = LP.client.append_qs(qs, 'link_hrefs', json_link_info);

        var config = {
            on: {
                failure: function(id, response, args) {
                    // If we have firebug installed, log the error.
                    if( console != undefined) {
                        console.log("Link Check Error: " + args + ': '
                                + response.status + ' - ' +
                                response.statusText + ' - '
                                + response.responseXML);
                    }
                },
                success: function(id, response) {
                    var link_info = Y.JSON.parse(response.responseText)
                    // ATM, we just handle branch links, but in future...
                    process_invalid_links(Y, link_info, 'branch-short-link',
                            'branch_links', "Invalid branch: ");
                }
            }
        }
        var uri = '+check-links';
        var on = Y.merge(config.on);
        var client = this;
        var y_config = { method: "POST",
                         headers: {'Accept': 'application/json'},
                         on: on,
                         'arguments': [client, uri],
                         data: qs};
        Y.io(uri, y_config);
    };

}, "0.1", {"requires": [
    "base", "node", "io", "dom", "json"
    ]});

