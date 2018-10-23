from setuptools import find_packages, setup


setup(
    name='aioamqp-consumer-best',
    version='1.1.0',
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
