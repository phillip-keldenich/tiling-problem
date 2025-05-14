from pydantic import BaseModel, Field, model_validator
import math


def point_almost_equal(p, q, epsilon=1e-8):
    return math.hypot(p[0] - q[0], p[1] - q[1]) < epsilon


def segment_almost_equal(s1, s2, epsilon=1e-8):
    return (
        point_almost_equal(s1.local_start, s2.local_start, epsilon)
        and point_almost_equal(s1.local_end, s2.local_end, epsilon)
    ) or (
        point_almost_equal(s1.local_start, s2.local_end, epsilon)
        and point_almost_equal(s1.local_end, s2.local_start, epsilon)
    )


class TileTypeDrawSegment(BaseModel, frozen=True):
    """
    Drawable segment in a tile type.
    """

    local_start: tuple[float, float] = Field(
        ..., description="Local start point of the segment"
    )
    local_end: tuple[float, float] = Field(
        ..., description="Local end point of the segment"
    )

    def rotate(self, amount: int):
        angle = amount * 0.5 * math.pi
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        x1, y1 = self.local_start
        x2, y2 = self.local_end
        return TileTypeDrawSegment(
            local_start=(
                x1 * cos_angle - y1 * sin_angle,
                x1 * sin_angle + y1 * cos_angle,
            ),
            local_end=(
                x2 * cos_angle - y2 * sin_angle,
                x2 * sin_angle + y2 * cos_angle,
            ),
        )

    def translate(self, amount: tuple[float, float]):
        x1, y1 = self.local_start
        x2, y2 = self.local_end
        dx, dy = amount
        return TileTypeDrawSegment(
            local_start=(x1 + dx, y1 + dy), local_end=(x2 + dx, y2 + dy)
        )

    def reflect(self, axis: str):
        if axis == "x":
            x1, y1 = self.local_start
            x2, y2 = self.local_end
            return TileTypeDrawSegment(local_start=(-x1, y1), local_end=(-x2, y2))
        elif axis == "y":
            x1, y1 = self.local_start
            x2, y2 = self.local_end
            return TileTypeDrawSegment(local_start=(x1, -y1), local_end=(x2, -y2))
        else:
            raise ValueError("Invalid axis for reflecting. Use 'x' or 'y'.")


class TileTypeDrawVertex(BaseModel, frozen=True):
    """
    Drawable vertex in a tile type.
    """

    location: tuple[float, float] = Field(
        ..., description="Location of the vertex (origin is at the center of the tile)"
    )

    def translate(self, amount: tuple[float, float]):
        x, y = self.location
        dx, dy = amount
        return TileTypeDrawVertex(location=(x + dx, y + dy))

    def rotate(self, amount: int):
        angle = 0.5 * math.pi * amount
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        x, y = self.location
        return TileTypeDrawVertex(
            location=(x * cos_angle - y * sin_angle, x * sin_angle + y * cos_angle)
        )

    def reflect(self, axis: str):
        if axis == "x":
            x, y = self.location
            return TileTypeDrawVertex(location=(-x, y))
        elif axis == "y":
            x, y = self.location
            return TileTypeDrawVertex(location=(x, -y))
        else:
            raise ValueError("Invalid axis for reflecting. Use 'x' or 'y'.")


class TileTypeDrawing(BaseModel):
    segments: list[TileTypeDrawSegment] = Field(
        ..., description="List of segments in the tile type"
    )
    vertices: list[TileTypeDrawVertex] = Field(
        ..., description="List of vertices in the tile type"
    )

    def rotate(self, amount: int):
        return TileTypeDrawing(
            segments=[segment.rotate(amount) for segment in self.segments],
            vertices=[vertex.rotate(amount) for vertex in self.vertices],
        )

    def reflect(self, axis: str):
        return TileTypeDrawing(
            segments=[segment.reflect(axis) for segment in self.segments],
            vertices=[vertex.reflect(axis) for vertex in self.vertices],
        )

    def translate(self, amount: tuple[float, float]):
        return TileTypeDrawing(
            segments=[segment.translate(amount) for segment in self.segments],
            vertices=[vertex.translate(amount) for vertex in self.vertices],
        )

    def is_almost_equal(self, other):
        o = set(other.vertices)
        for vertex in self.vertices:
            found = None
            for other_vertex in o:
                if point_almost_equal(vertex.location, other_vertex.location):
                    found = other_vertex
                    break
            if found is None:
                return False
            o.remove(found)
        oseg = set(other.segments)
        for segment in self.segments:
            found = None
            for other_segment in oseg:
                if segment_almost_equal(segment, other_segment):
                    found = other_segment
                    break
            if found is None:
                return False
            oseg.remove(found)
        return True


class TileType(BaseModel):
    """
    Class representing a tile type in a tiling instance.
    """

    name: str = Field(..., description="Name of the tile type")
    bottom_edges: list[float] = Field(
        ..., description="List of bottom edge indices of the tile type"
    )
    top_edges: list[float] = Field(
        ..., description="List of top edge indices of the tile type"
    )
    left_edges: list[float] = Field(
        ..., description="List of left edge indices of the tile type"
    )
    right_edges: list[float] = Field(
        ..., description="List of right edge indices of the tile type"
    )
    drawing: TileTypeDrawing = Field(
        ..., description="Drawing information of the tile type"
    )
    actual_index: int = Field(-1, description="Internal index")

    def boundaries(self):
        yield self.bottom_edges
        yield self.right_edges
        yield self.top_edges
        yield self.left_edges

    def rotate(self, amount: int):
        ccw_order = [
            self.bottom_edges,
            self.right_edges,
            self.top_edges,
            self.left_edges,
        ]
        new_order = ccw_order[-amount:] + ccw_order[:-amount]
        return TileType(
            name=self.name,
            bottom_edges=new_order[0],
            right_edges=new_order[1],
            top_edges=new_order[2],
            left_edges=new_order[3],
            drawing=self.drawing.rotate(amount),
        )

    def reflect(self, axis: str):
        if axis == "x":
            return TileType(
                name=self.name,
                bottom_edges=[-edge for edge in self.bottom_edges],
                right_edges=self.left_edges,
                top_edges=[-edge for edge in self.top_edges],
                left_edges=self.right_edges,
                drawing=self.drawing.reflect(axis),
            )
        elif axis == "y":
            return TileType(
                name=self.name,
                bottom_edges=self.top_edges,
                right_edges=[-edge for edge in self.right_edges],
                top_edges=self.bottom_edges,
                left_edges=[-edge for edge in self.left_edges],
                drawing=self.drawing.reflect(axis),
            )
        else:
            raise ValueError("Invalid axis for reflecting. Use 'x' or 'y'.")

    def is_almost_equal(self, other):
        return self.drawing.is_almost_equal(other.drawing)


class TilingInstance(BaseModel):
    """
    Class representing a tiling instance.
    """

    instance_name: str = Field(..., description="Name of the tiling instance")
    tile_types: list[TileType] = Field(
        ..., description="List of tile types in the tiling instance"
    )
    tile_type_counts: list[int] = Field(
        ..., description="List of counts for each tile type"
    )
    width: int = Field(..., description="Goal width of the tiling")
    height: int = Field(..., description="Goal height of the tiling")

    @model_validator(mode="after")
    def check_counts(self):
        if len(self.tile_types) != len(self.tile_type_counts):
            raise ValueError(
                "Tile types and tile type counts must have the same length."
            )
        if any(count < 0 for count in self.tile_type_counts):
            raise ValueError("Tile type counts must be non-negative.")
        for tile_type in self.tile_types:
            for boundary in tile_type.boundaries():
                boundary.sort()
        return self
