from .simple_tiling_instance import TileType
import matplotlib as mpl
import matplotlib.pyplot as plt


def draw_solution(solution: dict[tuple[int,int], TileType], axis=None):
    if axis is None:
        axis = plt.gca()
    vertex_positions_x = []
    vertex_positions_y = []
    line_segments = []
    boundaries = []
    for (x, y), tile_type in solution.items():
        xoffs = 2.0 * x
        yoffs = 2.0 * y
        translated = tile_type.drawing.translate((xoffs, yoffs))
        for vertex in translated.vertices:
            vertex_positions_x.append(vertex.location[0])
            vertex_positions_y.append(vertex.location[1])
        for segment in translated.segments:
            line_segments.append(([segment.local_start[0], segment.local_end[0]], 
                                  [segment.local_start[1], segment.local_end[1]]))
        boundaries += [([xoffs - 1.0, xoffs + 1.0], [yoffs - 1.0, yoffs - 1.0]), 
                       ([xoffs + 1.0, xoffs + 1.0], [yoffs - 1.0, yoffs + 1.0]),
                       ([xoffs + 1.0, xoffs - 1.0], [yoffs + 1.0, yoffs + 1.0]), 
                       ([xoffs - 1.0, xoffs - 1.0], [yoffs + 1.0, yoffs - 1.0])]
    axis.scatter(vertex_positions_x, vertex_positions_y, s=10, c='C0', zorder=3)
    for line_segment in line_segments:
        axis.plot(line_segment[0], line_segment[1], c='C0', zorder=2)
    for line_segment in boundaries:
        axis.plot(line_segment[0], line_segment[1], c='darkgray', zorder=1)
    axis.set_aspect('equal')
    return axis
