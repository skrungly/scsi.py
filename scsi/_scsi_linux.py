# This submodule should make use of the builtin `fcntl.ioctl` function
# to interact with the SCSI Generic driver in Linux.

import ctypes as ct
import os
from fcntl import ioctl
from typing import Tuple

from _utils import TypedStructure

# Any global constants and structs from here on out are as defined in
# the <linux/scsi/sg.h> header, unless otherwise specified.
SG_INTERFACE_ID_ORIG = ord("S")

SG_DXFER_NONE = -1
SG_DXFER_TO_DEV = -2
SG_DXFER_FROM_DEV = -3

SG_GET_VERSION_NUM = 0x2282
SG_IO = 0x2285


class SGIOHeader(TypedStructure):
    interface_id: ct.c_int
    dxfer_direction: ct.c_int
    cmd_len: ct.c_ubyte
    mx_sb_len: ct.c_ubyte
    iovec_count: ct.c_ushort
    dxfer_len: ct.c_uint
    dxferp: ct.c_char_p
    cmdp: ct.c_char_p
    sbp: ct.c_char_p
    timeout: ct.c_uint
    flags: ct.c_uint
    pack_id: ct.c_int
    usr_ptr: ct.c_char_p
    status: ct.c_ubyte
    masked_status: ct.c_ubyte
    msg_status: ct.c_ubyte
    sb_len_wr: ct.c_ubyte
    host_status: ct.c_ushort
    driver_status: ct.c_ushort
    resid: ct.c_int
    duration: ct.c_uint
    info: ct.c_uint


def _check_sg_version(device: int) -> Tuple[int, int, int]:
    version_buffer = ct.c_int()
    ioctl(device, SG_GET_VERSION_NUM, version_buffer)

    # if the version is X.Y.Z, then the number in the `version_buffer`
    # corresponds to (X * 10000 + Y * 100 + Z). let's interpret that.
    version = version_buffer.value

    ver_major = version // 10000
    ver_minor = (version % 10000) // 100
    ver_micro = version % 100

    return ver_major, ver_minor, ver_micro


def scsi_open(device_path: os.PathLike) -> int:
    device = os.open(device_path, os.O_RDWR | os.O_NONBLOCK)

    # we don't know if the new file handle actually refers to a SCSI
    # Generic device yet. however, by querying the SG driver version
    # we can check that the SG driver is not too outdated, while also
    # ensuring that we have indeed opened an actual SG device.
    ver_major, _, _ = _check_sg_version(device)

    if ver_major < 3:
        # earlier driver versions do not have the SG_IO ioctl we use.
        raise NotImplementedError(
            f"Outdated SG driver: {ver_major}.{ver_micro}.{ver_minor}"
        )

    return device


def scsi_read(device: int, cdb: bytes, amount: int, timeout: int) -> bytes:
    ...

def scsi_write(device: int, cdb: bytes, buffer: bytes, timeout: int) -> None:
    ...

def scsi_close(device: int) -> None:
    os.close(device)
