# This submodule should make use of the builtin `fcntl.ioctl` function
# to interact with the SCSI Generic driver in Linux.

import ctypes as ct
import os

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


def scsi_open(device_path: os.PathLike) -> int:
    ...

def scsi_read(device: int, command: bytes, amount: int, timeout: int) -> bytes:
    ...

def scsi_write(device: int, command: bytes, buffer: bytes) -> None:
    ...

def scsi_close(device: int) -> None:
    ...
