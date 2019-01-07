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

Odessa database has only Test set for all the protocols.

## Speaker diarization protocol


Protocol is initialized as follows:

```python
>>> from pyannote.database import get_protocol, FileFinder
>>> preprocessors = {'audio': FileFinder()}
>>> protocol = get_protocol('Odessa.SpeakerDiarization.Fullset',
...                         preprocessors=preprocessors)
```

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

Protocol is initialized as follows:

```python
>>> from pyannote.database import get_protocol, FileFinder
>>> preprocessors = {'audio': FileFinder()}
>>> protocol = get_protocol('Odessa.SpeakerSpotting.Fullset',
...                         preprocessors=preprocessors)
```

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
