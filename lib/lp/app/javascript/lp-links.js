/**
 * Launchpad utilities for manipulating links.
 *
 * @module app
 * @submodule links
 */
YUI.add('lp.app.links', function(Y) {

    var links = Y.namespace('lp.app.links');

    links.check_branch_links = function() {
        // We get all the links with defined css classes.
        // At the moment, we just handle branch links, but in future...
        var links_to_check = {};
        // Get any branch links
        var branch_link_info = new Array();
        Y.all('.branch-short-link').each(function(link) {
            var href = link.getAttribute('href');
            if( branch_link_info.indexOf(href)<0 ) {
                branch_link_info.push(href);
            }
        });
        links_to_check['branch_links'] = branch_link_info

        // Get the final json to send
        var json_link_info = Y.JSON.stringify(links_to_check);
        var qs = '';
        qs = LP.client.append_qs(qs, 'link_hrefs', json_link_info);
        CHECK_LINKS='+check-links?';
        Y.io(CHECK_LINKS+qs, {
            headers: {'Accept': 'application/json'},
            on: {
                failure: function(id, response, args) {
//                    alert("error: " + args + ': ' + response.status + ' - ' +
//                            response.statusText + ' - ' + response.responseXML);
                },
                success: function(id, response) {
                    var response_info = Y.JSON.parse(response.responseText)
                    var invalid_branch_links = Y.Array(
                            response_info.invalid_branch_links)

                    if( invalid_branch_links.length > 0) {
                        Y.all('.branch-short-link').each(function(link) {
                            var href = link.getAttribute('href');
                            if( invalid_branch_links.indexOf(href)>=0 ) {
                                var msg = 'Branch ' + href + ' does not exist.';
                                link.removeClass('branch-short-link');
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
            }
        });
    };

}, "0.1", {"requires": [
    "base", "node", "io", "dom", "json"
    ]});

