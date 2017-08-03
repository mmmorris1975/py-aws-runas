from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_desc = f.read()

setup(
  name='aws-runas',
  version='0.1.0',
  description='Execute a command using an AWS assumed role',
  long_description=long_desc,
  url='https://github.com/mmmorris1975/aws-runas',
  author='Michael Morris',
  author_email='mmmorris1975@netscape.net',
  license='MIT',
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3'
  ],
  keywords='aws runas iam role',
  install_requires=['boto3>=1.3.1'],
  python_requires='>=2.7, <4',
  packages=['aws_runas'],
  entry_points={
    'console_scripts': [
      'aws-runas = aws_runas:main'
    ]
  }
)
