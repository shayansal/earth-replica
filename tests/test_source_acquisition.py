import json

from earth_replica.source_acquisition import (
    SourceAcquisitionCatalog,
    build_replica_source_catalog,
)


def test_replica_source_catalog_lists_all_global_source_families():
    catalog = build_replica_source_catalog()
    record = catalog.to_record()

    names = {source["name"] for source in record["sources"]}
    assert "OSM planet PBF" in names
    assert "Overture Maps Buildings" in names
    assert "Overture Maps Transportation" in names
    assert "NOAA ETOPO 2022" in names
    assert "GEBCO global bathymetry" in names
    assert "Copernicus global land cover" in names
    assert "Sentinel-2 global imagery index" in names
    assert "NASA Blue Marble baseline imagery" in names
    assert record["safety"]["full_planet_download_requires_explicit_flag"] is True
    assert record["safety"]["local_default"] == "metadata_and_bounded_samples_only"


def test_catalog_rejects_full_planet_fetch_without_explicit_flag(tmp_path):
    catalog = build_replica_source_catalog()

    try:
        catalog.write_fetch_plan(tmp_path / "fetch-plan.json", allow_full_planet_downloads=False)
    except PermissionError as error:
        assert "full planet downloads require" in str(error)
    else:
        raise AssertionError("catalog allowed full-planet fetch without explicit flag")


def test_catalog_writes_manifest_when_large_downloads_are_allowed(tmp_path):
    catalog = build_replica_source_catalog()
    path = catalog.write_fetch_plan(tmp_path / "fetch-plan.json", allow_full_planet_downloads=True)
    record = json.loads(path.read_text(encoding="utf-8"))

    assert record["schema"] == "earth-replica/source-acquisition-catalog/v1"
    assert record["execution"]["allow_full_planet_downloads"] is True
    assert all("source_uri" in source for source in record["sources"])


def test_catalog_requires_required_source_families():
    try:
        SourceAcquisitionCatalog(sources=())
    except ValueError as error:
        assert "required source family" in str(error)
    else:
        raise AssertionError("catalog accepted empty source list")
