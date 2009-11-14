/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code for handling the popup diffs in the pretty overlays.
 *
 * @module popupdiff
 * @requires node
 */

YUI.add('code.popupdiff', function(Y) {

// The launchpad js client used.
var lp_client;

Y.popupdiff = Y.namespace('code.popupdiff');


var DiffOverlay = function() {
    DiffOverlay.superclass.constructor.apply(this, arguments);
};


Y.extend(DiffOverlay, Y.lazr.PrettyOverlay, {
        bindUI: function() {
            // call PrettyOverlay's bindUI
            this.constructor.superclass.bindUI.call(this);
        }
    });


DiffOverlay.NAME = 'diff-overlay';


var rendered_overlays = {};


function load_diff(node, api_url, librarian_url) {

    // Look to see if we have rendered one already.
    if (rendered_overlays[api_url] !== undefined) {
        rendered_overlays[api_url].show();
        return;
    }

    // Show a spinner.
    var html = [
        '<img src="/@@/spinner" alt="loading..." ',
        '     style="padding-left: 0.5em"/>'].join('');
    var spinner = Y.Node.create(html);
    node.appendChild(spinner);

    var config = {
        on: {
            success: function(formatted_diff) {
                node.removeChild(spinner);
                var diff_overlay = show_diff(formatted_diff);
                rendered_overlays[api_url] = diff_overlay;
            },
            failure: function() {
                node.removeChild(spinner);
                // Fail over to loading the librarian link.
                document.location = librarian_url;
            }
        },
        accept: LP.client.XHTML
    };
    lp_client.get(api_url, config);
}

function show_diff(diff_text) {

    var diff_overlay = new DiffOverlay({
            bodyContent: diff_text,
            align: {
                points: [Y.WidgetPositionExt.CC, Y.WidgetPositionExt.CC]
            },
            progressbar: false
        });
    diff_overlay.render();
    return diff_overlay;
}


/*
 * Connect the diff links to thier pretty overlay function.
 */
Y.popupdiff.connect_diff_links = function() {

    // Setup the LP client.
    lp_client = new LP.client.Launchpad();

    // var status_content = Y.get('#branch-details-status-value');
    var nl = Y.all('.popup-diff');
    nl.each(function(node, index, nodelist){
            var a = node.query('a');
            a.addClass('js-action');
            var librarian_url = a.getAttribute('href');
            var api_url = node.query('a.api-ref').getAttribute('href');
            a.on('click', function(e) {
                    e.preventDefault();
                    load_diff(a, api_url, librarian_url);
                });
        });
};

    }, '0.1', {requires: ['io', 'node', 'lazr.overlay', 'lp.client']});
