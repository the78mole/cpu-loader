from setuptools import setup, Extension
import platform

extra_compile_args = []
extra_link_args = []

if platform.system() != 'Windows':
    extra_compile_args = ['-pthread', '-O3']
    extra_link_args = ['-pthread']

module = Extension(
    'cpu_loader_core',
    sources=['src/cpu_loader_core.c'],
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
)

setup(
    ext_modules=[module],
)
