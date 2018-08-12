from setuptools import find_packages, setup


setup(
    name='aioamqp-consumer-best',
    version='1.0.1',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'aioamqp',
        'aionursery',
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
