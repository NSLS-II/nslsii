***************
Release History
***************

v0.10.3 (2024-06-28)
====================

* Add additional property 'type' to sync-experiment, requested by SRX.
* Add pmac kill device signal to delta tau motor controls.

v0.10.2 (2024-05-31)
====================

* Add a CLI tool to get IOC hostname for a given PV
* Add more proposal info to sync-experiment tool
* Support running nslsii.start_experiment as CLI

v0.10.1 (2024-05-30)
====================
* rename sync-redis to sync-experiment

v0.10.0 (2024-05-29)
====================
* add a utility to start/switch beamline experiment

v0.9.1 (2023-06-08)
====================
* add optional call_returns_result parameter to be propagated to the RunEngine
* add an ophyd class for a webcam streaming to a URL (Axis cameras)
* update data handling for flyscaning with Xspress3

v0.9.0 (2023-01-20)
===================
* fix incorrect usage of ``prefix=`` keyword argument in tests 
* add ``nslsii.areadetector.xspress3.Xspress3ExternalFileReference.dtype_str``

v0.8.0 (2022-12-19)
===================
* add ophyd classes for QEPro spectrometer IOC
* rationalize global key names for ``nslsii.md_dict.RunEngineRedisDict``
* add time series and units PVs to ``nslsii.areadetector.xspress3``
* add external file reference class to ``nslsii.areadetector.xspress3``
* add hdf5 plugin class to ``nslsii.areadetector.xspress3``

v0.7.0 (2022-08-05)
===================
* support for new sections in the Kafka configuration file
* simplified Kafka docker-compose script

v0.6.0 (2022-07-22)
===================
* improvements to ``nslsii.md_dict.RunEngineRedisDict``

v0.5.0 (2022-06-28)
===================
* add ``nslsii.md_dict.RunEngineRedisDict``

v0.4.0 (2022-04-05)
===================
* simplify ``nslsii.areadetector.xspress3`` component hierarchy (API change)
* replace deprecated IPython ``magic()`` calls with ``run_line_magic()``
* correction to documentation for ``nslsii.configure_base``

v0.3.2 (2022-01-20)
===================
* add a srx resource transform

v0.3.1 (2022-01-13)
===================
* fix a Kafka configuration bug in ``nslsii.configure_base``

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
