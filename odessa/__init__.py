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

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

import os
from pyannote.core import Segment, Timeline, Annotation, SlidingWindow
from pyannote.database import Database
from pyannote.database.protocol import SpeakerDiarizationProtocol
from pandas import read_table
from pathlib import Path


# this protocol defines a speaker diarization protocol: as such, a few methods
# needs to be defined: trn_iter, dev_iter, and tst_iter.

class Fullset(SpeakerDiarizationProtocol):
    """My first speaker diarization protocol """

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
                    'annotated': Timeline(uri=uri, segments=annotated_segments[uri]),
                    'annotation': annotation}

                yield current_file

    def dev_iter(self):
        # no development set
        pass

    def trn_iter(self):
        # no train set
        pass


# this is where we define each protocol for this database.
# without this, `pyannote.database.get_protocol` won't be able to find them...

class Odessa(Database):
    """Odessa database of recordings over IP """

    def __init__(self, preprocessors={}, **kwargs):
        super(Odessa, self).__init__(preprocessors=preprocessors, **kwargs)

        # register the first protocol: it will be known as
        # MyDatabase.SpeakerDiarization.MyFirstProtocol
        self.register_protocol(
            'SpeakerDiarization', 'Fullset', Fullset)
