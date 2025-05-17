from setuptools import setup, find_packages

package_version = '1.0.1'

package_name = 'python-jira-plus'
package_description = 'Enhanced Python client for JIRA with better error handling, pagination, and metadata validation.'

package_long_description_content_type = 'text/markdown'
package_url = f'https://github.com/aviz92/{package_name}'
package_python_requires = '>=3.11'
package_author = 'Avi Zaguri'

with open('requirements.txt', 'r') as file:
    package_install_requires = [
        line.strip() for line in file.readlines() if line.strip() and not line.startswith('#')
    ]

with open('README.md', 'r') as file:
    package_long_description = file.read()

setup(
    name=package_name,
    version=package_version,
    packages=find_packages(include=[package_name, f'{package_name}.*']),
    install_requires=package_install_requires,
    author=package_author,
    author_email='',
    description=package_description,
    long_description=package_long_description,
    long_description_content_type=package_long_description_content_type,
    url=package_url,
    project_urls={
        'Repository': package_url,
    },
    python_requires=package_python_requires,
)
