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
# Pavel KORSHUNOV - pavel.korshunov@idiap.ch

"""
Generate speaker spotting protocols for Odessa database. Enroll files and Test files can be generated.

Usage:
    prepare-spkspt-protocol enroll [options] <data_dir>
    prepare-spkspt-protocol test [options] <data_dir>
    prepare-spkspt-protocol -h | --help
    prepare-spkspt-protocol --version

Common options:
    -o, --output_file STR   Name of the protocol file.
                            [Default: out.txt]
"enroll" mode:
    <data_dir>              Set the input directory where the enrollment annotation files are.

"test" mode:
    -t, --trial-length INT  The trial length in seconds. Trials are the segments, in which all utterances will be split.
                            [Default: 30]
    <data_dir>              Set the input directory where the test annotation files are.
"""
from ._version import get_versions

__version__ = get_versions()['version']
del get_versions

import os
import numpy
from docopt import docopt
from pandas import read_table
from pyannote.core import Segment, Timeline, Annotation


def read_annotaitons(data_dir):
    annotations = []
    speakers = {}
    max_length = 0
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

                if max_length < turn.end: max_length = turn.end
                speakers[turn.speakerID] = turn.speakerID

            annotations.append(annotation)
    return annotations, max_length, speakers


def write_enroll_file(data_dir, output_file):
    annotations, _, _ = read_annotaitons(data_dir)
    with open(output_file, 'w') as f:
        for annotation in annotations:
            for segment, track, label in annotation.itertracks(yield_label=True):
                f.write('{0} 1 {1:0.3f} {2:0.5f} speaker NA NA {3}\n'.format(annotation.uri,
                                                                             segment.start,
                                                                             segment.duration,
                                                                             label))


def write_test_file(data_dir, output_file, trial_length):
    annotations, max_length, speakers = read_annotaitons(data_dir)
    # create an artificial non-overlapping segments each of the trial_length size
    trial_segments = Timeline()
    for i in range(0, int(max_length) // trial_length):
        trial_segments.add(Segment(start=i*trial_length, end=(i+1)*trial_length))

    with open(output_file, 'w') as f:
        for label in speakers.keys():
            for annotation in annotations:
                # make sure our trial segments are not extending beyond the total length of the speech data
                support = annotation.get_timeline().extent()
                # we consider smaller segment here to make sure an embedding of 3 seconds can be computed
                adjusted_trial_segments = trial_segments.crop(Segment(start=support.start, end=support.end - 3.),
                                                              mode='loose')
                uri = annotation.uri
                cur_timeline = annotation.label_timeline(label, copy=False)
                for trial_segment in adjusted_trial_segments:
                    cropped_speaker = cur_timeline.crop(trial_segment, mode='intersection')
                    if not cropped_speaker:
                        f.write('{0} {1} {2:0>7.2f} {3:0>7.2f} nontarget - -\n'.format(
                            label,
                            uri,
                            trial_segment.start,
                            trial_segment.end))
                    else:
                        f.write('{0} {1} {2:0>7.2f} {3:0>7.2f} target {4:0>7.2f} {5:0>7.2f}\n'.format(
                            label,
                            uri,
                            trial_segment.start,
                            trial_segment.end,
                            cropped_speaker[0].start,
                            cropped_speaker[0].duration))


def main():
    arguments = docopt(__doc__, version='Prepare protocol files for Odessa database')

    data_dir = arguments['<data_dir>']
    output_file = arguments['--output_file']

    if arguments['enroll']:
        write_enroll_file(data_dir, output_file)
    if arguments['test']:
        write_test_file(data_dir, output_file, int(arguments['--trial-length']))
