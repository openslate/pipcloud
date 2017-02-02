from setuptools import setup

from pipcloud import __version__

# Note, this was forked from s3pypi, but I didn't like the way it worked and
# ended up changing almost everything.


setup(
    name='pipcloud',
    version=__version__,
    description='pip equivalent of deb-s3',
    author="Mike O'Malley",
    author_email='mikeo@openslatedata.com',
    url='https://github.com/openslate/pipcloud',
    packages=['pipcloud'],
    package_data={'pipcloud': ['templates/*.j2']},
    install_requires=['boto3', 'Jinja2', 'wheel'],
    entry_points={'console_scripts': ['pipcloud=pipcloud.main:main']},
)
