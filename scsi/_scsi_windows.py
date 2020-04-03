# This submodule should use the `ctypes` builtin module to interact
# with the `kernel32.dll` library in the Windows API. We could then
# use functions like `DeviceIoControl` to do whatever we need to do.

import os


def scsi_open(device_path: os.PathLike) -> int:
    ...

def scsi_read(device: int, cdb: bytes, amount: int, timeout: int) -> bytes:
    ...

def scsi_write(device: int, cdb: bytes, buffer: bytes, timeout: int) -> None:
    ...

def scsi_close(device: int) -> None:
    ...
