import pytest

from run_pipeline import OUTPUT_FILENAMES, promote_outputs


def test_promote_outputs_preserves_old_delivery_when_staging_is_incomplete(
    tmp_path,
):
    data_directory = tmp_path / "data"
    staging_directory = tmp_path / "staging"
    data_directory.mkdir()
    staging_directory.mkdir()
    old_database = data_directory / "books.sqlite"
    old_database.write_text("old", encoding="utf-8")
    (staging_directory / "books.sqlite").write_text("new", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        promote_outputs(staging_directory, data_directory)

    assert old_database.read_text(encoding="utf-8") == "old"


def test_promote_outputs_replaces_complete_delivery(tmp_path):
    data_directory = tmp_path / "data"
    staging_directory = tmp_path / "staging"
    data_directory.mkdir()
    staging_directory.mkdir()
    for filename in OUTPUT_FILENAMES:
        (data_directory / filename).write_text("old", encoding="utf-8")
        (staging_directory / filename).write_text("new", encoding="utf-8")

    promote_outputs(staging_directory, data_directory)

    assert all(
        (data_directory / filename).read_text(encoding="utf-8") == "new"
        for filename in OUTPUT_FILENAMES
    )
