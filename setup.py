from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="python-jira-plus",
    version="0.1.3",
    author='Avi Zaguri',
    author_email="",
    description="Enhanced Python client for JIRA with better error handling, pagination, and metadata validation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aviz92/python-jira-plus",
    project_urls={
        'Repository': 'https://github.com/aviz92/python-jira-plus',
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.9",
    install_requires=[
        "jira>=3.1.1",
        "retrying>=1.3.3",
        "custom-python-logger>=0.1.4",
    ],
    keywords="jira, atlassian, api, client",
)
