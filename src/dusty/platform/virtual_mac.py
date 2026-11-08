"""Recognize a virtual Mac, where Dusty never starts the Metal engine.

A virtual Mac's GPU is Apple's paravirtual GPU. On GitHub's Mac runners the
pinned Metal engine either reports that this GPU lacks features it needs or
stalls while it compiles its shaders, before it reports anything (MAC11-VM).
macOS sets kern.hv_vmm_present inside a virtual machine, and those runners
also name their processor like "Apple M1 (Virtual)". Reading two sysctls
starts no process; anything unreadable counts as a real Mac.
"""

import sys


def is_virtual_mac() -> bool:
    """True inside a virtual Mac; False on a real Mac, on other systems or if unknown."""
    if sys.platform != "darwin":
        return False
    # Imported here so that importing the engine never loads ctypes.
    from dusty.platform.cpu_topology import _darwin_sysctl_count
    from dusty.platform.gpu_signature import _sysctl_string

    try:
        if _darwin_sysctl_count(b"kern.hv_vmm_present") == 1:
            return True
        return _sysctl_string(b"machdep.cpu.brand_string").endswith("(Virtual)")
    except (AttributeError, OSError, ValueError):
        return False
