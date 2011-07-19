# $Id: selftest.py 1758 2004-03-28 17:36:59Z fredrik $
# -*- coding: iso-8859-1 -*-
# elementtidy selftest program (in progress)

from elementtree import ElementTree

def sanity():
    """
    Make sure everything can be imported.

    >>> import _elementtidy
    >>> from elementtidy.TidyHTMLTreeBuilder import *
    """

HTML1 = "<title>Foo</title><ul><li>Foo!<li>åäö"

XML1 = """\
<html:html xmlns:html="http://www.w3.org/1999/xhtml">
<html:head>
<html:meta content="TIDY" name="generator" />
<html:title>Foo</html:title>
</html:head>
<html:body>
<html:ul>
<html:li>Foo!</html:li>
<html:li>&#229;&#228;&#246;</html:li>
</html:ul>
</html:body>
</html:html>"""

def check(a, b):
    import re
    a = ElementTree.tostring(ElementTree.XML(a))
    a = re.sub("HTML Tidy[^\"]+", "TIDY", a)
    a = re.sub("\r\n", "\n", a)
    if a != b:
        print a
        print "Expected:"
        print b

def testdriver():
    """
    Check basic driver interface.

    >>> import _elementtidy
    >>> xml, errors = _elementtidy.fixup(HTML1)
    >>> check(xml, XML1)
    """

def testencoding():
    """
    Check basic driver interface.

    >>> import _elementtidy
    >>> xml, errors = _elementtidy.fixup(HTML1, 'ascii')
    >>> check(xml, XML1)
    >>> xml, errors = _elementtidy.fixup(HTML1, 'latin1')
    >>> check(xml, XML1)
    """

def xmltoolkit35():
    """
    @XMLTOOLKIT35
    elementtidy crashes on really broken pages.

    >>> import _elementtidy
    >>> xml, errors = _elementtidy.fixup("<crash>")
    >>> tree = ElementTree.XML(xml)
    """

def xmltoolkit48():
    """
    @XMLTOOLKIT48
    elementtidy gives up on some pages.

    >>> import _elementtidy
    >>> html = "<table><form><tr><td>test</td></tr></form></table>"
    >>> xml, errors = _elementtidy.fixup(html)
    >>> tree = ElementTree.XML(xml)

    """

if __name__ == "__main__":
    import doctest, selftest
    failed, tested = doctest.testmod(selftest)
    print tested - failed, "tests ok."
