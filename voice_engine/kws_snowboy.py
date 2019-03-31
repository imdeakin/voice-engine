# -*- coding: utf-8 -*-

"""
Keyword spotting using snowboy
"""

import os
import sys
import threading

if sys.version_info[0] < 3:
    import Queue as queue
else:
    import queue

from snowboy import snowboydetect

from .element import Element


class KWS(Element):
    def __init__(self, model='snowboy', sensitivity=0.5, verbose=False):
        super(KWS, self).__init__()

        self.verbose = verbose

        resource_path = os.path.join(os.path.dirname(snowboydetect.__file__), 'resources')
        common_resource = os.path.join(resource_path, 'common.res')

        tm = type(model)
        ts = type(sensitivity)
        if tm is not list:
            model = [model]
        if ts is not list:
            sensitivity = [sensitivity]

        models = []
        for model_path in [resource_path, os.path.join(resource_path, 'models')]:
            for model_name in model:
                if model == 'alexa':
                    alexa_model = os.path.join(resource_path, 'alexa', 'alexa_02092017.umdl')
                    if os.path.isfile(alexa_model):
                        models.append(alexa_model)
                else:
                    builtin_model = os.path.join(model_path, '{}.umdl'.format(model_name))
                    if os.path.isfile(builtin_model):
                        models.append(builtin_model)
        model_str = ','.join(models)

        print("KWS============KWS===============KWS============KWS==========KWS");
        self.detector = snowboydetect.SnowboyDetect(common_resource.encode(), model_str.encode())

        self.num_hotwords = self.detector.NumHotwords()

        if self.num_hotwords > 1 and len(sensitivity) == 1:
            sensitivity = sensitivity*self.num_hotwords
        if len(sensitivity) != 0:
            assert self.num_hotwords == len(sensitivity), \
                "number of hotwords in decoder_model (%d) and sensitivity " \
                "(%d) does not match" % (self.num_hotwords, len(sensitivity))
        sensitivity_str = ",".join([str(t) for t in sensitivity])
        if len(sensitivity) != 0:
            self.detector.SetSensitivity(sensitivity_str.encode())

        # self.detector.SetAudioGain(1)
        # self.detector.ApplyFrontend(True)
        # self.detector.SetSensitivity(str(sensitivity).encode())

        self.queue = queue.Queue()
        self.done = False
        self.thread = None

        self.on_detected = None

    def put(self, data):
        self.queue.put(data)

    def start(self):
        self.done = False
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.done = True
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)

    def run(self):
        while not self.done:
            try:
                data = self.queue.get(timeout=1)
            except queue.Empty:
                break

            ans = self.detector.RunDetection(data)
            if ans > 0:
                if callable(self.on_detected):
                    self.on_detected(ans)

            if self.verbose:
                sys.stdout.write(str(ans+2))
                sys.stdout.flush()
            super(KWS, self).put(data)

    def set_callback(self, callback):
        self.on_detected = callback


def main():
    import time
    from voice_engine.source import Source

    src = Source()
    kws = KWS()

    src.link(kws)

    def on_detected(keyword):
        print('found {}'.format(keyword))

    kws.on_detected = on_detected

    kws.start()
    src.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    kws.stop()
    src.stop()


if __name__ == '__main__':
    main()
