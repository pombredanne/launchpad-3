YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: true
    }).use('test', 'console', 'lp.translations.translation_sharing_config', function(Y) {
    var suite = new Y.Test.Suite("translations_sharing_config Tests");
    var TranslationSharingConfig = (
      Y.lp.translations.translation_sharing_config.TranslationSharingConfig)
    var CheckItem = (
      Y.lp.translations.translation_sharing_config.CheckItem)
    var LinkCheckItem = (
      Y.lp.translations.translation_sharing_config.LinkCheckItem)

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
