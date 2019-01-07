# ODESSA database plugin for pyannote.database

## Installation

```bash
$ pip install pyannote.db.odessa.ip
```

Tell `pyannote` where to look for Odessa audio files.

```bash
$ cat ~/.pyannote/db.yml
Odessa: /path/to/odessa/audio/original/{uri}.wav
```

## Speaker diarization protocol

Odessa database has only Train and Test sets.

Protocol is initialized as follows:

```python
>>> from pyannote.database import get_protocol, FileFinder
>>> preprocessors = {'audio': FileFinder()}
>>> protocol = get_protocol('Odessa.SpeakerDiarization.Fullset',
...                         preprocessors=preprocessors)
```

### Training

For background training (e.g.
[GMM/UBM](http://www.sciencedirect.com/science/article/pii/S1051200499903615), [i-vector](http://ieeexplore.ieee.org/document/5545402/), or [TristouNet neural embedding](https://arxiv.org/abs/1609.04301)), files of the training set can be
iterated using `protocol.train()`:

```python
>>> for current_file in protocol.train():
...
...     # path to the audio file
...     audio = current_file['audio']
...
...     # "who speaks when" reference
...     reference = current_file['annotation']
...
...     # when current_file has an 'annotated' key, it indicates that
...     # annotations are only provided for some regions of the file.
...     annotated = current_file['annotated']
...     # See http://pyannote.github.io/pyannote-core/structure.html#timeline
...
...     # train...
```

`reference` is a pyannote.core.Annotation. In particular, it can be iterated
as follows:

```python
>>> for segment, _, speaker in reference.itertracks(yield_label=True):
...
...     print('Speaker {speaker} speaks between {start}s and {end}s'.format(
...         speaker=speaker, start=segment.start, end=segment.end))
```
See http://pyannote.github.io/pyannote-core/structure.html#annotation for
details on other ways to use this data structure.


### Test / Evaluation

```python
>>> # initialize evaluation metric
>>> from pyannote.metrics.diarization import DiarizationErrorRate
>>> metric = DiarizationErrorRate()
>>>
>>> # iterate over each file of the test set
>>> for test_file in protocol.test():
...
...     # process test file
...     audio = test_file['audio']
...     hypothesis = process_file(audio)
...
...     # evaluate hypothesis
...     reference = test_file['annotation']
...     uem = test_file['annotated']
...     metric(reference, hypothesis, uem=uem)
>>>
>>> # report results
>>> metric.report(display=True)
```

## Speaker spotting procotol

In order to use the Odessa dataset for the evaluation of speaker spotting systems,
the original speaker diarization training/test split has been
redefined.

Moreover, original files have also been split into shorter sessions in order to
increase the number of trials.

Protocol is initialized as follows:

```python
>>> from pyannote.database import get_protocol, FileFinder
>>> preprocessors = {'audio': FileFinder()}
>>> protocol = get_protocol('Odessa.SpeakerSpotting.Fullset',
...                         preprocessors=preprocessors)
```

### Training

`protocol.train()` can be used like in the speaker diarization protocol above.

### Enrolment

```python
>>> # dictionary meant to store all target models
>>> models = {}
>>>
>>> # iterate over all enrolments
>>> for current_enrolment in protocol.test_enrolment():
...
...     # target identifier
...     target = current_enrolment['model_id']
...     # the same speaker may be enrolled several times using different target
...     # identifiers. in other words, two different identifiers does not
...     # necessarily not mean two different speakers.
...
...     # path to audio file to use for enrolment
...     audio = current_enrolment['audio']
...
...     # pyannote.core.Timeline containing target speech turns
...     # See http://pyannote.github.io/pyannote-core/structure.html#timeline
...     enrol_with = current_enrolment['enrol_with']
...
...     # this is where enrolment actually happens and model is stored
...     models[target] = enrol(audio, enrol_with)
```

The following pseudo-code shows what the `enrol` function could look like:

```python
>>> def enrol(audio, enrol_with):
