from setuptools import setup

setup(name='fbns_mqtt',
      version='1.0.0',
      description='Instagram FBNS notification receiver',
      url='https://github.com/Sovetnikov/fbns_mqtt',
      author='Artem Sovetnikov',
      author_email='asovetnikov@gmail.com',
      packages=['fbns_mqtt', ],
      package_dir={'fbns_mqtt': 'src'},
      entry_points={
      },
      install_requires=[
          'gmqtt',
          'thriftpy',
      ],
      include_package_data=True,)
