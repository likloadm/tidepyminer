from setuptools import setup, Extension

tdc_mine_module = Extension('tdc_mine',
                            sources = ['src/module.c',
                                       'src/yespower.c',
                                       'src/yespower-opt.c',
                                       'src/sha2.c',
                                       'src/sha256.c',
                                       'src/cpu-miner.c',
                                       'src/util.c'
                                       ],
                            extra_compile_args=['-O2', '-funroll-loops', '-fomit-frame-pointer'],
                            include_dirs=['.','src'])

setup (name = 'tdc_mine',
       version = '1.0.0',
       author_email = 'tidecoins@protonmail.com',
       author = 'yarsawyer',
       url = 'https://github.com/yarsawyer/tdc_mine',
       description = 'Secret technology',
       package_dir = {"": "src"},
       ext_modules = [tdc_mine_module])
