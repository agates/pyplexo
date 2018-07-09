from setuptools import find_packages, setup

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='domaintypesystem',
    version='0.0.2',
    description='Decentralized type system',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Alecks Gates',
    author_email='agates@mail.agates.io',
    keywords=[],
    url='https://gitlab.com/agates/domain-type-system',
    python_requires='>=3.5',
    classifiers=(
        'Development Status :: 1 - Planning',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Adaptive Technologies',
        'Topic :: Home Automation',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ),
    install_requires=[
        'blosc~=1.5',
        'capnpy~=0.5'
    ],
    packages=find_packages(),
)
