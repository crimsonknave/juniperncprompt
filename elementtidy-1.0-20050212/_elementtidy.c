/*
 * ElementTree
 * $Id: _elementtidy.c 2276 2005-02-03 19:21:25Z fredrik $
 *
 * TidyHTMLTreeBuilder driver for the ElementTree package, based
 * on tidylib (from http://tidy.sourceforge.net)
 *
 * Copyright (c) 2003-2005 by Fredrik Lundh.  All rights reserved.
 */

/* --------------------------------------------------------------------
   Copyright (c) 2003-2005 by Fredrik Lundh

   By obtaining, using, and/or copying this software and/or its
   associated documentation, you agree that you have read, understood,
   and will comply with the following terms and conditions:

   Permission to use, copy, modify, and distribute this software and its
   associated documentation for any purpose and without fee is hereby
   granted, provided that the above copyright notice appears in all
   copies, and that both that copyright notice and this permission notice
   appear in supporting documentation, and that the name of Secret Labs
   AB or the author not be used in advertising or publicity pertaining to
   distribution of the software without specific, written prior
   permission.

   SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO
   THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
   FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR
   ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
   WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
   ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
   OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
   -------------------------------------------------------------------- */

#include "Python.h"

/* TODO: instead of saving to string, generate tree events */

#include "tidy.h"
#include "buffio.h"

static PyObject*
elementtidy_fixup(PyObject* self, PyObject* args)
{
    int rc;
    TidyDoc doc;
    TidyBuffer out = {0};
    TidyBuffer err = {0};
    PyObject* pyout;
    PyObject* pyerr;

    char* text;
    char* encoding = NULL;
    if (!PyArg_ParseTuple(args, "s|s:fixup", &text, &encoding))
        return NULL;

    doc = tidyCreate();

    /* options for nice XHTML output */
    if (encoding)
        /* if an encoding is given, use it for both input and output */
        tidyOptSetValue(doc, TidyCharEncoding, encoding);
    else
        /* if no encoding is given, use default input and utf-8 output */
        tidyOptSetValue(doc, TidyOutCharEncoding, "utf8");
    tidyOptSetBool(doc, TidyForceOutput, yes);
    tidyOptSetInt(doc, TidyWrapLen, 0);
    tidyOptSetBool(doc, TidyQuiet, yes);
    tidyOptSetBool(doc, TidyXhtmlOut, yes);
    tidyOptSetBool(doc, TidyXmlDecl, yes);
    tidyOptSetInt(doc, TidyIndentContent, 0);
    tidyOptSetBool(doc, TidyNumEntities, yes);

    rc = tidySetErrorBuffer(doc, &err);
    if (rc < 0) {
        PyErr_SetString(PyExc_IOError, "tidySetErrorBuffer failed");
        goto error;
    }

    rc = tidyParseString(doc, text);
    if (rc < 0) {
        PyErr_SetString(PyExc_IOError, "tidyParseString failed");
        goto error;
    }

    rc = tidyCleanAndRepair(doc);
    if (rc < 0) {
        PyErr_SetString(PyExc_IOError, "tidyCleanAndRepair failed");
        goto error;
    }

    rc = tidyRunDiagnostics(doc);
    if (rc < 0) {
        PyErr_SetString(PyExc_IOError, "tidyRunDiagnostics failed");
        goto error;
    }

    rc = tidySaveBuffer(doc, &out);
    if (rc < 0) {
        PyErr_SetString(PyExc_IOError, "tidyRunDiagnostics failed");
        goto error;
    }


    pyout = PyUnicode_FromString(out.bp ? out.bp : "");
    if (!pyout)
        goto error;
    pyerr = PyUnicode_FromString(err.bp ? err.bp : "");
    if (!pyerr) {
        Py_DECREF(pyout);
        goto error;
    }

    tidyBufFree(&out);
    tidyBufFree(&err);

    tidyRelease(doc);

    return Py_BuildValue("NN", pyout, pyerr);

  error:
    tidyBufFree(&out);
    tidyBufFree(&err);

    tidyRelease(doc);

    return NULL;
}

static PyMethodDef _functions[] = {
    {"fixup", elementtidy_fixup, 1},
    {NULL, NULL}
};

static struct PyModuleDef _elementtidy = {
  PyModuleDef_HEAD_INIT,
  "_elementtidy",
  NULL,
  -1,
  _functions
};

void
#ifdef WIN32
__declspec(dllexport)
#endif
/*
init_elementtidy()
{
Py_InitModule("_elementtidy", _functions);

}
*/
PyInit__elementtidy()
{
  PyModule_Create(&_elementtidy);
}
