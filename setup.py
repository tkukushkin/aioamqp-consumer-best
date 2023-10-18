from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="aioamqp-consumer-best",
    version="2.4.0",
    python_requires=">=3.10",
    url="https://github.com/tkukushkin/aioamqp-consumer-best",
    author="Timofey Kukushkin",
    author_email="tima@kukushkin.me",
    description="Consumer utility for AMQP",
    long_description=(Path(__file__).parent / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "aioamqp",
        "anyio>=4",
        "exceptiongroup>=1.1.3",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    project_urls={
        "Source": "https://github.com/tkukushkin/aioamqp-consumer-best",
    },
)
