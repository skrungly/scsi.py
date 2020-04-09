# This submodule should use the `ctypes` builtin module to interact
# with the `kernel32.dll` library in the Windows API. We could then
# use functions like `DeviceIoControl` to do whatever we need to do.

import os
import ctypes as ct
import ctypes.wintypes as wt

# these constants are defined in `ntddscsi.h`:
IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x4d014

SCSI_IOCTL_DATA_OUT = 0
SCSI_IOCTL_DATA_IN = 1
SCSI_IOCTL_DATA_UNSPECIFIED = 2

# the following code defines the constants required for CreateFileW:
GENERIC_READ = 0x80000000  # for dwDesiredAccess
GENERIC_WRITE = 0x40000000

FILE_SHARE_READ = 0x00000001  # for dwShareMode
FILE_SHARE_WRITE = 0x00000002

OPEN_EXISTING = 3  # for dwCreationDisposition

FILE_ATTRIBUTE_NORMAL = 0x80  # for dwFlagsAndAttributes

# TODO: rename these functions to make it clear that they are private
# and that they originate from the win32 API rather than in here.
create_file_w = ct.windll.kernel32.CreateFileW
create_file_w.restype = wt.HANDLE
create_file_w.argtypes = [
    wt.LPCWSTR,  # lpFileName
    wt.DWORD,    # dwDesiredAccess
    wt.DWORD,    # dwShareMode
    wt.LPVOID,   # lpSecurityAttributes
    wt.DWORD,    # dwCreationDisposition
    wt.DWORD,    # dwFlagsAndAttributes
    wt.HANDLE,   # hTemplateFile
]

close_handle = ct.windll.kernel32.CloseHandle
close_handle.restype = wt.BOOL
close_handle.argtypes = [wt.HANDLE]

device_io_control = ct.windll.kernel32.DeviceIoControl
device_io_control.restype = wt.BOOL
device_io_control.argtypes = [
    wt.HANDLE,   # hDevice
    wt.DWORD,    # dwIoControlCode
    wt.LPVOID,   # lpInBuffer
    wt.DWORD,    # nInBufferSize
    wt.LPVOID,   # lpOutBuffer
    wt.DWORD,    # nOutBufferSize
    wt.LPDWORD,  # lpBytesReturned
    wt.LPVOID,   # lpOverlapped
]


def _device_io_control(
    handle: int,
    control_code: int,
    in_buffer: Optional[ct.Array],
    out_buffer: Optional[ct.Array],
):
    if in_buffer is None:
        in_buffer = ct.create_string_buffer(0)

    if out_buffer is None:
        out_buffer = ct.create_string_buffer(0)

    bytes_returned = wt.DWORD()

    result = device_io_control(
        handle,
        control_code,
        in_buffer,
        len(in_buffer),
        out_buffer,
        len(out_buffer),
        ct.byref(bytes_returned),
        None
    )

    _raise_last_error()


def _raise_last_error():
    last_error = ct.GetLastError()
    if last_error != 0:
        raise ct.WinError(last_error)


def scsi_open(device_path: os.PathLike) -> int:
    device = create_file_w(
        device_path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )

    _raise_last_error()

    return device

def scsi_read(device: int, cdb: bytes, amount: int, timeout: int) -> bytes:
    ...

def scsi_write(device: int, cdb: bytes, buffer: bytes, timeout: int) -> None:
    ...

def scsi_close(device: int) -> None:
    close_handle(device)
    _raise_last_error()
