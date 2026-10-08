from scripts.export_openapi import SPEC_PATH, render


def test_committed_openapi_json_matches_the_app():
    """The frontend builds its types from openapi.json, so it must not fall behind the code."""
    assert SPEC_PATH.read_text() == render(), (
        "The API changed. Run `python -m scripts.export_openapi` in backend/ and commit openapi.json."
    )
