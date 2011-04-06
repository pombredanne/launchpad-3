/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: false
    }).use('test', 'console', 'lp.translations.sourcepackage_sharing_details',
    function(Y) {
    var suite = new Y.Test.Suite("sourcepackage_sharing_details Tests");
    var namespace = Y.lp.translations.sourcepackage_sharing_details;
    var TranslationSharingConfig = namespace.TranslationSharingConfig;
    var TranslationSharingController = namespace.TranslationSharingController;
    var CheckItem = (
      Y.lp.translations.sourcepackage_sharing_details.CheckItem);
    var LinkCheckItem = (
      Y.lp.translations.sourcepackage_sharing_details.LinkCheckItem);
    var test_ns = Y.lp.translations.sourcepackage_sharing_details;

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'setup',

        test_translations_usage_enabled: function() {
            var sharing_config = new TranslationSharingConfig();
            var usage = sharing_config.get('translations_usage');
            Y.Assert.isFalse(usage.get('enabled'));
            sharing_config.get('product_series').set_link('ps', 'http://');
            Y.Assert.isTrue(usage.get('enabled'));
        },
        test_branch: function() {
            var sharing_config = new TranslationSharingConfig();
            var product_series = sharing_config.get('product_series');
            Y.Assert.isFalse(product_series.get('complete'));
            Y.Assert.isFalse(sharing_config.get('branch').get('enabled'));
            product_series.set_link('ps', 'http://');
            Y.Assert.isTrue(sharing_config.get('branch').get('enabled'));
        },
        test_autoimport: function() {
            var sharing_config = new TranslationSharingConfig();
            Y.Assert.isFalse(sharing_config.get('autoimport').get('enabled'));
            sharing_config.get('branch').set_link('br', 'http://foo');
            Y.Assert.isTrue(sharing_config.get('autoimport').get('enabled'));
        },
        test_LinkCheckItem_contents: function() {
            var lci = new LinkCheckItem();
            Y.Assert.isNull(lci.get('text'));
            Y.Assert.isNull(lci.get('url'));
            lci.set_link('mytext', 'http://example.com');
            Y.Assert.areEqual('mytext', lci.get('text'));
            Y.Assert.areEqual('http://example.com', lci.get('url'));
        },
        test_LinkCheckItem_complete: function() {
            var lci = new LinkCheckItem();
            Y.Assert.isFalse(lci.get('complete'));
            lci.set_link('text', 'http://example.com');
            Y.Assert.isTrue(lci.get('complete'));
        },
        test_CheckItem_enabled: function() {
            var ci = new CheckItem();
            Y.Assert.isTrue(ci.get('enabled'));
        },
        test_CheckItem_enabled_dependency: function(){
            var lci = new LinkCheckItem();
            var ci = new CheckItem({dependency: lci});
            Y.Assert.isFalse(ci.get('enabled'));
            lci.set_link('text', 'http://example.com');
            Y.Assert.isTrue(ci.get('enabled'));
        },
        test_CheckItem_identifier: function(){
            var ci = new CheckItem({identifier: 'id1'});
            Y.Assert.areEqual('id1', ci.get('identifier'));
        },
        test_configure_empty: function(){
            var ctrl = new TranslationSharingController({});
            var cache = {
                productseries: null,
                upstream_branch: null
            };
            ctrl.configure(cache);
        },
        test_configure: function(){
            var cache = {
                product: {
                    translations_usage: test_ns.usage.launchpad,
                    resource_type_link: 'http://product'
                },
                productseries: {
                    title: 'title1',
                    web_link: 'http://web1',
                    translations_autoimport_mode: (
                        test_ns.autoimport_modes.import_translations),
                    resource_type_link: 'productseries'
                },
                upstream_branch: {
                    unique_name: 'title2',
                    web_link: 'http://web2',
                    resource_type_link: 'branch'
                }
            };
            var ctrl = new TranslationSharingController({});
            var lp_client = new Y.lp.client.Launchpad();
            cache = test_ns.convert_cache(lp_client, cache);
            ctrl.configure(cache);
            var tsconfig = ctrl.get('tsconfig');
            Y.Assert.areEqual(
                tsconfig.get('product_series').get('text'), 'title1');
            Y.Assert.areEqual(
                tsconfig.get('product_series').get('url'), 'http://web1');
            Y.Assert.areEqual(
                tsconfig.get('branch').get('text'), 'title2');
            Y.Assert.isTrue(tsconfig.get('autoimport').get('complete'));
            Y.Assert.isTrue(
                tsconfig.get('translations_usage').get('complete'));
        },
        test_convert_cache: function(){
            var cache = {
                foo: {
                    self_link: 'http://foo',
                    resource_type_link: 'http://foo_type'
                },
                bar: null
            };
            var lp_client = new Y.lp.client.Launchpad();
            cache = test_ns.convert_cache(lp_client, cache);
            Y.Assert.isNull(cache.bar);
            Y.Assert.areEqual('http://foo', cache.foo.get('self_link'));
        },
        test_update_branch: function(){
            var complete = Y.one('#branch-complete');
            var incomplete = Y.one('#branch-incomplete');
            var link = Y.one('#branch-complete a');
            Y.Assert.areEqual('', link.get('text'));
            Y.Assert.areNotEqual('http:///', link.get('href'));
            Y.Assert.isFalse(complete.hasClass('unseen'));
            Y.Assert.isFalse(incomplete.hasClass('unseen'));
            var ctrl = new TranslationSharingController({});
            ctrl.update();
            Y.Assert.isTrue(complete.hasClass('unseen'));
            Y.Assert.isFalse(incomplete.hasClass('unseen'));
            ctrl.get('tsconfig').get('branch').set_link('a', 'http:///');
            ctrl.update();
            Y.Assert.isFalse(complete.hasClass('unseen'));
            Y.Assert.isTrue(incomplete.hasClass('unseen'));
            link = Y.one('#branch-complete a');
            Y.Assert.areEqual('a', link.get('text'));
            Y.Assert.areEqual('http:///', link.get('href'));
        },
        test_update_check_disabled: function(){
            var incomplete = Y.one('#branch-incomplete');
            var ctrl = new TranslationSharingController({});
            var branch = ctrl.get('tsconfig').get('branch');
            ctrl.update_check(branch);
            Y.Assert.isTrue(incomplete.hasClass('lowlight'));
            var product_series = ctrl.get('tsconfig').get('product_series');
            product_series.set_link('a', 'http://');
            ctrl.update_check(branch);
            Y.Assert.isFalse(incomplete.hasClass('lowlight'));
        },
        test_set_autoimport_mode: function(){
            var ctrl = new TranslationSharingController({});
            var check = ctrl.get('tsconfig').get('autoimport');
            Y.Assert.isFalse(check.get('complete'));
            ctrl.set_autoimport_mode('Import template and translation files');
            Y.Assert.isTrue(check.get('complete'));
            ctrl.set_autoimport_mode('Import template files');
            Y.Assert.isFalse(check.get('complete'));
        },
        test_set_translations_usage: function(){
            var ctrl = new TranslationSharingController({});
            var check = ctrl.get('tsconfig').get('translations_usage');
            ctrl.set_translations_usage('Unknown');
            Y.Assert.isFalse(check.get('complete'));
            ctrl.set_translations_usage('Launchpad');
            Y.Assert.isTrue(check.get('complete'));
            ctrl.set_translations_usage('Not Applicable');
            Y.Assert.isFalse(check.get('complete'));
            ctrl.set_translations_usage('External');
            Y.Assert.isTrue(check.get('complete'));
        }
    }));

    // Lock, stock, and two smoking barrels.
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});
