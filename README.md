# NSLS-II-Tools

Repository of tools used for both data collection and analysis at NSLS-II. Items here
arew either specific to a beamline program (such as CSX-1) or common to all beamlines. 

For an overview of the NSLS-II software see the [NSLS2 software overview](http://nsls-ii.github.io).

## Directory Structure

The layout of the package is as:

```
.
├── LICENSE
├── MANIFEST.in
├── nsls2tools
│   ├── common
│   │   ├── __init__.py
│   │   └── ipynb
│   │       ├── animation.py
│   │       ├── info.py
│   │       ├── __init__.py
│   │       └── nbviewer.py
│   ├── csx1
│   │   ├── analysis
│   │   │   └── __init__.py
│   │   ├── bluesky
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   └── ophyd
│   │       └── __init__.py
│   ├── __init__.py
│   ├── six
│   │   └── __init__.py
│   └── _version.py
├── README.md
├── setup.cfg
├── setup.py
└── versioneer.py
```

Code should be separated into code which is specific to a beamline (Such as CSX-1) and 
code which is common. Within these modules (directories) there should be sub modules
for each use, such as `ipynb` for ipython notebook utilities and `bluesky` for bluesky plans
and config. 
