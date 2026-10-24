"""Model-free Vulkan initialization; call only inside a bounded child process."""

import ctypes as C
import os
from pathlib import Path


def is_real_gpu(kind: int, vendor: int, name: str) -> bool:
    """Require Vulkan integrated/discrete type and reject known software drivers."""
    return (
        kind in (1, 2)
        and vendor not in (0x1414, 0x1AE0)
        and not any(
            text in name.casefold()
            for text in ("lavapipe", "llvmpipe", "swiftshader", "basic render", "software")
        )
    )


class InstanceInfo(C.Structure):
    _fields_ = [
        ("type", C.c_uint32),
        ("next", C.c_void_p),
        ("flags", C.c_uint32),
        ("app", C.c_void_p),
        ("layers", C.c_uint32),
        ("layer_names", C.c_void_p),
        ("extensions", C.c_uint32),
        ("extension_names", C.c_void_p),
    ]


def physical_gpu_names() -> set[str]:
    """Read the stable Vulkan 1.0 properties prefix, never guess from ggml's type."""
    vk = C.CDLL("vulkan-1.dll", winmode=0x800)
    vk.vkCreateInstance.argtypes = [C.POINTER(InstanceInfo), C.c_void_p, C.POINTER(C.c_void_p)]
    vk.vkEnumeratePhysicalDevices.argtypes = [C.c_void_p, C.POINTER(C.c_uint32), C.c_void_p]
    vk.vkGetPhysicalDeviceProperties.argtypes = [C.c_void_p, C.c_void_p]
    vk.vkGetPhysicalDeviceProperties.restype = None
    vk.vkDestroyInstance.argtypes = [C.c_void_p, C.c_void_p]
    vk.vkDestroyInstance.restype = None
    instance = C.c_void_p()
    if vk.vkCreateInstance(C.byref(InstanceInfo(type=1)), None, C.byref(instance)):
        return set()
    try:
        count = C.c_uint32()
        if vk.vkEnumeratePhysicalDevices(instance, C.byref(count), None) or count.value > 64:
            return set()
        devices = (C.c_void_p * count.value)()
        if vk.vkEnumeratePhysicalDevices(instance, C.byref(count), devices):
            return set()
        names = set()
        for device in devices:
            # VkPhysicalDeviceProperties is smaller than this buffer. Its first
            # five uint32 values and deviceName[256] have fixed Vulkan 1.0 ABI.
            data = C.create_string_buffer(4096)
            vk.vkGetPhysicalDeviceProperties(device, data)
            vendor = int.from_bytes(data.raw[8:12], "little")
            kind = int.from_bytes(data.raw[16:20], "little")
            name = data.raw[20:276].split(b"\0", 1)[0].decode("utf-8", errors="replace")
            if is_real_gpu(kind, vendor, name):
                names.add(name)
        return names
    finally:
        vk.vkDestroyInstance(instance, None)


def probe_device(folder: Path) -> bool:
    """Initialize an actual engine backend and clear/synchronize a 4 KiB buffer."""
    real = physical_gpu_names()
    if not real:
        return False
    with os.add_dll_directory(str(folder.resolve())):
        api = C.CDLL(str((folder / "ggml.dll").resolve()))
        base = C.CDLL(str((folder / "ggml-base.dll").resolve()))

        def fn(name, args, result):
            value = getattr(api if name == "ggml_backend_load" else base, name)
            value.argtypes, value.restype = args, result
            return value

        ptr = C.c_void_p
        load = fn("ggml_backend_load", [C.c_char_p], ptr)
        count = fn("ggml_backend_reg_dev_count", [ptr], C.c_size_t)
        get = fn("ggml_backend_reg_dev_get", [ptr, C.c_size_t], ptr)
        description = fn("ggml_backend_dev_description", [ptr], C.c_char_p)
        init = fn("ggml_backend_dev_init", [ptr, C.c_char_p], ptr)
        alloc = fn("ggml_backend_alloc_buffer", [ptr, C.c_size_t], ptr)
        clear = fn("ggml_backend_buffer_clear", [ptr, C.c_uint8], None)
        sync = fn("ggml_backend_synchronize", [ptr], None)
        free_buffer = fn("ggml_backend_buffer_free", [ptr], None)
        free = fn("ggml_backend_free", [ptr], None)
        reg = load(os.fsencode((folder / "ggml-vulkan.dll").resolve()))
        if not reg:
            return False
        for index in range(count(reg)):
            device = get(reg, index)
            if description(device).decode("utf-8", errors="replace") not in real:
                continue
            backend = init(device, None)
            if not backend:
                continue
            try:
                buffer = alloc(backend, 4096)
                if buffer:
                    try:
                        clear(buffer, 0)
                        sync(backend)
                        return True
                    finally:
                        free_buffer(buffer)
            finally:
                free(backend)
    return False
