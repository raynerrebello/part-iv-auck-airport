import numpy as np
import simplekml
import os
import math
from subprocess import DEVNULL, STDOUT, check_call
from solve import solve
from visualize import visualize,gantt
from location import Location, dist, Landmark
from plane import Plane
from loaddata import loadplane, loadsep

solver_name = "mip"
log_name = "log.txt"
plot_during = False
plot_after = True
is_manual = True  # Manual data entry or not

# File
kml = simplekml.Kml()
# AKL airport
akl = Landmark("Auckland Airport", 174.779962, -37.013383, 4000, kml)
plane = loadplane(kml, is_manual)
sep_t = loadsep(kml)

# Number of minutes to solve at
skip = 50

minute = 0
sch = []
endtimes = []
name_list = []
while not all([pl.landed for pl in plane]):
    with open(log_name, 'a') as f:
        f.write("Minute "+str(minute)+": \n")
        if (minute % skip == 0):
            valid = [pl for pl in plane if not pl.landed and pl.arrived]
            eta = [pl.eta for pl in valid]
            delay_cost = [pl.delay_cost for pl in valid]
            max_delay = [pl.max_delay for pl in valid]
            class_num = [pl.class_num for pl in valid]
            depends = [valid.index(pl.pred)+1 if pl.pred and not pl.pred.landed else 0 for pl in valid]
            proc_t = [[sep_t[i.class_num-1, k.class_num-1] if i.name != k.name else 0 for k in valid] for i in valid]
            names = [pl.name for pl in valid]
            if valid:
                schedule,endtime = solve(eta, delay_cost, max_delay,class_num, proc_t, sep_t, depends, solver_name)
                sch.append(schedule)
                endtimes.append(endtime)
                name_list.append(names)
                for pl,sched in zip(valid,schedule):
                    if not pl.pred:
                        pl.eta = sched

        for pl in plane:
            pl.update(log_name, minute)

    minute += 1

    # Visualize the kml file
    if plot_during:
        visualize(kml)
if plot_after:
    visualize(kml)
gantt(sch,endtimes,name_list,skip) 


