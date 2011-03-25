/* Copyright 2009 Canonical Ltd.  This software is licensed under the
   GNU Affero General Public License version 3 (see the file LICENSE). */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: true
    }).use(
        'test', 'console', 'node-event-simulate', 'event-simulate', "io-base",
        'lp.soyuz.base', "lazr.anim", "lazr.effects",
        'lp.soyuz.dynamic_dom_updater',
        'lp.registry.distroseriesdifferences_details', function(Y) {

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;
var suite = new Y.Test.Suite("Distroseries differences Tests");
var dsd_details = Y.lp.registry.distroseriesdifferences_details;
var dsd_uri = '/deribuntu/deriwarty/+difference/evolution';
var console = new Y.Console({newestOnTop: false});
console.render('#log');

var get_placeholder_contents = function(existing_state) {
    ret = [
        '<table class="listing">',
        '  <tbody><tr><td>',
        '    <div class="diff-extra-container">',
        '      <input name="field.selected_differences" type="checkbox" />',
        '      <a class="toggle-extra" ',
        '        href="/deribuntu/deriwarty/+difference/evolution">',
        '        evolution</a>',
        '      <span class="package-diff-button"></span>',
        '    <dt class="package-diff-placeholder">',
        '      <a class="js-action sprite add" href="#">',
        '        Compute differences from last common version:',
        '      </a></dt>',
        '    <dd>',
        '    <ul class="package-diff-status">',
        '      <li>',
        '        <span id="derived" class="',
        existing_state,
        '">',
        '          1.2.1 to Derilucid version: 1.2.4',
        '        </span>',
        '      </li>',
        '      <li>',
        '        <span id="parent" class="request-derived-diff">',
        '          1.2.1 to Lucid version: 1.2.3',
        '        </span>',
        '      </li>',
        '    </ul>',
        '    </dd>',
        '    </div>',
        '  </td></tr></tbody>',
        '</table>'].join('');
    return ret;
}

var testPackageDiffUpdate = {

    name: 'package-diff',

    test_vocabulary_helper: function() {
        // The vocabulary helper extracts the selected item from a
        // jsonified vocabulary.
        var voc = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "selected": true, "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        var res = dsd_details.get_selected(voc);
        Assert.areEqual('COMPLETED', res.token);
        Assert.areEqual('Completed', res.title);
        var voc_nothing_selected = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        Assert.isUndefined(dsd_details.get_selected(voc_nothing_selected));
    },
};


var testPackageDiffUpdateInteraction = {

    name: 'package-diff-update-interaction',

    setUp: function() {
       var first_poll = true;
        pending_voc = [
            {"token": "PENDING", "selected": true, "title": "Pending"},
            {"token": "COMPLETED", "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        completed_voc = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "selected": true, "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];

        // Monkey patch request.
        var lp_prot = Y.lp.client.Launchpad.prototype;
        lp_prot.named_post = function(url, func, config) {
            config.on.success();};
        lp_prot.named_get = function(url, func, config) {
            config.on.success();};
        lp_prot.get = function(uri, config) {
            if (first_poll === true) {
                first_poll = false;
                Y.log('pending...');
                config.on.success(pending_voc);
            }
            else {
                Y.log('comple...');
                config.on.success(completed_voc);
            }
        };

        dsd_details.poll_interval = 2000;

   },

    test_request_package_diff_computation: function() {
        // A click on the button changes the package diff status and requests
        // the package diffs computation via post.
        var placeholder = Y.one('#placeholder');
        placeholder.set('innerHTML', get_placeholder_contents('FAILED'));
        dsd_details.setup_packages_diff_states(
            Y.one('.diff-extra-container'), dsd_uri);
        var func_req = undefined;
        var lp_prot = Y.lp.client.Launchpad.prototype;
        lp_prot.named_post = function(url, func, config) {
            func_req = func;
            config.on.success();
        };

        var button = Y.one('.package-diff-placeholder');

        Y.Event.simulate(Y.Node.getDOMNode(button), 'click');
        var package_diff = Y.one('#parent');

        Assert.isTrue(package_diff.hasClass('PENDING'));
        Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        Assert.areEqual('requestPackageDiffs', func_req);
        Assert.isNotUndefined(package_diff.updater);

        // Let the polling happen.
        this.wait(function() {
            Y.log('check pending');
            Assert.isTrue(package_diff.hasClass('PENDING'));
                this.wait(function() {
                    Y.log('check comple');
                    Assert.isTrue(package_diff.hasClass('COMPLETED'));
                }, 2500);
         }, 2500);
    },

    test_polling_for_pending_items: function() {
        // The polling has started on the pending package diff. The
        // status is being updated.
        var placeholder = Y.one('#placeholder');
        placeholder.set('innerHTML', get_placeholder_contents('PENDING'));
        dsd_details.setup_packages_diff_states(
            Y.one('.diff-extra-container'), dsd_uri);
        var package_diff = Y.one('#derived');
        Assert.isTrue(package_diff.hasClass('PENDING'));
        Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        this.wait(function() {
            Assert.isTrue(package_diff.hasClass('PENDING'));
                this.wait(function() {
                    Assert.isTrue(package_diff.hasClass('COMPLETED'));
                }, 2500);
         }, 2500);
   }
};

suite.add(new Y.Test.Case(testPackageDiffUpdate));

suite.add(new Y.Test.Case(testPackageDiffUpdateInteraction));

Y.Test.Runner.add(suite);

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});

