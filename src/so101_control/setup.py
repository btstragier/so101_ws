from setuptools import find_packages, setup

package_name = 'so101_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='bjorn',
    maintainer_email='btstragier@gmail.com',
    description='A package to publish control commands for the so101 robot',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [ 'sine_mover = so101_control.sine_mover:main',
                             "fk_monitor = so101_control.fk_monitor:main",
        ],
    },
)
