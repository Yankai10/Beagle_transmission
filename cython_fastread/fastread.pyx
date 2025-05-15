# cython_fastread/fastread.pyx
# cython: language_level=3

cdef extern from "unistd.h":
    ssize_t read(int fd, void *buf, size_t count)

cdef extern from "errno.h":
    int errno

def fast_read(int fd, size_t count):
    """
    从文件描述符 fd 读取 count 字节，返回一个 bytearray。
    """
    cdef bytearray buf = bytearray(count)
    cdef char* data = <char*>buf
    cdef ssize_t nread

    # 底层read
    nread = read(fd, data, count)
    if nread < 0:
        raise OSError(errno, "read failed")

    # 读到的数据比请求的少，就截断
    if nread != count:
        return buf[:nread]

    return buf
