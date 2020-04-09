"""Interact with SCSI devices through a simple unified API.

This module aims to provide a single interface for communicating with
SCSI devices from different host platforms. Although the underlying
implementations for each platform are significantly different from one
another, they should all behave identically on the surface.

Default implementations of standard SCSI commands are not currently on
the roadmap for this module, but it could be done if there is demand.

The API provided by this module is given by a small set of functions:
    - scsi_open: Open a device file and return a file descriptor.
    - scsi_read: Send a command, then read and return the response.
    - scsi_write: Send a command alongside additional data.
    - scsi_close: Close a device with a given file descriptor.
"""

import platform

os_info = platform.uname()

if os_info.system == "Linux":
    from scsi._scsi_linux import *

# this module has not yet been tested for anything below windows 10.
# until it is confirmed to work, i am restricting the version here.
elif os_info.system == "Windows" and os_info.release == "10":
    from scsi._scsi_windows import *

else:
    raise NotImplementedError("Your system is not supported.")

__all__ = ["scsi_open", "scsi_read", "scsi_write", "scsi_close"]
