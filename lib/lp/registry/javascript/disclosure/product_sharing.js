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
            headerContent: Y.Node.create("<h2></h2>").set('text', header),
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

    var observer_data = [
        {name: 'fred', display_name: 'Fred Bloggs', role: '(Maintainer)',
        permissions: {publicsecurity: 'some', embargoedsecurity: 'all'}},
        {name: 'john', display_name: 'John Smith', role: '',
        permissions: {publicsecurity: 'all', userdata: 'some'}}
    ];
    var sharing_permissions = [
        {value: 'all', name: 'All',
        title: 'share bug and branch subscriptions'},
        {value: 'some', name: 'Some',
        title: 'share bug and branch subscriptions'},
        {value: 'nothing', name: 'Nothing',
        title: 'revoke all bug and branch subscriptions'}
    ];

    var access_policy_types = {
        publicsecurity: 'Public Security',
        embargoedsecurity: 'Embargoed Security',
        userdata: 'User Data'
    };

    var otns = Y.lp.registry.disclosure.observertable;
    var observer_table = new otns.ObserverTableWidget({
        observers: observer_data,
        sharing_permissions: sharing_permissions,
        access_policy_types: access_policy_types
    });
    observer_table.render();
};

namespace.setup_product_sharing = setup_product_sharing;

}, "0.1", { "requires": [
    'node', 'lp.mustache', 'lazr.picker', 'lp.app.picker',
    'lp.mustache', 'lp.registry.disclosure',
    'lp.registry.disclosure.observertable'] });

