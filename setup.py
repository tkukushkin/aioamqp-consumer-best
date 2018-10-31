import os

from setuptools import find_packages, setup


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='aioamqp-consumer-best',
    version='1.1.2',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'aioamqp',
        'aionursery < 0.3.0',
        'dataclasses',
    ],
    extras_require={
        'test': [
            'mypy==0.600',
            'pycodestyle',
            'pylint',
            'pytest',
            'pytest-asyncio',
            'pytest-cov',
            'pytest-mock',
        ],
    },
)
