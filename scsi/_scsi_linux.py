import ctypes as ct
import os
from enum import IntEnum
from fcntl import ioctl
from typing import Tuple

from scsi._utils import SCSIError, SCSIStatus, TypedStructure

__all__ = ["scsi_open", "scsi_read", "scsi_write", "scsi_close"]

MAX_SENSE_SIZE = 32

# Any global constants and structs from here on out are as defined in
# the <linux/scsi/sg.h> header, unless otherwise specified.
SG_INTERFACE_ID_ORIG = ord("S")

SG_DXFER_NONE = -1
SG_DXFER_TO_DEV = -2
SG_DXFER_FROM_DEV = -3

SG_GET_VERSION_NUM = 0x2282
SG_IO = 0x2285

SG_INFO_OK_MASK = 0x1
SG_INFO_OK = 0x0
SG_INFO_CHECK = 0x1


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


# This enum, as well as the DriverStatus enum, represent the relevant
# constants that are defined in <linux/scsi/scsi.h>.
class HostStatus(IntEnum):
    OK = 0x00
    NO_CONNECT = 0x01
    BUS_BUSY = 0x02
    TIME_OUT = 0x03
    BAD_TARGET = 0x04
    ABORT = 0x05
    PARITY = 0x06
    ERROR = 0x07
    RESET = 0x08
    BAD_INTR = 0x09
    PASSTHROUGH = 0x0a
    SOFT_ERROR = 0x0b
    IMM_RETRY = 0x0c
    REQUEUE = 0x0d
    TRANSPORT_DISRUPTED = 0x0e
    TRANSPORT_FAILFAST = 0x0f
    TARGET_FAILURE = 0x10
    NEXUS_FAILURE = 0x11
    ALLOC_FAILURE = 0x12
    MEDIUM_ERROR = 0x13

    def raise_if_bad(self, message: str):
        if self is not HostStatus.OK:
            cls_name = type(self).__name__
            raise SCSIError(f"{cls_name}.{self.name}: {message}")


# TODO: It could be worth adding another enum for the DriverSuggestion
# part of the response. Right now, that must be masked out for this.
class DriverStatus(IntEnum):
    OK = 0x00
    BUSY = 0x01
    SOFT = 0x02
    MEDIA = 0x03
    ERROR = 0x04
    INVALID = 0x05
    TIMEOUT = 0x06
    HARD = 0x07
    SENSE = 0x08

    def raise_if_bad(self, message: str):
        if self is not DriverStatus.OK:
            cls_name = type(self).__name__
            raise SCSIError(f"{cls_name}.{self.name}: {message}")


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


def _check_for_errors(sgio_hdr: SGIOHeader, sense_buffer: bytes):
    if (sgio_hdr.info & SG_INFO_OK_MASK) != SG_INFO_OK:
        status = SCSIStatus(sgio_hdr.status.value)
        status_info = f"status buffer: {status.hex()}"

        if status is SCSIStatus.CHECK_CONDITION:
            status.raise_if_bad(status_info)

        status.raise_if_bad(status_info)

        # the 0x0f mask on the driver status code makes sure we only
        # get the status code itself, and not the suggestion. TODO: we
        # could implement the suggestion as a new enum at some point.
        DriverStatus(sgio_hdr.driver_status & 0x0f).raise_if_bad(status_info)
        HostStatus(sgio_hdr.host_status).raise_if_bad(status_info)

        # i think all of our bases are covered at this point, but we
        # should make sure we don't continue silently from this state.
        # TODO: perhaps this error message can be made more useful by
        # providing a full dump of the SGIOHeader in some format?
        raise SCSIError("An unknown error occurred.")


def _execute_command(
    device: int,
    cdb: bytes,
    buffer: bytes,
    timeout: int,
    direction: int,
):
    sense_buffer = bytes(MAX_SENSE_SIZE)

    sgio_hdr = SGIOHeader(
        interface_id=SG_INTERFACE_ID_ORIG,

        cmdp=cdb,
        cmd_len=len(cdb),

        dxfer_direction=direction,
        dxferp=buffer,
        dxfer_len=len(buffer),

        sbp=sense_buffer,
        mx_sb_len=MAX_SENSE_SIZE,
        timeout=timeout,
    )

    ioctl(device, SG_IO, sgio_hdr)

    _check_for_errors(sgio_hdr, sense_buffer)


def scsi_open(device_path: os.PathLike) -> int:
    device = os.open(device_path, os.O_RDWR | os.O_NONBLOCK)

    # we don't know if the new file handle actually refers to a SCSI
    # Generic device yet. however, by querying the SG driver version
    # we can check that the SG driver is not too outdated, while also
    # ensuring that we have indeed opened an actual SG device.
    ver_major, ver_minor, ver_micro = _check_sg_version(device)

    if ver_major < 3:
        # earlier driver versions do not have the SG_IO ioctl we use.
        raise NotImplementedError(
            f"Outdated SG driver: {ver_major}.{ver_minor}.{ver_micro}"
        )

    return device


def scsi_read(device: int, cdb: bytes, amount: int, timeout: int) -> bytes:
    buffer = bytes(amount)

    _execute_command(
        device,
        cdb,
        buffer,
        timeout,
        SG_DXFER_FROM_DEV
    )

    return buffer


def scsi_write(device: int, cdb: bytes, buffer: bytes, timeout: int) -> None:
    _execute_command(
        device,
        cdb,
        buffer,
        timeout,
        SG_DXFER_TO_DEV
    )


def scsi_close(device: int) -> None:
    os.close(device)
