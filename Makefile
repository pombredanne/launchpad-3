html: bzr-launchpad.html

clean:
	rm -f bzr-launchpad.html
	rm -f *~

%.html: html.xsl %.tmml
	xsltproc $^ > $@

%.png: %.dia
	dia -t png $^

%.ps: %.tmml
	#texmacs -x '(begin (export-buffer "$@") (quit-TeXmacs))' $<
	texmacs -c $< $@ -x '(quit-TeXmacs)'

%.pdf: %.tmml
	texmacs -c $< $@ -x '(quit-TeXmacs)'

%.tmml: %.tm
	texmacs -c $< $@  -x '(quit-TeXmacs))'

.PHONY: html
