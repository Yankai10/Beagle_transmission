# cython_fastread/fastread.pyx
# cython: language_level=3

from cpython.bytes cimport PyBytes_FromStringAndSize, PyBytes_AS_STRING

cdef extern from "unistd.h":
    ssize_t read(int fd, void *buf, size_t count)

cdef extern from "errno.h":
    int errno

def fast_read(int fd, size_t count):
    """
    直接分配未初始化的 bytes 缓冲区，然后 read() 写入，避免 double-memset，
    应该能接近 os.read 的速度。
    """
    cdef object buf = PyBytes_FromStringAndSize(NULL, count)
    if buf is NULL:
        raise MemoryError()
    cdef void* data = <void*>PyBytes_AS_STRING(buf)
    cdef ssize_t nread = read(fd, data, count)
    if nread < 0:
        raise OSError(errno, "read failed")
    if nread != count:
        return buf[:nread]
    return buf

