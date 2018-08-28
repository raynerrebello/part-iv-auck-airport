import numpy as np
import simplekml
import math
from coordinates import rect2earth, earth2rect
from location import Location, dist
from geopy.distance import lonlat, distance

tol = 1e-6  # Tolerance in floating point comparisons
SEC_PER_MIN = 60  # Seconds per minute


class Plane(Location):
    def __init__(self, name, lng, lat, class_num, apt, kml, delay_cost=1, speed=13000.0, max_delay=1000, swap_time=10, arr_time=None, pred=None):
        Location.__init__(self, name, lng, lat)

        # Create the folder to store all the KML data
        self.fol = kml.newfolder(name=name)
        self.coord_path = [(lng, lat)]

        self.class_num = class_num
        self.delay_cost = delay_cost
        self.landed = False
        self.speed = speed
        self.max_delay = max_delay
        self.swap_time = swap_time
        self.apt = apt
        self.pred = pred
        self.arr_time = arr_time

        if apt:
            self.eta = self.get_eta()
            if self.pred:
                self.eta += self.pred.eta + 10
        self.delay = 0

        if arr_time != None and arr_time > 1:
            self.arrived = False
        else:
            self.arrived = True

    def step(self, log_name, minute):
        if dist(self, self.apt) + tol >= self.eta * self.speed:
            step = self.speed

            if step <= tol + dist(self, self.apt):
                self.rect += step * \
                    (self.apt.rect - self.rect) / dist(self, self.apt)
            else:
                self.rect = self.apt.rect
                self.landed = True
                with open(log_name, 'a') as file:
                    file.write(self.name+" has landed\n")

            self.lng, self.lat = rect2earth(self.rect)
            self.id_arr = dist(self, self.apt)/self.speed
            self.coord_path.append((self.lng, self.lat))
            self.delay = 0
        else:
            self.set_delay(dist(self, self.apt) /
                           self.speed - self.eta, log_name)

    def update(self, log_name, minute):
        if self.pred:
            pred_landed = self.pred.landed
        else:
            pred_landed = True
        if not self.landed and self.arrived:
            if pred_landed:
                self.step(log_name, minute)
                pt = self.fol.newpoint(name=self.name, coords=[
                                       (self.lng, self.lat)])
                pt.timestamp.when = minute
                ls = self.fol.newlinestring(
                    name=self.name, coords=self.coord_path)
                ls.style.linestyle.width = 2
                ls.timestamp.when = minute

                if self.arrived:
                    if self.delay:
                        ls.style.linestyle.color = simplekml.Color.red
                        pt.style.labelstyle.color = simplekml.Color.red
                    else:
                        ls.style.linestyle.color = simplekml.Color.green
                        pt.style.iconstyle.scale = 0.8
                        pt.style.iconstyle.icon.href = "http://www.iconarchive.com/download/i91814/icons8/windows-8/Transport-Airplane-Mode-On.ico"
            self.eta -= 1
        elif not self.arrived and self.arr_time != None:
            if minute+1 >= self.arr_time:
                self.arrived = True

    def set_delay(self, delay, log_name):
        self.delay = delay
        with open(log_name, 'a') as file:
            file.write(self.name+" is estimated to be delayed by " +
                       str(delay)+" minute(s)\n")

    def get_eta(self):
        return (distance((self.lat, self.lng), (self.apt.lat, self.apt.lng)).meters)/self.speed

# Historical Data


class Arrival(Plane):
    def __init__(self, name, lng, lat, class_num, trail, kml, delay_cost=1, speed=13000.0, max_delay=1000, arr_time=None):
        Plane.__init__(self, name, lng, lat, class_num, None,
                       kml, delay_cost, speed, max_delay, 0, arr_time=arr_time)
        self.final_dest = Location(
            name+" end", trail[0]["lng"], trail[0]["lat"])
        self.id_arr = dist(self, self.final_dest)/self.speed
        self.final_time = trail[0]["ts"]
        self.eta = self.final_time
        self.trail = trail

    @staticmethod
    def get_point(trail, minute):
        for idx, point in enumerate(trail):
            # Step through the points on the trail from the end to the beginning
            if point["ts"]/SEC_PER_MIN <= minute + 1:
                # If the plane has already arrived, then return the point where it arrived.
                if idx == 0:
                    return point
                else:
                    # Otherwise, interpolate between the points on the trail.
                    pt0 = point
                    pt1 = trail[idx-1]

                    return {k: np.interp(minute*SEC_PER_MIN, [pt0["ts"], pt1["ts"]], [pt0[k], pt1[k]]) for k in point}
        # If the plane has not started a trail yet, just return None.
        return None

    def step(self, log_name, minute):
        if self.delay + self.eta <= minute + 1:
            self.landed = True
            self.rect = self.final_dest.rect
            self.lng, self.lat = rect2earth(self.rect)
            with open(log_name, 'a') as file:
                file.write(self.name+" has landed\n")
        else:
            new_point = Arrival.get_point(self.trail, minute+1)
            self.set_delay(dist(self, self.final_dest) /
                           self.speed - self.eta, log_name)
            if new_point:
                self.lng = new_point["lng"]
                self.lat = new_point["lat"]
                self.rect = earth2rect(self.lng, self.lat)
        self.id_arr = dist(self, self.final_dest)/self.speed
        pass
