#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *m_sha256d_str(PyObject *self, PyObject *args)
{
    PyBytesObject *coinb1str;
    PyBytesObject *xnonce1str;
    PyBytesObject *xnonce2str;
    PyBytesObject *coinb2str;
    PyBytesObject *merklestr;

    uint8_t *ret;
    PyObject *rv;

    if (!PyArg_ParseTuple(args, "SSSSS", &coinb1str, &xnonce1str, &xnonce2str, &coinb2str, &merklestr))
        return NULL;

    Py_INCREF(coinb1str);
    Py_INCREF(xnonce1str);
    Py_INCREF(xnonce2str);
    Py_INCREF(coinb2str);
    Py_INCREF(merklestr);

    ret = PyMem_Malloc(65);

    sha256d_str((uint8_t *)PyBytes_AsString((PyObject*) coinb1str), (uint8_t *)PyBytes_AsString((PyObject*) xnonce1str), (uint8_t *)PyBytes_AsString((PyObject*) xnonce2str), (uint8_t *)PyBytes_AsString((PyObject*) coinb2str), (uint8_t *)PyBytes_AsString((PyObject*) merklestr), ret);

    Py_DECREF(merklestr);
    Py_DECREF(coinb2str);
    Py_DECREF(xnonce2str);
    Py_DECREF(xnonce1str);
    Py_DECREF(coinb1str);


    rv = Py_BuildValue("y#", ret, 64);

    PyMem_Free(ret);

    return rv;
}


static PyObject *m_miner_thread(PyObject *self, PyObject *args)
{
    PyBytesObject *blockheader;
    PyBytesObject *targetstr;
    uint32_t first_nonce;

    uint8_t *ret;
    PyObject *rv;

    if (!PyArg_ParseTuple(args, "SSI", &blockheader, &targetstr, &first_nonce))
        return NULL;

    Py_INCREF(blockheader);
    Py_INCREF(targetstr);

    ret = PyMem_Malloc(139);

    miner_thread((uint8_t *)PyBytes_AsString((PyObject*) blockheader), (uint8_t *)PyBytes_AsString((PyObject*) targetstr), first_nonce, ret);

    Py_DECREF(targetstr);
    Py_DECREF(blockheader);


    rv = Py_BuildValue("y#", ret, 138);

    PyMem_Free(ret);

    return rv;
}

static PyMethodDef TdcmineMethods[] = {
    { "sha256d_str", (PyCFunction)m_sha256d_str, METH_VARARGS, "m_sha256d_str" },
    { "miner_thread", (PyCFunction)m_miner_thread, METH_VARARGS, "m_miner_thread" },
    { NULL, NULL, 0, NULL }
};

static struct PyModuleDef TdcmineModule = {
    PyModuleDef_HEAD_INIT,
    "tdc_mine",
    "...",
    -1,
    TdcmineMethods
};

PyMODINIT_FUNC PyInit_tdc_mine(void) {
    return PyModule_Create(&TdcmineModule);
}
