from distutils.core import setup

try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()

setup(
    name='aiohttp_tests',
    version='1.0.3',
    packages=['aiohttp_tests'],
    url='https://github.com/tumb1er/aiohttp_tests/',
    license='Beer License',
    author='tumbler',
    author_email='zimbler@gmail.com',
    description='unittest helper for aiohttp',
    long_description=read_md('README.md'),
    install_requires=['aiohttp>=2.0.7']
)
