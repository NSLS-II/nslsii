# interactive use
sd.monitors = []  # a list of signals to monitor concurrently
sd.flyers = []  # a list of "flyable" devices
# a list of devices to read at start and end
sd.baseline = [theta, delta, gamma,
               sx, say, saz, cryoangle,
               sy, sz,
               temp, #uw_temp,
               temp_sp,
               pgm_en,
               epu1, epu2,
               slt1, slt2, slt3,
               m1a, m3a,
               mono_tempa, mono_tempb,  grt1_temp, grt2_temp,
               nanop, tardis]

dets = [sclr] #TODO decide if this is permanent

pgm_en.readback.name = 'energy'

sclr.names.read_attrs=['name1','name2','name3','name4','name5','name6']  # TODO  WHAT IS THIS??? - Dan Allan
sclr.channels.read_attrs=['chan1','chan2','chan3','chan4','chan5','chan6']
sclr.hints = {'fields': ['sclr_ch2', 'sclr_ch3', 'sclr_ch6']}

def relabel_fig(fig, new_label):
    fig.set_label(new_label)
    fig.canvas.manager.set_window_title(fig.get_label())

fccd.hints = {'fields': ['fccd_stats1_total']}
dif_beam.hints = {'fields' : ['dif_beam_stats3_total','dif_beam_stats1_total']}

# This was imported in 00-startup.py
#  used to generate the list: [thing.name for thing in get_all_positioners()]
BlueskyMagics.positioners = [
 cryoangle,
 delta,
 diag2_y,
 diag3_y,
 diag5_y,
 diag6_pid,
 diag6_y,
 epu1.gap,
 epu1.phase,
 epu2.gap,
 epu2.phase,
 es_diag1_y,
 eta,
# flux_in,  #TODO decide if need these and fix the class to one device
# flux_out,
 gamma,
 m1a.z,
 m1a.y,
 m1a.x,
 m1a.pit,
 m1a.yaw,
 m1a.rol,
 m1b1.z,
 m1b1.y,
 m1b1.x,
 m1b1.pit,
 m1b1.yaw,
 m1b1.rol,
 m1b2.z,
 m1b2.y,
 m1b2.x,
 m1b2.pit,
 m1b2.yaw,
 m1b2.rol,
 m3a.x,
 m3a.pit,
 m3a.bdr,
# muR,  # TODO turn this back on when safe
# muT,  # TODO turn this back on when safe
 nanop.tx,
 nanop.ty,
 nanop.tz,
 nanop.bx,
 nanop.by,
 nanop.bz,
 pgm_en,
 say,
 saz,
 slt1.xg,
 slt1.xc,
 slt1.yg,
 slt1.yc,
 slt2.xg,
 slt2.xc,
 slt2.yg,
 slt2.yc,
 slt3.x,
 slt3.y,
 sm.curr,
 sm.volt,
 ssh_in,   #leave for now but decide base on below.
# ssh_out,  #TODO decide if need tehse and fix the class to one device
 sx,
 sy,
 sz,
 tardis.h,
 tardis.k,
 tardis.l,
  tardis.theta,
  tardis.omega,
  tardis.chi,
  tardis.phi,
  tardis.delta,
  tardis.gamma,
 temp_sp,
 theta,
# yag_cube_in,  #TODO decide if need these and fix the class to one device
# yag_cube_out
 ]

