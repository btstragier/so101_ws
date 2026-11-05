import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'hand_tracking'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'models'),
            glob('models/*.task')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='bjorn',
    maintainer_email='btstragier@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'hand_tracking_node = hand_tracking.hand_tracking_node:main',
            'hand_visualizer_node = hand_tracking.hand_visualizer_node:main',
        ],
    },
)
