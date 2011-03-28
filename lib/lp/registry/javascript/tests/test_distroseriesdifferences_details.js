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

var placeholder_content = Y.one('#placeholder_base').get('innerHTML');

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
        placeholder.set('innerHTML', placeholder_content);
        placeholder
            .one('#derived')
                .removeClass('PENDING')
                    .addClass('FAILED');
        dsd_details.setup_packages_diff_states(
            placeholder.one('.diff-extra-container'), dsd_uri);
        var func_req = undefined;
        var lp_prot = Y.lp.client.Launchpad.prototype;
        lp_prot.named_post = function(url, func, config) {
            func_req = func;
            config.on.success();
        };

        var button = Y.one('.package-diff-placeholder');

        button.simulate('click');
        var package_diff = Y.one('#parent');

        Assert.isTrue(package_diff.hasClass('PENDING'));
        Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        Assert.areEqual('requestPackageDiffs', func_req);
        Assert.isNotUndefined(package_diff.updater);

        // Let the polling happen.
        this.wait(function() {
            Assert.isTrue(package_diff.hasClass('PENDING'));
                this.wait(function() {
                    Assert.isTrue(package_diff.hasClass('COMPLETED'));
                }, 2500);
         }, 2500);
    },

    test_polling_for_pending_items: function() {
        // The polling has started on the pending package diff. The
        // status is being updated.
        var placeholder = Y.one('#placeholder');
        placeholder.set('innerHTML', placeholder_content);
        dsd_details.setup_packages_diff_states(
            placeholder.one('.diff-extra-container'), dsd_uri);
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

