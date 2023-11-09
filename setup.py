from setuptools import setup

reqs = []

with open("requirements.txt", "r") as f:
    line = f.readline().rstrip("\n")
    while line:
        reqs.append(line)
        line = f.readline().rstrip("\n")

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="jsonlog",
    version="0.3.1",
    packages=[
        "jsonlog",
    ],
    install_requires=reqs,
    author="Craig Robinson",
    author_email="craig@permutable.ai",
    long_description=long_description,
    python_requires=">=3",
)
