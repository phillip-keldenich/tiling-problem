from .simple_tiling_instance import TilingInstance, TileType
from ortools.sat.python import cp_model


class SimpleCPSATSolver:
    def _do_reflect(self, tile_type, axis_comb):
        if axis_comb == '':
            return tile_type
        if axis_comb == 'x':
            return tile_type.reflect('x')
        if axis_comb == 'y':
            return tile_type.reflect('y')
        tile_type = tile_type.reflect('x')
        tile_type = tile_type.reflect('y')
        return tile_type
    
    def _make_var(self, name=""):
        return self.solver.NewBoolVar(name)

    def _make_cell_vars(self):
        """
        Create variables for each cell in the grid.
        Also adds constraints to ensure that each cell has exactly one tile type,
        and that the number of tiles of each type matches the given counts.
        """
        cell_vars = {}
        tiles_of_type = {i: [] for i in range(len(self.instance.tile_types))}
        for y in range(self.instance.height):
            for x in range(self.instance.width):
                cvs = [self._make_var() for _ in range(len(self.actual_tile_types))]
                cell_vars[(x, y)] = cvs
                self.solver.add_exactly_one(cvs)
                for i, var in enumerate(cvs):
                    tiles_of_type[self.actual_tile_types[i].actual_index].append(var)
        for i, tile_vars in tiles_of_type.items():
            self.solver.add(sum(tile_vars) == self.instance.tile_type_counts[i])
        return cell_vars

    def _make_boundary_vars(self):
        boundary_vars = {}
        cell_vars = self.cell_vars
        for x, y in cell_vars.keys():
            n = [(x, y+1), (x+1, y)]
            for nx, ny in n:
                if (nx, ny) in cell_vars:
                    boundary_vars[(x, y), (nx, ny)] = [self._make_var() for _ in range(len(self.boundary_types))]
                    self.solver.add_exactly_one(boundary_vars[(x, y), (nx, ny)])
        return boundary_vars

    def _actual_tile_types(self):
        result = []
        for actual_index, tile_type in enumerate(self.instance.tile_types):
            for ref in (['', 'x', 'y', 'xy'] if self.allow_reflections else ['']):
                reflected = self._do_reflect(tile_type, ref)
                for rot in range(4 if self.allow_rotations else 1):
                    rotated = reflected.rotate(rot)
                    if not any(rotated.is_almost_equal(t) for t in result):
                        rotated.actual_index = actual_index
                        result.append(rotated)
        return result
    
    def _add_boundary_constraint(self, boundary_type_var, matching_cell_vars):
        """
        Add a constraint that ensures that the boundary variable is true
        iff one of the corresponding cell variables is true.
        """
        self.solver.add_bool_or([boundary_type_var.Not()] + matching_cell_vars)
        for cell_var in matching_cell_vars:
            self.solver.add_implication(cell_var, boundary_type_var)

    def _actual_tile_with_types(self):
        actual_tiles_with_top_type = {i: [] for i in range(len(self.boundary_types))}
        actual_tiles_with_bottom_type = {i: [] for i in range(len(self.boundary_types))}
        actual_tiles_with_left_type = {i: [] for i in range(len(self.boundary_types))}
        actual_tiles_with_right_type = {i: [] for i in range(len(self.boundary_types))}
        for i, tile_type in enumerate(self.actual_tile_types):
            actual_tiles_with_top_type[self.boundary_to_index[tuple(tile_type.top_edges)]].append(i)
            actual_tiles_with_bottom_type[self.boundary_to_index[tuple(tile_type.bottom_edges)]].append(i)
            actual_tiles_with_left_type[self.boundary_to_index[tuple(tile_type.left_edges)]].append(i)
            actual_tiles_with_right_type[self.boundary_to_index[tuple(tile_type.right_edges)]].append(i)
        self.actual_tiles_with_top_type = actual_tiles_with_top_type
        self.actual_tiles_with_bottom_type = actual_tiles_with_bottom_type
        self.actual_tiles_with_left_type = actual_tiles_with_left_type
        self.actual_tiles_with_right_type = actual_tiles_with_right_type

    def _add_boundary_constraints(self):
        self._actual_tile_with_types()
        attb = self.actual_tiles_with_bottom_type
        attt = self.actual_tiles_with_top_type
        attl = self.actual_tiles_with_left_type
        attr = self.actual_tiles_with_right_type
        for (c1, c2), bvs in self.boundary_vars.items():
            below = (c1[1] < c2[1])
            c1vs, c2vs = self.cell_vars[c1], self.cell_vars[c2]
            for boundary_type_index, boundary_var in enumerate(bvs):
                if below:
                    self._add_boundary_constraint(boundary_var, [c1vs[x] for x in attt[boundary_type_index]])
                    self._add_boundary_constraint(boundary_var, [c2vs[x] for x in attb[boundary_type_index]])
                else:
                    self._add_boundary_constraint(boundary_var, [c1vs[x] for x in attr[boundary_type_index]])
                    self._add_boundary_constraint(boundary_var, [c2vs[x] for x in attl[boundary_type_index]])

    def _compute_boundary_types(self):
        boundary_to_index = {}
        boundary_types = []
        for tile_type in self.actual_tile_types:
            for boundary in tile_type.boundaries():
                tb = tuple(boundary)
                if tb not in boundary_to_index:
                    boundary_to_index[tb] = len(boundary_types)
                    boundary_types.append(tb)
        return boundary_types, boundary_to_index

    def __init__(self, instance: TilingInstance,
                 allow_rotations: bool = True,
                 allow_reflections: bool = True):
        self.solver = cp_model.CpModel()
        self.instance = instance
        self.allow_rotations = allow_rotations
        self.allow_reflections = allow_reflections
        self.actual_tile_types: list[TileType] = self._actual_tile_types()
        self.boundary_types: list[tuple] = []
        self.boundary_to_index: dict[tuple, int] = {}
        self.boundary_types, self.boundary_to_index = self._compute_boundary_types()
        self.cell_vars = self._make_cell_vars()
        self.boundary_vars = self._make_boundary_vars()
        self._add_boundary_constraints()

    def solve(self) -> dict[tuple[int, int], TileType] | None:
        sol = cp_model.CpSolver()
        status = sol.solve(self.solver)
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            result = {}
            for (x, y), vars in self.cell_vars.items():
                for i, var in enumerate(vars):
                    if sol.boolean_value(var):
                        if (x, y) in result:
                            raise ValueError("Multiple tile types found for the same cell.")
                        result[(x, y)] = self.actual_tile_types[i]
                if (x, y) not in result:
                    raise ValueError("No tile type found for a cell.")
            return result
        if status == cp_model.INFEASIBLE:
            return None
        raise RuntimeError(f"Solver failed with status: {status}")
