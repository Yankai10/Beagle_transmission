import os, time
from cython_fastread.fastread import fast_read

DEV = "/dev/beaglelogic"
SIZE = 1024 * 1024  # 1 MiB

# 1) 打开设备
fd = os.open(DEV, os.O_RDONLY)

# 如果你的驱动/PRU 需要手动 start，先执行一次 start
# 可以直接调用你的 sensor.start() 或者写 sysfs:
# os.system("echo 1 > /sys/class/misc/beaglelogic/state")

# 2) 用 fast_read 读取
t0 = time.time()
buf_f = fast_read(fd, SIZE)
t1 = time.time()

print("fast_read: ",
      "type=", type(buf_f),
      "len=", len(buf_f),
      "first16=", buf_f[:16],
      f"  @ {SIZE/(t1-t0)/1e6:.1f} MB/s")

# 3) 用 os.read 读取
# 注意：上一次 read 已经推进了指针，因此先 seek 回去：
os.lseek(fd, 0, os.SEEK_SET)

t0 = time.time()
buf_o = os.read(fd, SIZE)
t1 = time.time()

print("os.read:  ",
      "type=", type(buf_o),
      "len=", len(buf_o),
      "first16=", buf_o[:16],
      f"  @ {SIZE/(t1-t0)/1e6:.1f} MB/s")

os.close(fd)
