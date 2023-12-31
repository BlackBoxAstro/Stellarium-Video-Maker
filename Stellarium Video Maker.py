#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
from datetime import datetime, time, timedelta
from pathlib import Path
import subprocess
import time as xxx
import tempfile
import shutil
from math import cos, sin, acos, asin, tan, degrees as deg, radians as rad  # Import math functions


class sun:
    """
    Calculate sunrise and sunset based on equations from NOAA
    http://www.srrb.noaa.gov/highlights/sunrise/calcdetails.html

    typical use, calculating the sunrise at the present day:

    import datetime
    import sunrise
    s = sun(lat=151.21,long=33.87)
    print('sunrise at ',s.sunrise(when=datetime.datetime.now())
    """

    def __init__(self, lat=151.21, long=-33.87):  # default Sydney, Aus
        self.lat = lat
        self.long = long



    def sunrise(self, when):
        """
        return the time of sunrise as a datetime.time object
        when is a datetime.datetime object. If none is given
        a local time zone is assumed (including daylight saving
        if present)
        """
        self.__preptime(when)
        self.__calc()
        return sun.__timefromdecimalday(self.sunrise_t)

    def sunset(self, when=None):
        self.__preptime(when)
        self.__calc()
        return sun.__timefromdecimalday(self.sunset_t)

    def solarnoon(self, when=None):
        self.__preptime(when)
        self.__calc()
        return sun.__timefromdecimalday(self.solarnoon_t)

    @staticmethod
    def __timefromdecimalday(day):
        """
        returns a datetime.time object.

        day is a decimal day between 0.0 and 1.0, e.g. noon = 0.5
        """
        hours = 24.0 * day
        h = int(hours)
        minutes = (hours - h) * 60
        m = int(minutes)
        seconds = (minutes - m) * 60
        s = int(seconds)
        return time(hour=h, minute=m, second=s)

    def __preptime(self, when):
        """
        Extract information in a suitable format from when,
        a datetime.datetime object.
        """
        # datetime days are numbered in the Gregorian calendar
        # while the calculations from NOAA are distibuted as
        # OpenOffice spreadsheets with days numbered from
        # 1/1/1900. The difference are those numbers taken for
        # 18/12/2010
        self.day = when.toordinal() - (734124 - 40529)
        t = when.time()
        self.time = (t.hour + t.minute / 60.0 + t.second / 3600.0) / 24.0

        self.timezone = 0
        offset = when.utcoffset()
        if not offset is None:
            self.timezone = offset.seconds / 3600.0

    def __calc(self):
        """
        Perform the actual calculations for sunrise, sunset and
        a number of related quantities.

        The results are stored in the instance variables
        sunrise_t, sunset_t and solarnoon_t
        """
        timezone = self.timezone  # in hours, east is positive
        longitude = self.long  # in decimal degrees, east is positive
        latitude = self.lat  # in decimal degrees, north is positive

        time = self.time  # percentage past midnight, i.e. noon  is 0.5
        day = self.day  # daynumber 1=1/1/1900

        Jday = day + 2415018.5 + time - timezone / 24  # Julian day
        Jcent = (Jday - 2451545) / 36525  # Julian century

        Manom = 357.52911 + Jcent * (35999.05029 - 0.0001537 * Jcent)
        Mlong = 280.46646 + Jcent * (36000.76983 + Jcent * 0.0003032) % 360
        Eccent = 0.016708634 - Jcent * (0.000042037 + 0.0001537 * Jcent)
        Mobliq = 23 + (26 + ((21.448 - Jcent * (46.815 + Jcent * (0.00059 - Jcent * 0.001813)))) / 60) / 60
        obliq = Mobliq + 0.00256 * cos(rad(125.04 - 1934.136 * Jcent))
        vary = tan(rad(obliq / 2)) * tan(rad(obliq / 2))
        Seqcent = sin(rad(Manom)) * (1.914602 - Jcent * (0.004817 + 0.000014 * Jcent)) + sin(rad(2 * Manom)) * (
                    0.019993 - 0.000101 * Jcent) + sin(rad(3 * Manom)) * 0.000289
        Struelong = Mlong + Seqcent
        Sapplong = Struelong - 0.00569 - 0.00478 * sin(rad(125.04 - 1934.136 * Jcent))
        declination = deg(asin(sin(rad(obliq)) * sin(rad(Sapplong))))

        eqtime = 4 * deg(
            vary * sin(2 * rad(Mlong)) - 2 * Eccent * sin(rad(Manom)) + 4 * Eccent * vary * sin(rad(Manom)) * cos(
                2 * rad(Mlong)) - 0.5 * vary * vary * sin(4 * rad(Mlong)) - 1.25 * Eccent * Eccent * sin(
                2 * rad(Manom)))

        hourangle = deg(acos(cos(rad(90.833)) / (cos(rad(latitude)) * cos(rad(declination))) - tan(rad(latitude)) * tan(
            rad(declination))))

        self.solarnoon_t = (720 - 4 * longitude - eqtime + timezone * 60) / 1440
        self.sunrise_t = self.solarnoon_t - hourangle * 4 / 1440
    
        # fix for #3, thanks to jmadajian (https://github.com/beltoforion/kalstar/issues/3)
        if self.sunrise_t > 1:
            self.sunrise_t -= 1
        elif self.sunrise_t < 0:
            self.sunrise_t += 1
    
        self.sunset_t = self.solarnoon_t + hourangle * 4 / 1440

        # fix for #3, thanks to jmadajian (https://github.com/beltoforion/kalstar/issues/3)
        if self.sunset_t > 1:
            self.sunset_t -= 1
        elif self.sunset_t < 0:
            self.sunset_t += 1

class StellariumToMpeg:
    def __init__(self, args):
        self.__args = args
        self.__frame_folder = "{0}/kalstar_frames".format(tempfile.gettempdir())
        self.__final_file = self.__frame_folder + "/final.png"

        if os.path.exists(self.__frame_folder):
            shutil.rmtree(self.__frame_folder)

        os.mkdir(self.__frame_folder)

        # Initialize the script here
        self.__script = """

    // Originally by Ingo Berg, this script has been edited and updated by BlackBoxAstro
    // License: Public Domain

    param_frame_folder = "$FRAME_FOLDER$"
    param_az = $AZ$
    param_alt = $ALT$
    param_lat = $LAT$
    param_long = $LONG$
    param_title = "$TITLE$"
    param_date = "$DATE$"
    param_timespan = $TIMESPAN$
    param_fov = $FOV$
    param_dt=$DELTAT$
    
    function makeVideo(date, file_prefix, caption, hours, long, lat, alt, azi)
    {
        core.setDate(date, "utc");
        core.setObserverLocation(long, lat, 425, 1, "Freiberg", "Earth");
        core.wait(0.5);

        core.moveToAltAzi(alt, azi)
        core.wait(0.5);

        label = LabelMgr.labelScreen(caption, 70, 40, false, 40, "#aa0000");
        LabelMgr.setLabelShow(label, false); 

        labelTime = LabelMgr.labelScreen("", 70, 90, false, 25, "#aa0000");
        LabelMgr.setLabelShow(labelTime, false); 

        core.wait(0.5);

        max_sec = hours * 60 * 60
        for (var sec = 0; sec < max_sec; sec += param_dt) {
            core.setDate('+' + param_dt + ' seconds');
            LabelMgr.setLabelText(labelTime, core.getDate(""));
            core.wait(0.1);
            core.screenshot(file_prefix);
        }

        LabelMgr.deleteAllLabels();
    }

    core.setTimeRate(0); 
    core.setGuiVisible(false);

    MilkyWay.setFlagShow(true); //Sets whether to show the Milky Way.
    MilkyWay.setIntensity(1); //Set Milky Way intensity. Stellarium default value: 1.

    SolarSystem.setFlagPlanets(true); //Set flag which determines if planets are drawn or hidden.
    SolarSystem.setFlagLabels(false); //Set flag which determines if planet labels are drawn or hidden.
    //SolarSystem.setMoonScale(6); //Set the display scaling factor for Earth's moon.
    SolarSystem.setFlagMoonScale(false); //Set flag which determines if Earth's moon is scaled or not.
    SolarSystem.setFontSize(10); //Set planet names font size.
    
    //StelSkyDrawer.setAbsoluteStarScale(1.5); //Set the absolute star brightness scale.
    //StelSkyDrawer.setRelativeStarScale(1.65); //Set the way brighter stars will look bigger as the fainter ones.

    StarMgr.setFontSize(20); //Define font size to use for star names display.
    StarMgr.setLabelsAmount(0); //Set the amount of star labels between 0 and 10. 0 is no labels, 10 is maximum of labels

    ConstellationMgr.setFlagLines(false); //Set whether constellation art will be displayed.
    ConstellationMgr.setFlagLabels(false); //Set whether constellation names will be displayed.
    ConstellationMgr.setArtIntensity(0.1); //Set constellation maximum art intensity (between 0 and 1) Note that the art intensity is linearly faded out if the FOV is in a specific interval, which can be adjusted 
    ConstellationMgr.setFlagArt(false); //Set whether constellation art will be displayed.
    ConstellationMgr.setFlagBoundaries(false); //Set whether constellation boundaries lines will be displayed.
    ConstellationMgr.setConstellationLineThickness(1); //Set the thickness of lines of the constellations.
    ConstellationMgr.setFontSize(3); //Set the font size used for constellation names display.

    LandscapeMgr.setCurrentLandscapeName("Hurricane Ridge"); //Change the current landscape to the landscape with the ID specified. 
    LandscapeMgr.setFlagAtmosphere(false); //Set flag for displaying Atmosphere.

    StelMovementMgr.zoomTo(param_fov, 0); //Change the zoom level.
    core.wait(0.5);

    makeVideo(param_date, "frame_", param_title, param_timespan, param_long, param_lat, param_alt, param_az)
    core.screenshot("final", invert=false, dir=param_frame_folder, overwrite=true);
    core.setGuiVisible(true);
    core.quitStellarium();"""
        
    def __addSecs(self, tm, secs):
        fulldate = datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
        fulldate = fulldate + timedelta(seconds=secs)
        return fulldate.time()

    def create_script(self):
        s = sun(lat=self.__args['lat'], long=self.__args['long'])
        sunset_time = s.sunset(self.__args['date'])
        sunset_time = self.__addSecs(sunset_time, 3600)
        sunset_date = "{0}T{1}".format(self.__args['date'].strftime("%Y-%m-%d"), sunset_time.strftime("%H:%M:%S"))

        script = self.__script
        script = script.replace("$FRAME_FOLDER$", self.__frame_folder)
        script = script.replace("$LAT$", str(self.__args['lat']))
        script = script.replace("$LONG$", str(self.__args['long']))
        script = script.replace("$TITLE$", str(self.__args['title']))
        script = script.replace("$DATE$", sunset_date)
        script = script.replace("$TIMESPAN$", str(self.__args['timespan']))
        script = script.replace("$FOV$", str(self.__args['fov']))
        script = script.replace("$DELTAT$", str(self.__args['dt']))
        script = script.replace("$AZ$", str(self.__args['az']))
        script = script.replace("$ALT$", str(self.__args['alt']))

        with open("/Applications/Stellarium.app/Contents/Resources/scripts/kalstar.ssc", "w") as file:
            file.write(script)

    def create_frames(self):
        proc_stellarium = subprocess.Popen(['/Applications/Stellarium.app/Contents/MacOS/stellarium', '--startup-script', 'kalstar.ssc', '--screenshot-dir', self.__frame_folder], stdout=subprocess.PIPE)

        s = 0
        timeout = 600
        while not os.path.exists(self.__final_file) and s < timeout:
            xxx.sleep(1)
            s = s + 1

        proc_stellarium.kill()

    def create_video(self):
        ffmpeg_path = "/opt/homebrew/bin/ffmpeg" ##Default for MacOS. If using another operating system, please change this path.
        proc = subprocess.Popen([ffmpeg_path,
                                 '-y',
                                 '-r', str(self.__args['fps']),
                                 '-f', 'image2',
                                 '-s', '1920x1080',
                                 '-i', '{0}/frame_%03d.png'.format(self.__frame_folder),
                                 '-crf', '12',
                                 '-pix_fmt', 'yuv420p',
                                 self.__args['outfile']], stdout=subprocess.PIPE)
        proc.communicate()

        # Check if 'show_video' key exists and is True
        if self.__args.get('show_video', False):
            vlc_path = '/Applications/VLC.app/Contents/MacOS/VLC' ##Default for MacOS. If using another operating system, please change this path.
            subprocess.Popen([vlc_path, '--repeat', self.__args['outfile']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, close_fds=True)

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

def positive_number(x):
    x = float(x)
    if x < 0.0:
        raise argparse.ArgumentTypeError("%r is negative"%(x,))
    return x

def get_next_monday():
    today = datetime.now()
    days_ahead = 0 if today.weekday() == 0 else 7 - today.weekday()
    next_monday = today + timedelta(days=days_ahead)
    return next_monday.strftime("%Y-%m-%d")

def prompt_for_arguments():

    print('Stellarium Video Maker by BlackBoxAstro')
    print('Built on Kalstar by Beltoforion')
    print('  ')
    print('----------------------------------------')
    print('  ')
    accept_defaults = input("Do you want to accept all default options? (Yes/No) [default: Sydney, Next Monday, Full sky pointed straight up for 12 hours]: ").strip().lower() or "yes"
    

    script_directory = os.path.dirname(os.path.realpath(__file__))
    default_outfile_name = "output_video.mp4"  # You can set a default file name here
    default_outfile_path = os.path.join(script_directory, default_outfile_name)

    if accept_defaults == "yes":
        default_date = get_next_monday()
        return {
            'long': 151.2093,
            'lat': -33.8688,
            'alt': 90,
            'az': 90,
            'date': datetime.strptime(default_date, "%Y-%m-%d"),
            'fps': 30,
            'fov': 360,
            'title': "--",  # You might want to set a sensible default title
            'timespan': 12,
            'dt': 10,
            'outfile': default_outfile_path,
            'show_video': True
        }
    else:
        long = input("Enter Longitude (default: 151.2093): ") or 151.2093
        lat = input("Enter Latitude (default: -33.8688): ") or -33.8688
        alt = input("Enter Altitude (default: 90): ") or 90
        az = input("Enter Azimuth (default: 90): ") or 90
        default_date = get_next_monday()
        date_input = input(f"Enter Date (format YYYY-MM-DD, default: {default_date}): ") or default_date
        try:
            date = datetime.strptime(date_input, "%Y-%m-%d")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
            return prompt_for_arguments()  # Recursively prompt for correct input

        fps = input("Enter Frames Per Second (default: 30): ") or 30
        fov = input("Enter Field of View (default: 360): ") or 360
        title = input("Enter Title: ")
        timespan = input("Enter TimeSpan (default: 12): ") or 12
        dt = input("Enter DeltaT (default: 10): ") or 10
        outfile = input("Enter Outfile (or leave blank for default naming): ")
        show_video_input = input("Show video after rendering? (yes/no) [default: yes]: ").strip().lower() or "yes"
        show_video = show_video_input == 'yes'

    return {
        'long': float(long),
        'lat': float(lat),
        'alt': float(alt),
        'az': float(az),
        'date': date,
        'fps': float(fps),
        'fov': float(fov),
        'title': title,
        'timespan': float(timespan),
        'dt': float(dt),
        'outfile': outfile,
        'show_video': show_video  # Add the show_video key to the dictionary
    }

def main():
    user_args = prompt_for_arguments()

    if not user_args['outfile']:
        script_directory = os.path.dirname(os.path.realpath(__file__))
        formatted_date = user_args['date'].strftime("%Y_%m_%d")
        formatted_lat = "{:.3f}".format(user_args['lat'])
        formatted_long = "{:.3f}".format(user_args['long'])
        user_args['outfile'] = os.path.join(script_directory, f"{formatted_date}_{formatted_lat}_{formatted_long}.mp4")

    print('-------------------------------------------')
    print(f'Running')


    if not os.path.isdir('/Applications/Stellarium.app'): ##default for macOS. change if on another OS.
        print('Stellarium does not seem to be installed!')

    scripts_dir = '/Applications/Stellarium.app/Contents/Resources/scripts' ##change stellarium location here. This should be the default location if you are on a Mac. 
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)

    sa = StellariumToMpeg(user_args)
    sa.create_script()
    sa.create_frames()
    sa.create_video()

if __name__ == "__main__":
    main()
