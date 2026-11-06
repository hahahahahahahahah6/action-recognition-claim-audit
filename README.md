# Documentation claim auditor

Offline, deterministic, standard-library-only inspection of documentation about
naming what a person is doing in a clip. Requires Python 3.9 or later. No network,
telemetry, model execution, or file writes are performed.

## Usage

```sh
python3 -m pip install .
action-recognition-claim-audit audit .
python3 -m action_recognition_claim_audit audit . --json
action-recognition-claim-audit audit . --verbose --ignore vendor/ --ignore examples/
action-recognition-claim-audit audit . --fail-on medium
action-recognition-claim-audit --version
```

The repository defaults to the current directory. Exit status is 0 when no
finding reaches the threshold, 2 when one does, and 1 for usage or IO errors.
The default threshold is high. JSON emits a list of findings with id, severity,
path, verdict, message, and phrases. Verbose scope and per-file decisions go to
standard error. Repeatable ignore prefixes match repository-relative paths.

## Scope and rules

Scans the root README and Markdown below docs. Claims in files under a tests
directory receive medium severity. Python sources are inspected throughout the
repository, excluding version control, bytecode caches, virtual environments,
and build output. Each evidence route must be complete in one module. Imported
aliases, simple assigned aliases, and chained calls are supported. Local function
and class definitions shadow imported names. Unparseable modules supply no evidence.

Fenced code is excluded; inline code counts as prose. Matching uses exact,
case-insensitive substrings without stemming or hyphen normalization. Denial
spans are removed first. Longest-first matching blanks spans so each occurrence
matches once under its longest phrase. A claim without evidence is high severity;
a denial contradicted by evidence is high severity. A denial without evidence
passes. Findings use these identifiers:

```text
documented-action-recognition-claim-false
documented-no-action-recognition-claim-false
```

## Differentiation

The first neighbor checks finding objects in a frame, the second estimates joint
positions, and the third follows a subject across frames:

```text
object-detection-claim-audit
pose-claim-audit
tracking-claim-audit
```

This auditor checks naming what a person is doing across frames. Those neighboring
capabilities alone do not establish the checked feature.

## Evidence and limitations

Static pattern matching is not semantic judgement. Exact phrases miss restatements.
Generic calls on unrelated objects count because their method names are shared:

```python
unrelated.recognize_action()
```

A bare generic call needs a matching from-import. Video factories below require
construction plus a forward or direct call on the returned instance, assigned or
chained, in the same module:

```text
torchvision.models.video: r3d_18, mc3_18, r2plus1d_18, s3d, mvit_v1_b, mvit_v2_s
pytorchvideo.models: slowfast_r50, slowfast_r101, x3d_m, x3d_s, x3d_xs, x3d_l
transformers: VideoMAEForVideoClassification, VivitForVideoClassification, VideoSwinForVideoClassification
```

The first family plus a forward call cannot distinguish naming an action from
other clip-level labelling with the same backbone: the pattern checks invocation,
not label meanings. The following pipeline also requires a call on its returned
value; its task literal alone is trusted without network access or weight checks:

```python
from transformers import pipeline
p = pipeline("video-classification")
p(clip)
```

The following pair is counted on construction plus a call in the same module.
It shows use of the checked capability, not that predicted labels are correct:

```text
mmaction: init_recognizer + inference_recognizer
```

These exact phrases are ambiguous because they can also describe detecting or
classifying user or UI actions such as clicks, keystrokes, or log events:

```text
action detection
action classification
```

The auditor cannot distinguish those meanings. Control flow and runtime types
are not evaluated. Bare imports, strings, comments, docstrings, subprocess CLI
commands, setup alone, and evidence split across modules do not count. Still-image
labelling, box finding, joint estimation, flow, tracking, generation, and frame
decoding alone do not establish the checked capability. Encoder-only video
models also do not qualify. No model quality or prediction correctness is verified.

## Development

```sh
python3 -m unittest discover
python3 -m build
```

Distributed under the MIT license.
