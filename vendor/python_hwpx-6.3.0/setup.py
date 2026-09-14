from setuptools import find_packages, setup

setup(
    name="python-hwpx",
    version="6.3.0",
    packages=find_packages(),
    package_data={"hwpx": ["data/**/*"]},
    include_package_data=True,
    install_requires=["lxml>=4.9,<7"],
)
