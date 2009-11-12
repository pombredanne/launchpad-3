/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
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

function show_diff(address) {

    // Look to see if we have rendered one already.
    if (rendered_overlays[address] !== undefined) {
        rendered_overlays[address].show()
        return;
    }

    var diff_overlay = new DiffOverlay({
            bodyContent: '<div class="loading">loading... <img src="/@@/spinner"/></div>',
            align: {
                points: [Y.WidgetPositionExt.CC, Y.WidgetPositionExt.CC]
            },
            progressbar: false,
        });
    diff_overlay.render();
    rendered_overlays[address] = diff_overlay;
    // Load the diff.
    var diff_url = address + '/++diff';
    Y.log('load the diff: ' + diff_url);
    Y.io(diff_url, {
            on: {
                success: function(id, response) {
                    Y.log('success loading diff');
                    diff_overlay.get('contentBox').set('innerHTML', response.responseText);
                },
                failure: function(id, response) {
                    Y.log('failed loading diff');
                    //barr
                    diff_overlay.get('contentBox').set('innerHTML', 'failed to load diff.');
                    delete rendered_overlays[address];
                }
            }
        })
}

function get_mp_class(node)
{
    var node_classes = node.getAttribute('class').split(/\s+/);
    for (var i=0; i < node_classes.length; ++i) {
        var class_name = node_classes[i];
        if (class_name.match(/^mp-\d+$/)) {
            return class_name
        }
    }
    // Not found, so return the empty string.
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
    Y.log('connect diff links');
    var nl = Y.all('.popup-diff');
    Y.log(nl.size());
    nl.each(function(node, index, nodelist){
            Y.log(node);
            var a = node.query('a');
            Y.log(a);
            Y.log(a.getAttribute('href'));
            a.addClass('js-action');
            var mp_url = get_mp_url_for_node(node);
            Y.log(mp_url);
            a.on('click', function(e) {
                    e.preventDefault();
                    show_diff(mp_url);
                });
        });

    Y.log(Y.winWidth, Y.winHeight);
};

    }, '0.1', {requires: ['io', 'node', 'lazr.overlay']});
