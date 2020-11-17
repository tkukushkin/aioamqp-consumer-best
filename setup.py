import os

from setuptools import find_packages, setup


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='aioamqp-consumer-best',
    version='2.2.2',
    python_requires='~=3.7',
    url='https://github.com/tkukushkin/aioamqp-consumer-best',
    author='Timofey Kukushkin',
    author_email='tima@kukushkin.me',
    description='Consumer utility for AMQP',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'aioamqp',
        'anyio>=2',
    ],
    extras_require={
        'test': [
            'aiodocker',
            'mock<4',
            'mypy',
            'pycodestyle',
            'pylint',
            'pytest',
            'pytest-asyncio',
            'pytest-cov',
            'pytest-mock>=1.11.1,<2',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Typing :: Typed',
    ],
    project_urls={
        'Source': 'https://github.com/tkukushkin/aioamqp-consumer-best',
    },
)
