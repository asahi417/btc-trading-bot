from setuptools import setup, find_packages

FULL_VERSION = '0.0.0'

with open('README.md') as f:
    readme = f.read()

setup(
    name='btc_trader',
    version=FULL_VERSION,
    description='BTC currency trading.',
    long_description=readme,
    author='Asahi Ushio',
    author_email='asahi1992ushio@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests',
        'sqlalchemy',
        'pandas',
        'numpy',
        'psycopg2',
        'matplotlib',
        'toml',
        'slackweb',
        'pytz'
    ],
    dependency_links=[
        'git+https://github.com/matplotlib/mpl_finance.git'
    ]
)
