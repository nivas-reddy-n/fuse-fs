from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="fuse-fs",
    version="0.1.0",
    author="Nivas Reddy Nalla",
    author_email="nivasreddynalla@gmail.com",
    description="FUSE Virtual File System with Metadata Storage, Cloud Sync, and LFU Caching",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nivas-reddy-n/fuse-fs",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: MIT License",
        "Operating System :: POSIX",
        "Topic :: System :: Filesystems",
    ],
    python_requires=">=3.7",
    install_requires=[
        "fusepy>=3.0.1",
        "mysql-connector-python>=8.0.32",
        "google-api-python-client>=2.86.0",
        "google-auth-httplib2>=0.1.0",
        "google-auth-oauthlib>=1.0.0",
        "pycryptodome>=3.18.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "fuse-fs=fuse_fs.__main__:main",
        ],
    },
) 