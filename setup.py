from setuptools import setup, find_packages

setup(
    name="shroomie",
    version="0.1.0",
    description="A tool for gathering environmental data relevant to mushroom cultivation",
    author="Shroomie Team",
    packages=find_packages(),
    install_requires=[
        "requests",
        "folium",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "shroomie=shroomie.cli.main:main",
        ],
    },
    python_requires=">=3.6",
)