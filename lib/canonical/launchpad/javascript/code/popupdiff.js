/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code for handling the popup diffs in the pretty overlays.
 *
 * @module popupdiff
 * @requires node
 */

YUI.add('code.popupdiff', function(Y) {


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


function load_diff(node, address, librarian_url) {

    // Look to see if we have rendered one already.
    if (rendered_overlays[address] !== undefined) {
        rendered_overlays[address].show();
        return;
    }

    // Show a spinner.
    var html = [
        '<img src="/@@/spinner" alt="loading..." ',
        '     style="padding-left: 0.5em"/>'].join('');
    var spinner = Y.Node.create(html);
    node.appendChild(spinner);
    // Load the diff.
    var diff_url = address + '/++diff';
    Y.io(diff_url, {
            on: {
                success: function(id, response) {
                    node.removeChild(spinner);
                    show_diff(address, response.responseText);
                },
                failure: function(id, response) {
                    node.removeChild(spinner);
                    // Fail over to loading the librarian link.
                    document.location = librarian_url;
                }
            }
        });
}

function show_diff(address, diff_text) {

    var diff_overlay = new DiffOverlay({
            bodyContent: diff_text,
            align: {
                points: [Y.WidgetPositionExt.CC, Y.WidgetPositionExt.CC]
            },
            progressbar: false
        });
    diff_overlay.render();
    rendered_overlays[address] = diff_overlay;
}


function get_mp_class(node)
{
    // Look for the class name on the node that starts with "mp-" and return
    // it.  If one isn't found, the empty string is returned.
    var mp_regex = /^mp-\d+$/;
    var node_classes = node.getAttribute('class').split(/\s+/);
    for (var i=0; i < node_classes.length; ++i) {
        var class_name = node_classes[i];
        if (class_name.match(mp_regex)) {
            return class_name;
        }
    }
    return '';
}


function get_mp_url_for_node(node)
{
    var mp_class = get_mp_class(node);
    var div = Y.get('div.' + mp_class);
    return div.query('a').getAttribute('href');
}


/*
 * Connect the diff links to thier pretty overlay function.
 */
Y.popupdiff.connect_diff_links = function() {

    // var status_content = Y.get('#branch-details-status-value');
    var nl = Y.all('.popup-diff');
    nl.each(function(node, index, nodelist){
            var a = node.query('a');
            a.addClass('js-action');
            var librarian_url = a.getAttribute('href');
            var mp_url = get_mp_url_for_node(node);
            a.on('click', function(e) {
                    e.preventDefault();
                    load_diff(a, mp_url, librarian_url);
                });
        });
};

    }, '0.1', {requires: ['io', 'node', 'lazr.overlay']});
