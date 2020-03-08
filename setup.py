from setuptools import find_packages, setup

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='plexo',
    version='1.0.0',
    description='Decentralized event coordination',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Alecks Gates',
    author_email='agates@mail.agates.io',
    keywords=[],
    url='https://gitlab.com/agates/pyplexo',
    python_requires='>=3.5',
    classifiers=(
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Adaptive Technologies',
        'Topic :: Home Automation',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ),
    install_requires=[
        'capnpy~=0.8',
        'pyrsistent~=0.15',
        'pyzmq~=19.0',
        'typing_extensions~=3.7'
    ],
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={'plexo': ['schema/*']},
    entry_points={
        'console_scripts': [
        ],
    }
)
