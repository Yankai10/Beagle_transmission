# cython_fastread/fastread.pyx
# cython: language_level=3

from cpython.bytes cimport PyBytes_FromStringAndSize, PyBytes_AS_STRING

cdef extern from "unistd.h":
    ssize_t read(int fd, void *buf, size_t count)

cdef extern from "errno.h":
    int errno

def fast_read(int fd, size_t count):
    """
    从文件描述符 fd 中读取 count 字节，返回一个 Python bytes 对象。
    """
    cdef bytes buf
    cdef char* data
    cdef ssize_t nread

    # 1) 申请一个指定大小的 bytes 对象（内部预分配好内存）
    buf = PyBytes_FromStringAndSize(NULL, count)
    if buf is NULL:
        raise MemoryError()

    # 2) 拿到底层内存指针
    data = PyBytes_AS_STRING(buf)

    # 3) 调用底层 read
    nread = read(fd, <void*>data, count)
    if nread < 0:
        # 失败就抛异常（GC 会回收 buf）
        raise OSError(errno, "read failed")

    # 4) 如果没读满 count，就切片返回
    if nread != count:
        return buf[:nread]

    # 5) 否则整块返回
    return buf
