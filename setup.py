import setuptools

setuptools.setup(
    name="microboiler",
    version="0.0.1",
    author="Okan Aslankan",
    author_email="okn.aslnkn@gmail.com",
    description="A Python tool for generating various types of microservice architecture projects.",
    url="https://github.com/DooMachine/microboiler",
    install_requires=['pyyaml==3.12','python-nginx==1.4.1'],
    packages=setuptools.find_packages(),
    package_dir={'microboiler': 'src'},
    include_package_data=True,
    keywords='microservices node .net devops development',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    project_urls={ 
        'Bug Reports': 'https://github.com/DooMachine/microboiler/issues',
        'Funding': 'https://donate.pypi.org',
        'Source': 'https://github.com/DooMachine/microboiler/',
    },
)