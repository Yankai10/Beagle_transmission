# cython: language_level=3
from libc.unistd cimport read
from cpython.bytes cimport PyBytes_FromStringAndSize, PyBytes_AS_STRING

def fast_read(int fd, size_t count):
    """
    从给定文件描述符 fd 读取 count 字节，返回 bytes 对象。
    """
    cdef PyObject *buf
    cdef ssize_t nread

    # 申请一个 bytes 容器
    buf = PyBytes_FromStringAndSize(NULL, count)
    if not buf:
        raise MemoryError()

    # 调用 POSIX read
    nread = read(fd, PyBytes_AS_STRING(buf), count)
    if nread < 0:
        # 失败时释放 buf 并抛出异常
        Py_DECREF(buf)
        raise OSError(errno, "read failed")

    # 如果读到的数据少于预期，需要截断
    if nread != count:
        # buf[:nread]
        return (<bytes>buf)[:nread]

    return <bytes>buf
