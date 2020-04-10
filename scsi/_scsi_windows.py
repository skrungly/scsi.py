import os
import ctypes as ct
import ctypes.wintypes as wt
from typing import Optional

from scsi._utils import TypedStructure

__all__ = ["scsi_open", "scsi_read", "scsi_write", "scsi_close"]

MAX_SENSE_SIZE = 32

# this type is currently not defined, but i have asked about it on the
# `capi-sig` mailing list to see if that might have been accidental.
UCHAR = ct.c_ubyte

# these constants are defined in `ntddscsi.h`:
IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x4d014

SCSI_IOCTL_DATA_OUT = 0
SCSI_IOCTL_DATA_IN = 1
SCSI_IOCTL_DATA_UNSPECIFIED = 2


class SCSIPassThroughDirect(TypedStructure):
    length: wt.USHORT
    scsi_status: UCHAR
    path_id: UCHAR
    target_id: UCHAR
    lun: UCHAR
    cdb_length: UCHAR
    sense_info_length: UCHAR
    data_in: UCHAR
    data_transfer_length: wt.ULONG
    timeout_value: wt.ULONG
    data_buffer: ct.c_char_p
    sense_info_offset: wt.ULONG
    cdb: ct.c_char * 16

    # this sense buffer is not defined here in the reference struct.
    # however, it is nice to have it here because it makes it easy to
    # compute the value of `sense_info_offset`.
    # TODO: implement a way of making this array variable-sized. this
    # would allow for a custom value for maximum sense size if needed.
    sense_buffer: ct.c_char * MAX_SENSE_SIZE


# the following code defines the constants required for CreateFileW:
GENERIC_READ = 0x80000000  # for dwDesiredAccess
GENERIC_WRITE = 0x40000000

FILE_SHARE_READ = 0x00000001  # for dwShareMode
FILE_SHARE_WRITE = 0x00000002

OPEN_EXISTING = 3  # for dwCreationDisposition

FILE_ATTRIBUTE_NORMAL = 0x80  # for dwFlagsAndAttributes

_w32_create_file_w = ct.windll.kernel32.CreateFileW
_w32_create_file_w.restype = wt.HANDLE
_w32_create_file_w.argtypes = [
    wt.LPCWSTR,  # lpFileName
    wt.DWORD,    # dwDesiredAccess
    wt.DWORD,    # dwShareMode
    wt.LPVOID,   # lpSecurityAttributes
    wt.DWORD,    # dwCreationDisposition
    wt.DWORD,    # dwFlagsAndAttributes
    wt.HANDLE,   # hTemplateFile
]

_w32_close_handle = ct.windll.kernel32.CloseHandle
_w32_close_handle.restype = wt.BOOL
_w32_close_handle.argtypes = [wt.HANDLE]

_w32_device_io_control = ct.windll.kernel32.DeviceIoControl
_w32_device_io_control.restype = wt.BOOL
_w32_device_io_control.argtypes = [
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

    result = _w32_device_io_control(
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


def _execute_command(
    handle: int,
    cdb: bytes,
    buffer: bytes,
    timeout: int,
    direction: int,
):

    # account for the extra sense buffer we have on the end
    header_size = ct.sizeof(SCSIPassThroughDirect) - MAX_SENSE_SIZE
    sense_buffer = bytes(MAX_SENSE_SIZE)

    scsi_header = SCSIPassThroughDirect(
        length=header_size,
        cdb_length=len(cdb),
        sense_info_length=MAX_SENSE_SIZE,
        data_in=direction,
        data_transfer_length=len(buffer),
        timeout_value=timeout,
        data_buffer=buffer,
        sense_info_offset=header_size,
        cdb=cdb,
        sense_buffer=sense_buffer
    )

    scsi_header_buffer = ct.string_at(
        ct.addressof(scsi_header),
        ct.sizeof(scsi_header),
    )

    _device_io_control(
        handle,
        IOCTL_SCSI_PASS_THROUGH_DIRECT,
        scsi_header_buffer,
        None,
    )

    # TODO: deal with the `scsi_status` and `sense_buffer` attributes.
    # these should be used to raise SCSI-specific errors that appear.


def _raise_last_error():
    last_error = ct.GetLastError()
    if last_error != 0:
        raise ct.WinError(last_error)


def scsi_open(device_path: os.PathLike) -> int:
    device = _w32_create_file_w(
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
    buffer = bytes(amount)

    _execute_command(
        device,
        cdb,
        buffer,
        timeout // 1000,
        SCSI_IOCTL_DATA_IN,
    )

    return buffer


def scsi_write(device: int, cdb: bytes, buffer: bytes, timeout: int) -> None:
    _execute_command(
        device,
        cdb,
        buffer,
        timeout // 1000,
        SCSI_IOCTL_DATA_OUT,
    )


def scsi_close(device: int) -> None:
    _w32_close_handle(device)
    _raise_last_error()
