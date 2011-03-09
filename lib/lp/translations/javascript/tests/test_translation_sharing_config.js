YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: true
    }).use('test', 'console', 'lp.translations.translation_sharing_config', function(Y) {
    var suite = new Y.Test.Suite("translations_sharing_config Tests");
    var TranslationSharingConfig = (
      Y.lp.translations.translation_sharing_config.TranslationSharingConfig)

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'setup',

        test_branch_enabled: function() {
            var sharing_config = new TranslationSharingConfig();
            Y.Assert.isNull(sharing_config.get('product_series'));
            Y.Assert.isFalse(sharing_config.get('branch_enabled'));
            sharing_config.set('product_series', 'http://foo')
            Y.Assert.isTrue(sharing_config.get('branch_enabled'));
            },
        }));

    // Lock, stock, and two smoking barrels.
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});
