# This submodule should make use of the builtin `fcntl.ioctl` function
# to interact with the SCSI Generic driver in Linux.

import os


def scsi_open(device_path: os.PathLike) -> int:
    ...

def scsi_read(device: int, command: bytes, amount: int, timeout: int) -> bytes:
    ...

def scsi_write(device: int, command: bytes, buffer: bytes) -> None:
    ...

def scsi_close(device: int) -> None:
    ...
