YUI().use('lp.testing.runner', 'lp.testing.mockio', 'test', 'console', 
          'lp.client', 'node-event-simulate', 'lp.bugs.bugtask.taglist', 
    function(Y) {

    var module = Y.lp.bugs.bugtask.taglist;
    var suite = new Y.Test.Suite("Bug tags portlet Tests");

    suite.add(new Y.Test.Case({
        name: 'Tags list',

        tearDown: function() {
                Y.one('.portletBody').remove();
                Y.one('#show-more-tags-link').addClass('hidden');
                Y.one('#show-less-tags-link').addClass('hidden');
            },
        
        test_io_url: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.setup_taglist({io_provider: mockio});
            mockio.success({
                responseText: '<div class="portletBody"><div class="section">'+
                              '<h2>Tags</h2><ul class="tag-list">'+
                              '</ul></div></div>',
                responseHeaders: {'Content-type': 'text/html'}});
            Y.Assert.areEqual('/launchpad/+bugtarget-portlet-tags-content',
                              mockio.last_request.url,
                              'The url should have been set');
            },
        
        test_no_tags: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.setup_taglist({io_provider: mockio});
            mockio.success({
                responseText: '<div class="portletBody"><div class="section">'+
                              '<h2>Tags</h2><ul class="tag-list">'+
                              '</ul></div></div>',
                responseHeaders: {'Content-type': 'text/html'}});
            var tags = Y.all('.tag-list li');
            var show_more_link = Y.one('#show-more-tags-link');
            var show_less_link = Y.one('#show-less-tags-link');
            Y.Assert.areEqual(0, tags.size(), 'The list should be empty');
            Y.Assert.isTrue(show_more_link.hasClass('hidden'),
                'The show more link should be hidden');
            Y.Assert.isTrue(show_less_link.hasClass('hidden'),
                'The show less link should be hidden');
            },
        
        test_twenty_tags_or_less: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.setup_taglist({io_provider: mockio});
            var response = '<div class="portletBody"><div class="section">'+
                              '<h2>Tags</h2><ul class="tag-list">';
            for (var i=0; i<=5; i++) {
                response += '<li><span class="tag-count">'+i+'</span>'+
                        '<a href="+bugs?field.tag=crash">tag'+i+'</a></li>';
            }
            response += '</ul></div></div>';
            mockio.success({
                responseText: response,
                responseHeaders: {'Content-type': 'text/html'}});
            var tags = Y.all('.tag-list li');
            var show_more_link = Y.one('#show-more-tags-link');
            var show_less_link = Y.one('#show-less-tags-link');
            Y.assert(tags.size() <= 20,
                'The list should have twenty tags or less');
            Y.Assert.isTrue(show_more_link.hasClass('hidden'),
                'The show more link should be hidden');
            Y.Assert.isTrue(show_less_link.hasClass('hidden'),
                'The show less link should be hidden');
            },

        test_more_than_twenty_tags: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.setup_taglist({io_provider: mockio});
            var response = '<div class="portletBody"><div class="section">'+
                              '<h2>Tags</h2><ul class="tag-list">';
            for (var i=0; i<=22; i++) {
                response += '<li><span class="tag-count">'+i+'</span>'+
                        '<a href="+bugs?field.tag=crash">tag'+i+'</a></li>';
            }
            response += '</ul></div></div>';
            mockio.success({
                responseText: response,
                responseHeaders: {'Content-type': 'text/html'}});
            var tags = Y.all('.tag-list li');
            var show_more_link = Y.one('#show-more-tags-link');
            var show_less_link = Y.one('#show-less-tags-link');
            var tag_count = tags.size()
            Y.assert(tag_count > 20,
                'The list should have more than twenty tags');
            Y.Assert.areEqual(20, tag_count - tags.filter('.hidden').size(),
                'Only twenty tags should be visible');
            Y.Assert.isTrue(show_less_link.hasClass('hidden'),
                'The show less link should be hidden');
            Y.Assert.isFalse(show_more_link.hasClass('hidden'),
                'The show less link should be visible');
            show_more_link.simulate('click');
            Y.Assert.areEqual(0, tags.filter('.hidden').size(),
                'All the tags should now be visible');
            Y.Assert.isTrue(show_more_link.hasClass('hidden'),
                'The show more link should now be hidden');
            Y.Assert.isFalse(show_less_link.hasClass('hidden'),
                'The show less link should now be visible');
            show_less_link.simulate('click');
            Y.Assert.areEqual(20, tag_count - tags.filter('.hidden').size(),
                'Only twenty tags should now be visible');
            Y.Assert.isTrue(show_less_link.hasClass('hidden'),
                'The show less link should now be hidden');
            Y.Assert.isFalse(show_more_link.hasClass('hidden'),
                'The show more link should now be visible');
            },
        }));

    Y.lp.testing.Runner.run(suite);
});
