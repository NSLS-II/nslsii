from bluesky.suspenders import (SuspendBoolHigh,
                                SuspendBoolLow,
                                SuspendFloor,
                                SuspendCeil,
                                SuspendInBand,
                                SuspendOutBand)

## Enable this line for standard GU operation
print('\n\nEnabling ring current suspender with 200 mA threshold and 120 s recovery time\n\n')
ring_suspender = SuspendFloor(EpicsSignal('XF:23ID-SR{}I-I'), 200, sleep=120)

# Enable this line for low current modes, decay, parasitic operations ..
#print('\n\nWARNING: special operation mode, enabling ring current suspender with 15 mA threshold and 120 s recovery time.\n\n')
#ring_suspender = SuspendFloor(EpicsSignal('XF:23ID-SR{}I-I'), 15, sleep=120)

# Enable this line for low current modes, decay, parasitic operations ..
print('Enabling FE shutter suspender with 15*60 s recovery time\n\n')
fe_shut_suspender = SuspendBoolHigh(EpicsSignal('XF:23ID-PPS{Sh:FE}Pos-Sts'), sleep=30*60)

#test_shutsusp = SuspendBoolHigh(EpicsSignal('XF:23IDA-EPS{DP:1-Sh:1}Pos-Sts'), sleep=5)

# Enable this line for CSX2 closing our PSh:1
print('Preparing CSX1 Photon Shutter 1 suspender with 3*60 s recovery time\n\tRE.install_suspender(ps1_shut_suspender) to enable.\n')
ps1_shut_suspender =  SuspendBoolHigh(EpicsSignal('XF:23IDA-PPS:1{PSh}Pos-Sts'),sleep=3*60)


## It needs:
## RE.install_suspender(test_shutsusp)
## RE.remove_suspender(test_shutsusp)

#RE.install_suspender(ring_suspender)
#RE.install_suspender(fe_shut_suspender)
#RE.install_suspender(ps1_shut_suspender)

