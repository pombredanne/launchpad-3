YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: true
    }).use('test', 'console', 'lp.translations.sourcepackage_sharing_details', function(Y) {
    var suite = new Y.Test.Suite("sourcepackage_sharing_details Tests");
    var TranslationSharingConfig = (
      Y.lp.translations.sourcepackage_sharing_details.TranslationSharingConfig)
    var TranslationSharingController = (
      Y.lp.translations.sourcepackage_sharing_details.TranslationSharingController)
    var CheckItem = (
      Y.lp.translations.sourcepackage_sharing_details.CheckItem)
    var LinkCheckItem = (
      Y.lp.translations.sourcepackage_sharing_details.LinkCheckItem)

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'setup',

        test_translation_usage_enabled: function() {
            var sharing_config = new TranslationSharingConfig();
            var usage = sharing_config.get('translation_usage')
            Y.Assert.isFalse(usage.get('enabled'));
            sharing_config.get('product_series').set_link('ps', 'http://')
            Y.Assert.isTrue(usage.get('enabled'));
        },
        test_branch: function() {
            var sharing_config = new TranslationSharingConfig();
            var product_series = sharing_config.get('product_series')
            Y.Assert.isFalse(product_series.get('complete'));
            Y.Assert.isFalse(sharing_config.get('branch').get('enabled'));
            product_series.set_link('ps', 'http://')
            Y.Assert.isTrue(sharing_config.get('branch').get('enabled'));
        },
        test_autoimport: function() {
            var sharing_config = new TranslationSharingConfig();
            Y.Assert.isFalse(sharing_config.get('autoimport').get('enabled'));
            sharing_config.get('branch').set_link('br', 'http://foo')
            Y.Assert.isTrue(sharing_config.get('autoimport').get('enabled'));
        },
        test_LinkCheckItem_contents: function() {
            lci = new LinkCheckItem()
            Y.Assert.isNull(lci.get('text'));
            Y.Assert.isNull(lci.get('url'));
            lci.set_link('mytext', 'http://example.com');
            Y.Assert.areEqual('mytext', lci.get('text'));
            Y.Assert.areEqual('http://example.com', lci.get('url'));
        },
        test_LinkCheckItem_complete: function() {
            lci = new LinkCheckItem()
            Y.Assert.isFalse(lci.get('complete'));
            lci.set_link('text', 'http://example.com');
            Y.Assert.isTrue(lci.get('complete'));
        },
        test_CheckItem_enabled: function() {
            ci = new CheckItem();
            Y.Assert.isTrue(ci.get('enabled'));
        },
        test_CheckItem_enabled_dependency: function(){
            lci = new LinkCheckItem()
            ci = new CheckItem({dependency: lci})
            Y.Assert.isFalse(ci.get('enabled'))
            lci.set_link('text', 'http://example.com');
            Y.Assert.isTrue(ci.get('enabled'))
        },
        test_CheckItem_identifier: function(){
            ci = new CheckItem({identifier: 'id1'});
            Y.Assert.areEqual('id1', ci.get('identifier'))
        },
        test_update_branch: function(){
            complete = Y.one('#branch .complete')
            incomplete = Y.one('#branch .incomplete')
            link = Y.one('#branch .complete a')
            Y.Assert.areEqual('', link.get('text'))
            Y.Assert.areNotEqual('http:///', link.get('href'))
            Y.Assert.isFalse(complete.hasClass('unseen'))
            Y.Assert.isFalse(incomplete.hasClass('unseen'))
            ctrl = new TranslationSharingController({})
            ctrl.update()
            Y.Assert.isTrue(complete.hasClass('unseen'))
            Y.Assert.isFalse(incomplete.hasClass('unseen'))
            ctrl.get('tsconfig').get('branch').set_link('a', 'http:///')
            ctrl.update()
            Y.Assert.isFalse(complete.hasClass('unseen'))
            Y.Assert.isTrue(incomplete.hasClass('unseen'))
            link = Y.one('#branch .complete a')
            Y.Assert.areEqual('a', link.get('text'))
            Y.Assert.areEqual('http:///', link.get('href'))
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
