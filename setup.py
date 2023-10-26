from setuptools import setup

setup(
    install_requires=['Pillow', 'graphviz'],
    author='Akahara',
    name='commandlinetools',
    version='1.0.0',
    description='Random command line tools',
    scripts=['catimg', 'git-find', 'graph-dependencies'],
)