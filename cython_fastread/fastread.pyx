# cython_fastread/fastread.pyx
# cython: language_level=3

from cpython.bytes   cimport PyBytes_FromStringAndSize, PyBytes_AS_STRING
from cpython.ref     cimport PyObject

cdef extern from "unistd.h":
    ssize_t read(int fd, void *buf, size_t count)

cdef extern from "errno.h":
    int errno

def fast_read(int fd, size_t count):
    """
    直接分配未初始化的 bytes 缓冲区，然后 read() 写入，避免 double-memset，
    并且用 C 指针检查失败。
    """
    cdef PyObject *buf = PyBytes_FromStringAndSize(NULL, count)
    if buf == NULL:
        raise MemoryError()

    cdef void *data = <void*>PyBytes_AS_STRING(buf)
    cdef ssize_t nread = read(fd, data, count)
    if nread < 0:
        raise OSError(errno, "read failed")

    # 如果读到的数据比请求的少，就截断
    if nread != count:
        return (<bytes>buf)[:nread]

    return <bytes>buf


