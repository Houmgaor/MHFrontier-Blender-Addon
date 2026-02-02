# -*- coding: utf-8 -*-
"""
Centralized builder factory for Blender operations.

Provides a single entry point for obtaining all builder instances,
avoiding scattered _get_default_builders() functions throughout the codebase.
"""

from dataclasses import dataclass
from typing import Optional

from .api import (
    MeshBuilder,
    ObjectBuilder,
    MaterialBuilder,
    ImageLoader,
    SceneManager,
    MatrixFactory,
    AnimationBuilder,
)


@dataclass
class Builders:
    """
    Container holding all builder instances for Blender operations.

    This class centralizes access to all builder interfaces, allowing
    import functions to receive a single object rather than multiple
    optional parameters.
    """

    mesh: MeshBuilder
    object: ObjectBuilder
    material: MaterialBuilder
    image: ImageLoader
    scene: SceneManager
    matrix: MatrixFactory
    animation: AnimationBuilder


_cached_builders: Optional[Builders] = None


def get_builders() -> Builders:
    """
    Get the singleton Builders instance with all Blender implementations.

    Uses lazy initialization to avoid importing Blender at module load time.

    :return: Builders instance with all concrete implementations.
    """
    global _cached_builders
    if _cached_builders is None:
        from .blender_impl import (
            get_mesh_builder,
            get_object_builder,
            get_material_builder,
            get_image_loader,
            get_scene_manager,
            get_matrix_factory,
            get_animation_builder,
        )

        _cached_builders = Builders(
            mesh=get_mesh_builder(),
            object=get_object_builder(),
            material=get_material_builder(),
            image=get_image_loader(),
            scene=get_scene_manager(),
            matrix=get_matrix_factory(),
            animation=get_animation_builder(),
        )
    return _cached_builders


def get_mock_builders() -> Builders:
    """
    Get a Builders instance with all mock implementations for testing.

    Creates a fresh set of mock builders each time (not cached).

    :return: Builders instance with mock implementations.
    """
    from .mock_impl import (
        MockMeshBuilder,
        MockObjectBuilder,
        MockMaterialBuilder,
        MockImageLoader,
        MockSceneManager,
        MockMatrixFactory,
        MockAnimationBuilder,
    )

    return Builders(
        mesh=MockMeshBuilder(),
        object=MockObjectBuilder(),
        material=MockMaterialBuilder(),
        image=MockImageLoader(),
        scene=MockSceneManager(),
        matrix=MockMatrixFactory(),
        animation=MockAnimationBuilder(),
    )
