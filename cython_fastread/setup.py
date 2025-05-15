from setuptools import setup
from Cython.Build import cythonize

setup(
    name="cython_fastread",
    ext_modules=cythonize("fastread.pyx", compiler_directives={'language_level': "3"}),
    zip_safe=False,
)
