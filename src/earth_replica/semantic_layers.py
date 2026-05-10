"""Semantic surface material layers for the globe preview and tile pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticSurfaceLayer:
    """A separate map material layer with source and provenance metadata."""

    id: str
    label: str
    source_layers: tuple[str, ...]
    material_class: str
    physical_surface: str
    color: str
    opacity: float
    provenance_source: str
    provenance_state: str = "observed"
    confidence: float = 0.74

    def to_record(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "source_layers": list(self.source_layers),
            "material": {
                "class": self.material_class,
                "physical_surface": self.physical_surface,
                "color": self.color,
                "opacity": self.opacity,
            },
            "provenance": {
                "source": self.provenance_source,
                "state": self.provenance_state,
                "confidence": self.confidence,
            },
        }


def semantic_surface_layers() -> tuple[SemanticSurfaceLayer, ...]:
    """Return ordered semantic layers for Earth surface rendering."""

    source = "OpenMapTiles/MapTiler vector tiles from OSM and open land-cover sources"
    return (
        SemanticSurfaceLayer(
            id="water",
            label="Water",
            source_layers=("water",),
            material_class="water",
            physical_surface="fluid",
            color="#1d6f9f",
            opacity=0.46,
            provenance_source=source,
            confidence=0.86,
        ),
        SemanticSurfaceLayer(
            id="forest",
            label="Forest",
            source_layers=("landcover",),
            material_class="vegetation",
            physical_surface="canopy",
            color="#1f6b3b",
            opacity=0.34,
            provenance_source=source,
            confidence=0.76,
        ),
        SemanticSurfaceLayer(
            id="park_grass",
            label="Parks and grass",
            source_layers=("park", "landcover"),
            material_class="vegetation",
            physical_surface="grass",
            color="#6fae5f",
            opacity=0.26,
            provenance_source=source,
            confidence=0.68,
        ),
        SemanticSurfaceLayer(
            id="farmland",
            label="Farmland",
            source_layers=("landuse",),
            material_class="cropland",
            physical_surface="soil_vegetation",
            color="#b7a95a",
            opacity=0.25,
            provenance_source=source,
            confidence=0.7,
        ),
        SemanticSurfaceLayer(
            id="desert_sand",
            label="Desert and sand",
            source_layers=("landcover",),
            material_class="sand",
            physical_surface="granular_soil",
            color="#c9b06d",
            opacity=0.28,
            provenance_source=source,
            confidence=0.62,
        ),
        SemanticSurfaceLayer(
            id="snow_ice",
            label="Snow and ice",
            source_layers=("landcover",),
            material_class="ice",
            physical_surface="frozen_water",
            color="#e6f3ff",
            opacity=0.52,
            provenance_source=source,
            confidence=0.72,
        ),
        SemanticSurfaceLayer(
            id="wetland",
            label="Wetland",
            source_layers=("landcover", "landuse"),
            material_class="wetland",
            physical_surface="saturated_soil",
            color="#4f8d7c",
            opacity=0.28,
            provenance_source=source,
            confidence=0.62,
        ),
        SemanticSurfaceLayer(
            id="urban",
            label="Urban",
            source_layers=("landuse",),
            material_class="built_up",
            physical_surface="impervious",
            color="#9a9690",
            opacity=0.22,
            provenance_source=source,
            confidence=0.78,
        ),
        SemanticSurfaceLayer(
            id="roads",
            label="Roads",
            source_layers=("transportation",),
            material_class="asphalt_concrete",
            physical_surface="impervious",
            color="#eee5d5",
            opacity=0.78,
            provenance_source=source,
            confidence=0.84,
        ),
    )


def semantic_surface_manifest() -> dict[str, object]:
    """Return a serializable semantic material/provenance manifest."""

    return {
        "schema": "earth-replica/semantic-surface-layers/v1",
        "layers": [layer.to_record() for layer in semantic_surface_layers()],
        "recommended_repositories": [
            {
                "name": "openmaptiles/openmaptiles",
                "purpose": "Open vector tile schema and generation for water, roads, buildings, landcover, and landuse.",
                "url": "https://github.com/openmaptiles/openmaptiles",
            },
            {
                "name": "OvertureMaps/overture-tiles",
                "purpose": "Open PMTiles pipeline for Overture buildings, transportation, base, land, and water themes.",
                "url": "https://github.com/OvertureMaps/overture-tiles",
            },
        ],
        "quality_policy": {
            "semantic_layers_are_not_pixel_colors": True,
            "source_provenance_required_per_layer": True,
            "ai_classification_must_remain_inferred": True,
        },
    }
