from setuptools import setup, find_packages

setup(
    name="spy-imsicd",
    version="1.0.0",
    author="SPY-IMSICD",
    description="IMSI Catcher Detector for GSM/LTE networks",
    packages=find_packages(),
    install_requires=[
        "click",
        "pyserial",
        "requests",
        "plyer",
        "python-telegram-bot",
    ],
    entry_points={
        "console_scripts": [
            "spy-imsicd=spy_imsicd.cli:cli",
        ],
    },
)
