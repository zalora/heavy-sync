#!/usr/bin/env python

from distutils.core import setup
from os.path import join

setup(name='heavy-sync',
      version='0.1',
      description='Synchronize huge cloud buckets with ease',
      author='Hoang Xuan Phu',
      author_email='phu.hoang@zalora.com',
      url='https://github.com/zalora/heavy-sync',
      packages=['heavy-sync'],
      install_requires=['boto', 'gcs-oauth2-boto-plugin'],
      scripts=[
          join('heavy-sync', 'heavy-check'),
          join('heavy-sync', 'heavy-sync'),
      ],
)
