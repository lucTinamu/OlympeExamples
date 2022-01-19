#!/usr/bin/env python

# NOTE: Line numbers of this example are referenced in the user guide.
# Don't forget to update the user guide after every modification of this example.

import time
import csv
import math
import os
import queue
import shlex
import subprocess
import tempfile
import threading

import olympe
from olympe.messages.ardrone3.Piloting import TakeOff, Landing
from olympe.messages.ardrone3.Piloting import moveBy
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged
from olympe.messages.ardrone3.PilotingSettings import MaxTilt
from olympe.messages.ardrone3.GPSSettingsState import GPSFixStateChanged


olympe.log.update_config({"loggers": {"olympe": {"level": "WARNING"}}})

#DRONE_IP = os.environ.get("DRONE_IP", "10.202.0.1")
# use real drone to create memory leak
DRONE_IP = "192.168.42.1"
DRONE_RTSP_PORT = os.environ.get("DRONE_RTSP_PORT")


class StreamingExample:
    def __init__(self):
        # Create the olympe.Drone object from its IP address
        self.drone = olympe.Drone(DRONE_IP)
        
        self.frame_queue = queue.Queue()
        self.flush_queue_lock = threading.Lock()

        # separate thread to process frame_queue:
        self.processQueueThread = threading.Thread(name='processQueueThread',
                                                   target=self.processLatestFrame,
                                                   daemon=True)
        self.processQueueThread.start()

    def start(self):
        # Connect the the drone
        self.drone.connect()

        if DRONE_RTSP_PORT is not None:
            self.drone.streaming.server_addr = f"{DRONE_IP}:{DRONE_RTSP_PORT}"

        # Setup your callback functions to do some live video processing
        self.drone.streaming.set_callbacks(
            raw_cb=self.yuv_frame_cb,
            h264_cb=None,
            start_cb=self.start_cb,
            end_cb=self.end_cb,
            flush_raw_cb=self.flush_cb,
        )

        # Start video streaming
        self.drone.streaming.start()
        # self.renderer = PdrawRenderer(pdraw=self.drone.streaming)

    def stop(self):
        # Properly stop the video stream and disconnect
        self.drone.streaming.stop()
        self.drone.disconnect()


    def processLatestFrame(self):
        while True:
            nrOfFrames = self.frame_queue.qsize()
            for frameIdx in range(nrOfFrames):
                frame = self.frame_queue.get(block=True, timeout=None)
                frame.unref()


    def yuv_frame_cb(self, yuv_frame):
        """
        This function will be called by Olympe for each decoded YUV frame.

            :type yuv_frame: olympe.VideoFrame
        """
        yuv_frame.ref()
        self.frame_queue.put_nowait(yuv_frame)

    def flush_cb(self, stream):
        if stream["vdef_format"] != olympe.VDEF_I420:
            return True
        with self.flush_queue_lock:
            while not self.frame_queue.empty():
                self.frame_queue.get_nowait().unref()
        return True

    def start_cb(self):
        pass

    def end_cb(self):
        pass


def test_streaming():
    streaming_example = StreamingExample()
    # Start the video stream
    streaming_example.start()

    time.sleep(1000)

    # Stop the video stream
    streaming_example.stop()


if __name__ == "__main__":
    test_streaming()
