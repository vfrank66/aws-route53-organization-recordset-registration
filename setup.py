# pylint: disable=missing-docstring

import os
import sys

from setuptools import find_namespace_packages, setup

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

PROPS = {}
with open("sonar-project.properties", "r") as fh:
    for line in fh:
        line = line.rstrip()

        if "=" not in line:
            continue
        if line.startswith("#"):
            continue

        key, value = line.split("=", 1)

        PROPS[key] = value

BASE_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(BASE_DIR, "src")

sys.path.insert(0, SRC_DIR)


setup(
    name="aws-route53-organization-recordset-registration",
    version=PROPS.get("sonar.projectVersion"),
    author="vfrank66",
    description=PROPS.get("sonar.projectDescription"),
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url=PROPS.get("sonar.links.scm"),
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    include_package_data=True,
    install_requires=[],
    python_requires=">=3.9",
)
