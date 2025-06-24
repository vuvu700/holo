from setuptools import setup, find_packages


setup(
    name='holo',
    version='0.1.0',
    author='Ludovic Andrieu',
    author_email='vuvu700.vuvu@gmail.com',
    description='A short description of your package',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/vuvu700/holo',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    install_requires=[
        "numpy",
        "numba",
        "matplotlib",
        "typing_extensions",
        "requests",
        "mypy",
        "multiprocess",
        "ffmpeg-python",
    ],
)
