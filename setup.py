import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="autoscraper",  # Replace with your own username
    version="0.0.1",
    author="Karl Lorey",
    author_email="git@karllorey.com",
    description="Scrape information from HTML automatically",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lorey/autoscraper",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.5",
)
