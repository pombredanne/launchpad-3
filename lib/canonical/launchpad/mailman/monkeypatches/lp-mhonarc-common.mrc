<!-- Launchpad customizations common to all our MHonArc-generated
     mailing list archives.

     See http://www.mhonarc.org/MHonArc/doc/mhonarc.html and
     http://www.mhonarc.org/MHonArc/doc/faq/, they are your friends.

     http://www.mhonarc.org/MHonArc/doc/resources.html#index is
     especially your friend, when all others have abandoned you.  -->

<!-- Basic parameters. -->
<MAIN>
<THREAD>
<SORT>
<REVERSE>
<TREVERSE>
<NODOC>

<!-- Use multi-page indexes.
     See http://www.mhonarc.org/MHonArc/doc/resources/multipg.html -->
<MULTIPG>
<IDXSIZE>
200
</IDXSIZE>

<!-- Define a custom resource variable to represent this mailing list.
     This depends on $ML-NAME$ having been set already, presumably on
     the command line via '-definevar'.  See 
     http://www.mhonarc.org/MHonArc/doc/resources/definevar.html. -->
<DefineVar>
ML-FULL-TITLE
<a href="https://launchpad.net/~$ML-NAME$">$ML-NAME$</a> mailing list archive
</DefineVar>

<IDXLABEL>
Date Index
</IDXLABEL>

<TIDXLABEL>
Thread Index
</TIDXLABEL>

<!-- What do the next/prev links look like? -->
<PREVPGLINK>
<a href="$PG(FIRST)$">&larr;First</a>&nbsp;&nbsp;&nbsp;<a href="$PG(PREV)$">&larr;Prev</a>
</PREVPGLINK>
<PREVPGLINKIA>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
</PREVPGLINKIA>
<TPREVPGLINK>
<a href="$PG(TFIRST)$">&larr;First</a>&nbsp;&nbsp;&nbsp;<a href="$PG(TPREV)$">&larr;Prev</a>
</TPREVPGLINK>
<TPREVPGLINKIA>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
</TPREVPGLINKIA>
<NEXTPGLINK>
<a href="$PG(NEXT)$">Next&rarr;</a>&nbsp;&nbsp;&nbsp;<a href="$PG(LAST)$">Last&rarr;</a>
</NEXTPGLINK>
<NEXTPGLINKIA>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
</NEXTPGLINKIA>
<TNEXTPGLINK>
<a href="$PG(TNEXT)$">Next&rarr;</a>&nbsp;&nbsp;&nbsp;<a href="$PG(TLAST)$">Last&rarr;</a>
</TNEXTPGLINK>
<TNEXTPGLINKIA>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
</TNEXTPGLINKIA>

<!-- Formatting for the start of list page.
     See http://www.mhonarc.org/MHonArc/doc/resources/listbegin.html. -->
<LISTBEGIN>
<p>(<a href="$TIDXFNAME$">go to $TIDXLABEL$</a>)</p>
<hr/>
<div style="text-align: left;">$PGLINK(PREV)$&nbsp;&nbsp;&nbsp;$PGLINK(NEXT)$</div>
<div style="text-align: center;">$PGLINKLIST(5;5)$</div>
<ul>
</LISTBEGIN>

<LISTEND>
</ul>
<div style="text-align: center;">$PGLINKLIST(5;5)$</div>
<div style="text-align: left;">$PGLINK(PREV)$&nbsp;&nbsp;&nbsp;$PGLINK(NEXT)$</div>
</LISTEND>

<!-- Formatting for the start of thread page.
     See http://www.mhonarc.org/MHonArc/doc/resources/thead.html. -->
<THEAD>
<p>(<a href="$IDXFNAME$">go to $IDXLABEL$</a>)</p>
<hr/>
<div style="text-align: left;">$PGLINK(TPREV)$&nbsp;&nbsp;&nbsp;$PGLINK(TNEXT)$</div>
<div style="text-align: center;">$PGLINKLIST(T5;T5)$</div>
<ul>
</THEAD>

<TFOOT>
</ul>
<div style="text-align: center;">$PGLINKLIST(T5;T5)$</div>
<div style="text-align: left;">$PGLINK(TPREV)$&nbsp;&nbsp;&nbsp;$PGLINK(TNEXT)$</div>
</TFOOT>

<!-- Per-message formatting on the indexed-by-date main page. -->
<LITEMPLATE>
<li><strong>$SUBJECT$</strong>
<ul><li><em>From</em>: $FROM$,&nbsp;<em>$YYYYMMDD$</em></li></ul>
</li>
</LITEMPLATE>

<!-- Per-message formatting on the thread page. -->
<TTOPBEGIN>
<li><strong>$SUBJECT$</strong>,
<em><b>$FROMNAME$</b>, $YYYYMMDD$</em>
</TTOPBEGIN>
<TLITXT>
<li><strong>$SUBJECT$</strong>,
<em><b>$FROMNAME$</b>, $YYYYMMDD$</em>
</TLITXT>
<TSINGLETXT>
<li><strong>$SUBJECT$</strong>,
<em><b>$FROMNAME$</b>, $YYYYMMDD$</em>
</TSINGLETXT>

<!-- Modify appropriate resources to print our link at the bottom
     of MHonArc generated pages. Notice how the custom resource
     variable defined above can be used to include our link. -->

<!-- Main index pages -->
<IDXPGBEGIN>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>$ML-NAME$ mailing list (by date)</title>
</head>
<body text="#000000" bgcolor="#FFFFFF">
<p><a href="https://launchpad.net/"><img border="0" src="https://launchpad.net/@@/launchpad-logo-and-name.png" alt="Launchpad logo and name."/></a></p>
<h1><center>$ML-FULL-TITLE$ (by date)</center></h1>
</IDXPGBEGIN>

<IDXPGEND>
<hr/>
<p><strong>This is the $ML-FULL-TITLE$&mdash;&nbsp;see also the
general <a href="https://help.launchpad.net/Teams/MailingLists"
>help for Launchpad.net mailing lists</a>.</strong></p>
<p><em>(Formatted by <a href="$DOCURL$">MHonArc</a>.)</em></p>
</body>
</html>
</IDXPGEND>

<!-- Thread index pages -->
<TIDXPGBEGIN>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>$ML-NAME$ mailing list (by thread)</title>
</head>
<body text="#000000" bgcolor="#FFFFFF">
<p><a href="https://launchpad.net/"><img border="0" src="https://launchpad.net/@@/launchpad-logo-and-name.png" alt="Launchpad logo and name."/></a></p>
<h1><center>$ML-FULL-TITLE$ (by thread)</center></h1>
</TIDXPGBEGIN>

<TIDXPGEND>
<hr/>
<p><strong>This is the $ML-FULL-TITLE$&mdash;&nbsp;see also the
general <a href="https://help.launchpad.net/Teams/MailingLists"
>help for Launchpad.net mailing lists</a>.</strong></p>
<p><em>(Formatted by <a href="$DOCURL$">MHonArc</a>.)</em></p>
</body>
</html>
</TIDXPGEND>

<!-- Message pages -->
<MSGPGBEGIN>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>$SUBJECTNA$</title>
<link rev="made" href="mailto:$FROMADDR$">
</head>
<body text="#000000" bgcolor="#FFFFFF">
<p><a href="https://launchpad.net/"><img border="0" src="https://launchpad.net/@@/launchpad-logo-and-name.png" alt="Launchpad logo and name."/></a></p>
</MSGPGBEGIN>

<MSGPGEND>
<hr/>
<p><strong>This is the $ML-FULL-TITLE$&mdash;&nbsp;see also the
general <a href="https://help.launchpad.net/Teams/MailingLists"
>help for Launchpad.net mailing lists</a>.</strong></p>
<p><em>(Formatted by <a href="$DOCURL$">MHonArc</a>.)</em></p>
</body>
</html>
</MSGPGEND>
