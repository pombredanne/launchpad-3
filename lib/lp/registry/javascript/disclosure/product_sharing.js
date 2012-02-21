/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Disclosure infrastructure.
 *
 * @module lp.registry.disclosure
 */

YUI.add('lp.registry.disclosure.sharing', function(Y) {

var namespace = Y.namespace('lp.registry.disclosure.sharing');

var disclosure_picker = null;

var save_sharing_selection = function(result) {
    Y.log(result.access_policy);
    Y.log(result.api_uri);
};

var setup_product_sharing = function(config) {

    if (disclosure_picker === null) {
        var vocab = 'ValidPillarOwner';
        var header = 'Grant access to project artifacts.';
        if (config !== undefined) {
            if (config.header !== undefined) {
                header = config.header;
            }
        } else {
            config = {};
        }
        var new_config = Y.merge(config, {
            align: {
                points: [Y.WidgetPositionAlign.CC,
                         Y.WidgetPositionAlign.CC]
            },
            progressbar: true,
            progress: 50,
            headerContent: "<h2>" + header + "</h2>",
            zIndex: 1000,
            visible: false,
            save: save_sharing_selection
        });
        disclosure_picker =
            new Y.lp.registry.disclosure.DisclosurePicker(new_config);
        Y.lp.app.picker.setup_vocab_picker(
            disclosure_picker, vocab, new_config);
    }

    var share_link = Y.one('#add-observer-link');
    share_link.on('click', function(e) {
        e.preventDefault();
        disclosure_picker.show();
    });
};

namespace.setup_product_sharing = setup_product_sharing;

}, "0.1", { "requires": [
    'node', 'lp.mustache', 'lazr.picker', 'lp.app.picker',
    'lp.registry.disclosure'] });

