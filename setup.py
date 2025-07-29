from setuptools import setup, find_packages

setup(
    name='df',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'psutil>=7.0.0'
    ],
    python_requires='>=3.10',
    author='DBCM Technologies',
    description='A HTTP File Server',
    url='https://github.com/DBCM-Technologies/df',
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
)
