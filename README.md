# Stellarium-Video-Maker

Automatically creating videos of the night sky with Stellarium.

This script  will automate the process of creating videos of the night sky with stellarium. It will take an observation position and other observation parameters (you can use the default options or input your own parameters when prompted) and then create a script for Stellarium's built in scripting engine to compute the animation frames for the given date. Once the frames are created the script will invoke ffmpeg to combine the frames into an mp4 video file.

Prerequisites:
In order to use this script Stellarium, ffmpeg and VLC must be installed. The filepaths used are for MacOS, however I have commented where they will need to be changed if you are on another OS. 

Acknowledgements:
This script was based on the Kalstar script written by Beltoforion (https://github.com/beltoforion/kalstar). 
