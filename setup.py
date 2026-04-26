from setuptools import find_namespace_packages, setup


setup(
    name="context-bridge",
    version="0.2.0",
    description="Developer productivity CLI tool (cb)",
    packages=find_namespace_packages(include=["cli*", "dashboard*", "integrations*", "storage*"]),
    py_modules=["config"],
    include_package_data=True,
    package_data={
        "dashboard": ["templates/*.html"],
    },
    install_requires=[
        "click",
        "requests",
        "rich",
        "flask",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "cb=cli.main:cli",
        ]
    },
    python_requires=">=3.9",
)