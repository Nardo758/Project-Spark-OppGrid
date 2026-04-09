from setuptools import setup, find_packages

setup(
    name="oppgrid",
    version="1.0.0",
    description="Official Python SDK for the OppGrid Public API v1",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="OppGrid",
    author_email="api@oppgrid.com",
    url="https://oppgrid.com/developer",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="oppgrid api sdk business intelligence opportunities markets",
)
