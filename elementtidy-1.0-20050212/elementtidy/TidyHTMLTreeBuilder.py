#
# ElementTree
# $Id: TidyHTMLTreeBuilder.py 2276 2005-02-03 19:21:25Z fredrik $
#
# tree builder based on the _elementtidy tidylib wrapper
#
# history:
# 2003-07-06 fl   created
# 2003-09-17 fl   capture stderr as well
# 2005-02-03 fl   added encoding support
#
# Copyright (c) 1999-2005 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2005 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

# note: route all elementtree access via ElementTree, so that external
# users can "patch in" another implementation if they want to (such as
# cElementTree)

# Support for python >= 2.5
try:
  from elementtree import ElementTree
except ImportError:
  from xml.etree import ElementTree

import _elementtidy
import string

##
# ElementTree builder for HTML source code.  This builder converts an
# HTML document or fragment to an XHTML ElementTree, by running it
# through the _elementtidy processor.
#
# @kwparam encoding Optional source document encoding.
#
# @see elementtree.ElementTree

class TidyHTMLTreeBuilder:

    def __init__(self, encoding=None):
        self.__data = []
        if encoding:
            if encoding == "iso-8859-1":
                encoding = "latin1"
            else:
                encoding = string.replace(encoding, "-", "")
        self.__encoding = encoding
        self.errlog = None

    ##
    # Add data to parser buffers.

    def feed(self, text):
        self.__data.append(text)

    ##
    # Flush parser buffers, and return the root element.
    #
    # @return An Element instance.

    def close(self):
        args = [string.join(self.__data, "")]
        if self.__encoding:
            args.append(self.__encoding)
        stdout, stderr = _elementtidy.fixup(*args)
        self.errlog = stderr
        return ElementTree.XML(stdout)

##
# An alias for the <b>TidyHTMLTreeBuilder</b> class.

TreeBuilder = TidyHTMLTreeBuilder

##
# Parse an HTML document into an XHTML-style element tree.
#
# @param source A filename or file object containing HTML data.
# @return An ElementTree instance

def parse(source):
    return ElementTree.parse(source, TreeBuilder())

##
# Parse an HTML document into an XHTML-style element tree, and return
# both the tree and the error log.
#
# @param source A filename or file object containing HTML data.
# @return A 2-tuple containing an ElementTree instance and a string
#     with TidyLib's error log.

def parse2(source):
    builder = TreeBuilder()
    tree = ElementTree.parse(source, builder)
    return tree, builder.errlog

if __name__ == "__main__":
    import sys
    ElementTree.dump(parse(open(sys.argv[1])))
