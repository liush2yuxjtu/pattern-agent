"""Test-only software WebGPU launch; readers need no flags or these tools."""
import os


def chromium_args():
    flags=['--no-sandbox','--enable-unsafe-swiftshader']
    if os.environ.get('CLOTH_WEBGPU')=='1':
        # --disable-vulkan-surface makes presentation blank on this host even
        # though GPU buffer/texture readback succeeds. Keep the surface enabled.
        flags += ['--enable-unsafe-webgpu','--use-angle=swiftshader',
                  '--enable-features=Vulkan','--use-vulkan=swiftshader','--use-gl=angle']
    return flags
