# cython: language_level=3
from cpython.bytes cimport PyBytes_FromStringAndSize, PyBytes_AS_STRING
from cpython.ref   cimport Py_DECREF

# 直接从标准头文件声明 POSIX read 和 errno
cdef extern from "unistd.h":
    ssize_t read(int fd, void *buf, size_t count)
cdef extern from "errno.h":
    int errno

def fast_read(int fd, size_t count):
    cdef PyObject *buf
    cdef ssize_t nread

    # 申请一个 bytes 缓冲区
    buf = PyBytes_FromStringAndSize(NULL, count)
    if buf is NULL:
        raise MemoryError()

    # 调用底层 read()
    nread = read(fd, PyBytes_AS_STRING(buf), count)
    if nread < 0:
        Py_DECREF(buf)
        raise OSError(errno, "read failed")

    # 如果读到的数据比请求的少，就截断返回
    if nread != count:
        return (<bytes>buf)[:nread]

    return <bytes>buf


