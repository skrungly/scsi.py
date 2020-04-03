import ctypes as ct
from enum import IntEnum

# the type of `Structure` can be found in the `_ctypes` module, but we
# cannot just import it because the `_ctypes` module does not export
# that type. instead, we can just steal it from the class itself. :D
MetaStructure = type(ct.Structure)


class MetaTypedStructure(MetaStructure):
    def __new__(metacls, name, bases, attrs, **kwargs):
        type_hints = attrs.get("__annotations__", {})
        attrs["_fields_"] = list(type_hints.items())
        return super().__new__(metacls, name, bases, attrs, **kwargs)


class TypedStructure(ct.Structure, metaclass=MetaTypedStructure):
    pass


class SCSIStatus(IntEnum):
    GOOD = 0x00
    CHECK_CONDITION = 0x02
    CONDITION_MET = 0x04
    BUSY = 0x08
    INTERMEDIATE = 0x10  # obsolete
    INTERMEDIATE_CONDITION_MET = 0x14  # obsolete
    RESERVATION_CONFLICT = 0x18
    COMMAND_TERMINATED = 0x22  # obsolete
    TASK_SET_FULL = 0x28
    ACA_ACTIVE = 0x30
    TASK_ABORTED = 0x40

    def raise_if_bad(self, message: str):
        if self is not SCSIStatus.GOOD:
            raise SCSIStatusError(self, message)


class SCSIError(Exception):
    """
    A base class for SCSI-related errors.

    Although inherited exception types are designed to be platform-
    agnostic, their error messages may be platform-specific in order
    to allow for better problem diagnosis.
    """


class SCSIStatusError(SCSIError):
    def __init__(self, status: SCSIStatus, message: str):
        self.status = status
        self.message = message

    def __str__(self):
        return f"{self.status.name}: {self.message}"
