"""Check every compiled identity row against the immutable source fixture."""

import argparse
import json
import re

from doeda_identity_audit import FIXTURE
from lexical_nada_audit import ROOT, read


def inspect(text, data):
    string = r'"(?:[^"\\]|\\.)*"'
    pattern = re.compile(
        r"OriginSource\s*\{\s*base:\s*(" + string + r"),\s*"
        r"expected_origins:\s*&(?P<origins>\[[^]]*\]),\s*"
        r"whole_entries:\s*&(?P<entries>\[[^]]*\]),\s*"
        r"whole_origins_complete:\s*(?P<complete>true|false),\s*\}",
        re.DOTALL,
    )
    actual = [
        {
            "base": json.loads(m.group(1)),
            "expected_origins": json.loads(m["origins"]),
            "whole_entries": json.loads(m["entries"]),
            "whole_origins_complete": m["complete"] == "true",
        }
        for m in pattern.finditer(text)
    ]
    expected = [
        {
            k: row[k]
            for k in (
                "base",
                "expected_origins",
                "whole_entries",
                "whole_origins_complete",
            )
        }
        for row in sorted(data["heads"], key=lambda r: r["base"])
    ]
    assert actual == expected and len(actual) == 192
    assert len({r["base"] for r in actual}) == len(actual)
    assert "if !matches!(class, PredicateClass::Verb)" in text
    print(
        "Verified 192 unique rows sorted by base, all whole IDs/origins and finite verb scope."
    )


def verify():
    inspect((ROOT / "src/doeda_identity.rs").read_text(), read(FIXTURE))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true", required=True)
    p.parse_args()
    verify()
