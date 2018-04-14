from setuptools import find_packages, setup


setup(
    name='aioamqp-consumer',
    version='1.0.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'aioamqp',
        'dataclasses',
    ],
    extras_require={
        'test': [
            'mypy',
            'pycodestyle',
            'pylint',
            'pytest',
            'pytest-asyncio',
            'pytest-cov',
            'pytest-mock',
        ],
    },
)
