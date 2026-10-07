"""Verify captured runtime inputs from archived bytes, without original file paths."""

import hashlib
from pathlib import PurePosixPath

from reported_dana_corpora import read, sha


def source_snapshots():
    snapshots = dict(read("docs/reported-deoni-broad-inputs.json.gz")["sources"])
    assert len(snapshots) == 2
    corpus = read("docs/reported-dana-prototype-corpora.json.gz")
    assert len(corpus["corpora"]) == 4
    for row in corpus["corpora"]:
        relative = PurePosixPath(row["source"])
        assert not relative.is_absolute() and ".." not in relative.parts
        name = "/home/josh/projects/klem/" + str(relative)
        assert name not in snapshots
        snapshots[name] = {
            "text": row["original_source_text"],
            "sha256": row["source_sha256"],
        }
    assert len(snapshots) == 6
    return snapshots


def verify_frozen_inputs(frozen, snapshots=None):
    for name, expected in frozen.items():
        path = PurePosixPath(name)
        if not path.is_absolute() and path.parts[0] == "docs":
            assert ".." not in path.parts
            assert sha(name) == expected
        else:
            if snapshots is None:
                snapshots = source_snapshots()
            assert name in snapshots, name
            archived = snapshots[name]
            assert (
                hashlib.sha256(archived["text"].encode()).hexdigest()
                == archived["sha256"]
                == expected
            ), name
