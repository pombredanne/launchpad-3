/* Copyright 2009 Canonical Ltd.  This software is licensed under the
   GNU Affero General Public License version 3 (see the file LICENSE). */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: true
    }).use(
        'test', 'console', 'node-event-simulate', 'event-simulate', "io-base",
        'lp.soyuz.base', "lazr.anim", "lazr.effects", "lp.soyuz.dynamic_dom_updater",
        'lp.registry.distroseriesdifferences_details', function(Y) {

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;
var suite = new Y.Test.Suite("Distroseries differences Tests");
var dsd_details = Y.lp.registry.distroseriesdifferences_details;
var dsd_uri = '/deribuntu/deriwarty/+difference/evolution';
var console = new Y.Console({newestOnTop: false});
console.render('#log');
var placeholder_contents = [
    '<table class="listing">',
    '<tbody><tr><td>',
    '<div class="diff-extra-container">',
    '<input name="field.selected_differences" type="checkbox" />',
    '<a class="toggle-extra" href="/deribuntu/deriwarty/+difference/evolution">evolution</a>',
    '<span class="package-diff-button"></span>',
    '<dt>Differences from last common version:</dt>',
    '<dd>',
    '<ul class="package-diff-status">',
    '<li>',
    '<span id="derived" class="PENDING">',
    'Derilucid version 1.2.4',
    '</span>',
    '</li>',
    '<li>',
    '<span id="parent" class="request-derived-diff">',
    'Lucid version 1.2.3',
    '</span>',
    '</span>',
    '</li>',
    '</ul>',
    '</dd>',
    '</div>',
    '</td></tr></tbody>',
    '</table>'].join('');

var testPackageDiffUpdateSetup = {

    name: 'package-diff-update',

    setUp: function() {
        this.placeholder = Y.one('#placeholder');
        this.placeholder.set('innerHTML', placeholder_contents);

        // Monkey patch request.
        Y.lp.client.Launchpad.prototype.named_post = function(url, func, config) {};
        Y.lp.client.Launchpad.prototype.named_get = function(url, func, config) {};
        Y.lp.client.Launchpad.prototype.get = function(url, func, config) {};

        dsd_details.poll_interval = 1; // 1ms
        dsd_details.setup_packages_diff_states(
            Y.one('.diff-extra-container'), dsd_uri);
    },

    test_button_setup: function() {
        // The button used to trigger the package diff computation has been added.
        Assert.isNotNull(Y.one('.package-diff-button').one('button'));
    },

    test_vocabulary_helper: function() {
        // The vocabulary helper extracts the selected item from a jsonified vocabulary.
        var voc = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "selected": true, "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        Assert.areEqual("COMPLETED", dsd_details.get_selected_state(voc));
        var voc_nothing_selected = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        Assert.isUndefined(dsd_details.get_selected_state(voc_nothing_selected));
    },
};


var testPackageDiffUpdateInteraction = {

    name: 'package-diff-update-interaction',

    setUp: function() {
        this.placeholder = Y.one('#placeholder');
        this.placeholder.set('innerHTML', placeholder_contents);
        voc = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "selected": true, "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];

        // Monkey patch request.
        Y.lp.client.Launchpad.prototype.named_post = function(url, func, config) {
            config.on.success();
        };
        Y.lp.client.Launchpad.prototype.named_get = function(url, func, config) {
            config.on.success();
        };
        Y.lp.client.Launchpad.prototype.get = function(uri, config) {
            config.on.success(voc);
        };

        dsd_details.poll_interval = 1;

        dsd_details.setup_packages_diff_states(Y.one('.diff-extra-container'), dsd_uri);
    },

    test_request_package_diff_computation: function() {
        // A click on the button changes the package diff status and requests
        // the package diffs computation via post.
        var func_req = undefined;

        Y.lp.client.Launchpad.prototype.named_post = function(url, func, config) {
            func_req = func;
            config.on.success();
        };

        var button = Y.one('.package-diff-button').one('button');

        Y.Event.simulate(Y.Node.getDOMNode(button), 'click');
        var package_diff = Y.one('#parent');

        Assert.isTrue(package_diff.hasClass('PENDING'));
        Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        Assert.areEqual('requestPackageDiffs', func_req);
        Assert.isNotUndefined(package_diff.updater);

        // Let the polling happen.
        var check_completed = function() {
            Assert.isTrue(package_diff.hasClass('COMPLETED'));
        };
        Y.later(100, this, check_completed);
     },

    test_polling_for_pending_items: function() {
        // The polling has started on the pending package diff. This
        // status is being updated.
        var package_diff = Y.one('#derived');
        Assert.isTrue(package_diff.hasClass('PENDING'));
        Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        var check_completed = function() {
            Assert.isTrue(package_diff.hasClass('COMPLETED'));
        };
        Y.later(100, this, check_completed);
   }
};

suite.add(new Y.Test.Case(testPackageDiffUpdateSetup));

suite.add(new Y.Test.Case(testPackageDiffUpdateInteraction));

Y.Test.Runner.add(suite);

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});

