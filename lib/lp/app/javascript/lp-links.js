/**
 * Launchpad utilities for manipulating links.
 *
 * @module app
 * @submodule links
 */
YUI.add('lp.app.links', function(Y) {

    var links = Y.namespace('lp.app.links');

    links.check_branch_links = function() {

        var link_info = new Array();
        Y.all('.branch-short-link').each(function(link) {
            var href = link.getAttribute('href');
            if( link_info.indexOf(href)<0 ) {
                link_info.push(href);
            }
        });
        var json_link_info = Y.JSON.stringify(link_info);

        var qs = '';
        qs = LP.client.append_qs(qs, 'link_hrefs', json_link_info);
        CHECK_LINKS='+check-links?';
        Y.io(CHECK_LINKS+qs, {
            headers: {'Accept': 'application/json'},
            on: {
                success: function(id, response) {
                    var response_info = Y.JSON.parse(response.responseText)
                    var invalid_links = Y.Array(response_info.invalid_links)
                    Y.all('.branch-short-link').each(function(link) {
                        var href = link.getAttribute('href');
                        if( invalid_links.indexOf(href)>=0 ) {
                            link.removeClass('branch-short-link');
                            link.addClass('invalid-link');
                            link.on('click', function(e) {
                                e.halt();
                                alert('Invalid link: ' + href);
                            });
                        }
                    });
                }
            }
        });
    };

}, "0.1", {"requires": [
    "base", "node", "io", "dom", "json"
    ]});

