#!/usr/bin/env python
# encoding: utf-8

# The MIT License (MIT)

# Copyright (c) 2017 CNRS

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# AUTHORS
# Hervé BREDIN - http://herve.niderb.fr
# Pavel KORSHUNOV - pavel.korshunov@idiap.ch

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

import os
from pyannote.core import Segment, Timeline, Annotation, SlidingWindow
from pyannote.database import Database
from pyannote.database.protocol import SpeakerDiarizationProtocol
from pyannote.database.protocol import SpeakerSpottingProtocol
from pandas import read_table
from pathlib import Path


# this protocol defines a speaker diarization protocol: as such, a few methods
# needs to be defined: trn_iter, dev_iter, and tst_iter.

class SpeakerDiarization(SpeakerDiarizationProtocol):
    """My first speaker diarization protocol """

    def trn_iter(self):
        # no train set
        pass

    def dev_iter(self):
        # no development set
        pass

    def tst_iter(self):

        # absolute path to 'data' directory where annotations are stored
        data_dir = Path(__file__).parent / 'data' / 'speaker_diarization'

        annotated = data_dir / 'fullset.uem'
        names = ['uri', 'NA0', 'start', 'end']
        annotated = read_table(annotated, delim_whitespace=True, names=names)
        annotated_segments = {}
        for segment in annotated.itertuples():
            annotated_segments[segment.uri] = Segment(start=segment.start, end=segment.end)

        # iterate through the text annotation files
        for filename in os.listdir(data_dir):
            if filename.endswith(".txt"):
                uri, _ = os.path.splitext(os.path.basename(filename))
                annotation = Annotation(uri=uri)

                names = ['start', 'end', 'speaker', 'speakerID']
                parsed_file = read_table(os.path.join(data_dir, filename), delim_whitespace=True, names=names)
                for t, turn in enumerate(parsed_file.itertuples()):
                    segment = Segment(start=turn.start,
                                      end=turn.end)
                    annotation[segment, t] = turn.speakerID

                current_file = {
                    'database': 'Odessa',
                    'uri': uri,
                    'annotated': Timeline(uri=uri, segments=[annotated_segments[uri]]),
                    'annotation': annotation}

                yield current_file


class SpeakerSpotting(SpeakerDiarization, SpeakerSpottingProtocol):


    def trn_iter(self):
        # no train set
        pass

    def dev_iter(self):
        # no development set
        pass

    def tst_iter(self):
        for current_file in super().tst_iter():
            annotated = current_file['annotated']
            annotation = current_file['annotation']

            for segment in annotated:
                sessions = SlidingWindow(start=segment.start,
                                         duration=30., step=30.,
                                         end=segment.end - 3.)

                for session in sessions:
                    session_file = dict(current_file)
                    session_file['annotated'] = annotated.crop(session)
                    session_file['annotation'] = annotation.crop(session)

                    yield session_file

    def dev_enrol_iter(self):
        # no development set
        pass

    def tst_enrol_iter(self):
        # load enrolments
        data_dir = Path(__file__).parent / 'data' / 'speaker_spotting'
        enrolments = data_dir / 'tst.enrol.txt'
        names = ['uri', 'NA0', 'start', 'duration',
                 'NA1', 'NA2', 'NA3', 'model_id']
        enrolments = read_table(enrolments, delim_whitespace=True, names=names)

        for model_id, turns in enrolments.groupby(by=['uri', 'model_id']):

            # gather enrolment data
            segments = []
            uri = ''
            for t, turn in enumerate(turns.itertuples()):
                if t == 0:
                    uri = turn.uri
                segment = Segment(start=turn.start,
                                  end=turn.start + turn.duration)
                if segment:
                    segments.append(segment)
            enrol_with = Timeline(segments=segments, uri=uri)

            current_enrolment = {
                'database': 'Odessa',
                'uri': uri,
                'model_id': model_id[1],  # model_id
                'enrol_with': enrol_with,
            }

            yield current_enrolment

    def dev_try_iter(self):
        # no development set
        pass

    def tst_try_iter(self):
        def get_turns(uri):
            ref_file_path = Path(__file__).parent / 'data' / 'speaker_diarization' / uri
            ref_file_path = Path(str(ref_file_path) + '.txt')
            gt_names = ['start', 'end', 'speaker', 'speakerID']
            return read_table(os.path.join(data_dir, ref_file_path), delim_whitespace=True, names=gt_names)

        diarization = getattr(self, 'diarization', True)

        # load trials
        data_dir = Path(__file__).parent / 'data' / 'speaker_spotting'
        trials = data_dir / 'tst.trial.txt'
        names = ['model_id', 'uri', 'start', 'end', 'target', 'first', 'total']
        trials = read_table(trials, delim_whitespace=True, names=names)

        for trial in trials.itertuples():

            model_id = trial.model_id

            speaker = model_id

            uri = trial.uri

            # trial session
            try_with = Segment(start=trial.start, end=trial.end)

            if diarization:
                # 'annotation' & 'annotated' are needed when diarization is set
                # therefore, this needs a bit more work than when set to False.

                annotation = Annotation(uri=uri)
                turns = get_turns(uri)
                for t, turn in enumerate(turns.itertuples()):
                    segment = Segment(start=turn.start,
                                      end=turn.end)
                    if not (segment & try_with):
                        continue
                    annotation[segment, t] = turn.speakerID

                annotation = annotation.crop(try_with)
                reference = annotation.label_timeline(speaker)
                annotated = Timeline(uri=uri, segments=[try_with])

                # pack & yield trial
                current_trial = {
                    'database': 'Odessa',
                    'uri': uri,
                    'try_with': try_with,
                    'model_id': model_id,
                    'reference': reference,
                    'annotation': annotation,
                    'annotated': annotated,
                }

            else:
                # 'annotation' & 'annotated' are not needed when diarization is
                # set to False -- leading to a faster implementation...
                segments = []
                if trial.target == 'target':
                    turns = get_turns(uri).groupby(by='speakerID')
                    for t, turn in enumerate(turns.get_group(speaker).itertuples()):
                        segment = Segment(start=turn.start,
                                          end=turn.end)
                        segments.append(segment)
                reference = Timeline(uri=uri, segments=segments).crop(try_with)

                # pack & yield trial
                current_trial = {
                    'database': 'Odessa',
                    'uri': uri,
                    'try_with': try_with,
                    'model_id': model_id,
                    'reference': reference,
                }

            yield current_trial


# this is where we define each protocol for this database.
# without this, `pyannote.database.get_protocol` won't be able to find them...

class Odessa(Database):
    """Odessa database of recordings over IP """

    def __init__(self, preprocessors={}, **kwargs):
        super(Odessa, self).__init__(preprocessors=preprocessors, **kwargs)

        # register the first protocol: it will be known as
        # MyDatabase.SpeakerDiarization.MyFirstProtocol
        self.register_protocol(
            'SpeakerDiarization', 'Fullset', SpeakerDiarization)

        self.register_protocol(
            'SpeakerSpotting', 'Fullset', SpeakerSpotting)
