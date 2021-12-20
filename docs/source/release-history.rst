***************
Release History
***************

v0.3.0 (2021-12-20)
===================
* add Kafka configuration parameters and support to ``nslsii.configure_base``

v0.2.2 (2021-12-08)
===================
* add the ``bec_derivative`` kwarg to ``nslsii.configure.base``
* add GitHub Action workflow to publish to PyPI automatically

v0.2.1 (2021-08-27)
===================
* reinstate ``bluesky_kafka`` conditional import with tests
* add GitHub Action for CI

v0.2.0 (2021-08-24)
===================
* updated documentation for beamline RunEngine Kafka topic names
* import ``bluesky_kafka`` only when needed in ``nslsii.configure_base``
* resolved an issue with importing ``nslsii.iocs``
* improved exception handling when bluesky documents are published as Kafka messages
* send beamline log output to syslog
* added ``nslsii.areadetector.xspress3`` to support APS Xspress3 IOC

v0.1.3 (2021-03-29)
===================
* added environment variable for kafka bootstrap servers
* change bluesky kafka topic naming scheme

v0.1.2 (2021-01-26)
===================
* fix the ``TwoButtonShutter`` class to be compatible with ophyd 1.6.0+
* added log propagation configuration to reduce log noise

v0.1.1 (2020-10-26)
===================
* update manifest and license files
* make minimal traceback reporting optional
* changes to allow 'nslsii' to load without IPython
* update the status of the xspress3 detector on unstaging

v0.1.0 (2020-09-04)
===================
* synchronize xspress3 code with hxntools
* new TwoButtonShutter configuration
* change Signal.value to Signal.get()
* handle Kafka exceptions

v0.0.17 (2020-08-06)
====================
* update the function that subscribes a Kafka producer to the RunEngine

v0.0.16 (2020-06-26)
====================
* create the default logging directory if it does not exist

v0.0.15 (2020-06-16)
====================
* use appdirs to determine default logging directory
* add a function to subscribe a Kafka producer to the RunEngine

v0.0.10 (2019-06-06)
====================

Features
--------
* Add EPSTwoStateIOC class for simulation
