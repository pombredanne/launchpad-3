html: bzr-launchpad.html

bzr-launchpad.html: html.xsl bzr-launchpad.tmml
	xsltproc $^ > $@

.PHONY: html
