from os import remove as removeFile
from itertools import starmap
import unittest
import logic_iterative as logic
import data_structs as ds

# --- Unit tests -------------------------------------------------------------------------------------------------------


class UnitTests(unittest.TestCase):
    def test_init(self):
        metrics = {"T1": 3.0, "T2": 5}
        unit = logic.Unit(code="D", metrics=metrics, scale="test")
        self.assertEqual(unit.code, "D")
        self.assertEqual(unit.metrics, metrics)
        self.assertEqual(unit.name, "D_Name")
        self.assertEqual(unit.metric, 3)

    def test_strHelpers(self):
        unit = logic.Unit(code="D", metrics={"T1": 3.0}, scale="test")
        self.assertEqual(f"String name: {unit}", "String name: D")

    def test_setMetric(self):
        metrics = {"T1": 3.0, "T2": 5}
        unit = logic.Unit(code="D", metrics=metrics, scale="test")
        self.assertEqual(unit.metric, metrics["T1"])
        unit.setCurrentMetric("T2")
        self.assertEqual(unit.metric, metrics["T2"])

    def test_comparison(self):
        unit1 = logic.Unit(code="D", metrics={"T1": 3.0}, scale="test")
        unit2 = logic.Unit(code="D", metrics={"T2": 5}, scale="test")
        self.assertEqual(unit1, unit2)
        self.assertEqual(unit1, "D")
        self.assertEqual(unit2, "D")


class FileReadTests(unittest.TestCase):
    def test_fileRead(self):
        unitlist, metricNames = ds.readFile("test")
        (a, b, c, d, e, f, g, h, i, j) = [logic.Unit(code, {"T1": i}, "test") for i, code in enumerate("ABCDEFGHIJ")]
        self.assertEqual(unitlist, [a, b, c, d, e, f, g, h, i, j])
        self.assertEqual([u.metrics["T1"] for u in unitlist], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(
            [u.adj for u in unitlist],
            [
                {d},
                {c, e, f},
                {b, f, g},
                {a},
                {b, f},
                {b, c, e, g, h},
                {c, f, h},
                {f, g, i, j},
                {h, j},
                {h, i},
            ],
        )
        self.assertEqual(metricNames, ["T1"])

    def test_lazyInit(self):
        (a, b, c, d, e, f, g, h, i, j) = [logic.Unit(code, {"T1": i}, "test") for i, code in enumerate("ABCDEFGHIJ")]

        self.assertEqual(ds._unitlists, {})
        self.assertEqual(ds._metricNames, {})

        # Confirm that both lists are initialized from one read
        self.assertEqual(ds.unitlist("test"), [a, b, c, d, e, f, g, h, i, j])
        self.assertEqual(ds._unitlists, {"test": [a, b, c, d, e, f, g, h, i, j]})
        self.assertEqual(ds._metricNames, {"test": ["T1"]})
        self.assertEqual(ds.metricNames("test"), ["T1"])

        # clear lists to try again
        ds._unitlists = {}
        ds._metricNames = {}

        # Confirm that both lists are initialized in the opposite direction read
        self.assertEqual(ds.metricNames("test"), ["T1"])
        self.assertEqual(ds._unitlists, {"test": [a, b, c, d, e, f, g, h, i, j]})
        self.assertEqual(ds._metricNames, {"test": ["T1"]})
        self.assertEqual(ds.unitlist("test"), [a, b, c, d, e, f, g, h, i, j])

        # clear lists to try again
        ds._unitlists = {}
        ds._metricNames = {"test": ["T2"]}

        # Confirm that list is not re-initialized if it's already set
        self.assertEqual(ds.metricNames("test"), ["T2"])
        self.assertEqual(ds._unitlists, {})
        self.assertEqual(ds.unitlist("test"), [a, b, c, d, e, f, g, h, i, j])

    def test_distanceGen(self):
        distances = [
            {"D": 1},
            {"C": 1, "E": 1, "F": 1, "G": 2, "H": 2, "I": 3, "J": 3},
            {"B": 1, "E": 2, "F": 1, "G": 1, "H": 2, "I": 3, "J": 3},
            {"A": 1},
            {"B": 1, "C": 2, "F": 1, "G": 2, "H": 2, "I": 3, "J": 3},
            {"B": 1, "C": 1, "E": 1, "G": 1, "H": 1, "I": 2, "J": 2},
            {"B": 2, "C": 1, "E": 2, "F": 1, "H": 1, "I": 2, "J": 2},
            {"B": 2, "C": 2, "E": 2, "F": 1, "G": 1, "I": 1, "J": 1},
            {"B": 3, "C": 3, "E": 3, "F": 2, "G": 2, "H": 1, "J": 1},
            {"B": 3, "C": 3, "E": 3, "F": 2, "G": 2, "H": 1, "I": 1},
        ]

        _, _ = ds.readFile("test")
        unitlist, _ = ds.readFile("test")
        self.assertEqual([u.distances for u in unitlist], distances)
        removeFile("assets/test/distance.csv")
        unitlist, _ = ds.readFile("test")
        self.assertEqual([u.distances for u in unitlist], distances)


class GroupTests(unittest.TestCase):
    unitlist, metricNames = ds.readFile("test")

    def test_init(self):
        group = logic.Group(index=0)
        self.assertEqual(group.index, 0)
        self.assertEqual(group.metric, 0)
        self.assertTrue(group.empty)

    def test_compare(self):
        (a, b, c, d, e, f, g, h, i, j) = GroupTests.unitlist
        g1 = logic.Group(index=0)
        g2 = logic.Group(index=1)
        g3 = logic.Group(index=2)

        self.assertEqual(sorted([g1, g2, g3]), [g1, g2, g3])

        g2.addUnit(j)
        g3.addUnit(f)
        self.assertEqual(sorted([g1, g2, g3]), [g1, g3, g2])

    def test_isContiguous(self):
        (a, b, c, d, e, f, g, h, i, j) = GroupTests.unitlist
        group = logic.Group(index=0)
        self.assertTrue(group.isContiguous)

        group.addUnit(a)
        self.assertTrue(group.isContiguous)

        group.addUnit(d)
        self.assertTrue(group.isContiguous)

        group.addUnit(c)
        self.assertTrue(group.isContiguous)

        group.addUnit(b)
        self.assertTrue(group.isContiguous)

        group.addUnit(h)
        self.assertFalse(group.isContiguous)

        group.addUnit(i)
        self.assertFalse(group.isContiguous)

        group.addUnit(f)
        self.assertTrue(group.isContiguous)

        group.removeUnit(h)
        self.assertFalse(group.isContiguous)

        group.removeUnit(i)
        self.assertTrue(group.isContiguous)

        group.removeUnit(d)
        self.assertTrue(group.isContiguous)

    def test_unitChanges(self):
        (a, b, c, d, e, f, g, h, i, j) = GroupTests.unitlist
        group = logic.Group(index=0)

        self.assertTrue(group.empty)
        self.assertEqual(group.metric, 0)
        self.assertEqual(group.units, set())
        self.assertEqual(group.adj, set())
        self.assertEqual(group.distanceSum, {})

        group.addUnit(b)
        self.assertFalse(group.empty)
        self.assertEqual(group.metric, 1)
        self.assertEqual(group.units, {b})
        self.assertEqual(group.adj, {c, e, f})
        self.assertEqual(group.distanceSum, {"C": 1, "E": 1, "F": 1, "G": 2, "H": 2, "I": 3, "J": 3})

        group.addUnit(e)
        self.assertFalse(group.empty)
        self.assertEqual(group.metric, 5)
        self.assertEqual(group.units, {b, e})
        self.assertEqual(group.adj, {c, f})
        self.assertEqual(group.distanceSum, {"B": 1, "C": 3, "E": 1, "F": 2, "G": 4, "H": 4, "I": 6, "J": 6})

        group.removeUnit(b)
        self.assertFalse(group.empty)
        self.assertEqual(group.metric, 4)
        self.assertEqual(group.units, {e})
        self.assertEqual(group.adj, {b, f})
        self.assertEqual(group.distanceSum, {"B": 1, "C": 2, "F": 1, "G": 2, "H": 2, "I": 3, "J": 3})

        group.addUnit(a)
        self.assertFalse(group.empty)
        self.assertEqual(group.metric, 4)
        self.assertEqual(group.units, {a, e})
        self.assertEqual(group.adj, {b, d, f})
        self.assertEqual(group.distanceSum, {"B": 1, "C": 2, "D": 1, "F": 1, "G": 2, "H": 2, "I": 3, "J": 3})

        group.removeUnit(e)
        self.assertFalse(group.empty)
        self.assertEqual(group.metric, 0)
        self.assertEqual(group.units, {a})
        self.assertEqual(group.adj, {d})
        self.assertEqual(group.distanceSum, {"D": 1})

        group.removeUnit(a)
        self.assertTrue(group.empty)
        self.assertEqual(group.metric, 0)
        self.assertEqual(group.units, set())
        self.assertEqual(group.adj, set())
        self.assertEqual(group.distanceSum, {})

    def test_canLose(self):
        (a, b, c, d, e, f, g, h, i, j) = GroupTests.unitlist
        group = logic.Group(index=0)
        group.addUnit(a)
        group.addUnit(c)
        group.addUnit(g)
        group.addUnit(h)

        self.assertTrue(group.canLose(a))
        self.assertTrue(group.canLose(h))
        self.assertTrue(group.canLose(c))
        self.assertFalse(group.canLose(g))

        group.removeUnit(h)
        self.assertTrue(group.canLose(g))


class StateTests(unittest.TestCase):
    def test_convenienceParsers(self):
        ds.scales = ["test"]
        ds._metricNames = {"test": ["T1"]}
        self.assertEqual(logic.State.parseScale(0), "test")
        self.assertEqual(logic.State.parseScale("test2"), "test2")

        self.assertEqual(logic.State.parseMetricID("test", 0), "T1")
        self.assertEqual(logic.State.parseMetricID("test", "T2"), "T2")

    def test_init(self):
        state = logic.State(2, "T1", "test")
        self.assertEqual(state.metricID, "T1")
        self.assertEqual(state.scale, "test")
        self.assertIsNone(state._callback)

        self.assertEqual(sorted(u.code for u in state.placements), ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"])
        self.assertTrue(
            all((p == 0 for p in state.placements.values())),
            f"Units prematurely placed: {[(u.code, p) for u, p in state.placements.items() if p != 1]}",
        )

        self.assertEqual(state.unplacedUnits, ["J", "I", "H", "G", "F", "E", "D", "C", "B", "A"])

        self.assertEqual(sorted(g.index for g in state.groups), [1, 2])

    def test_addToGroup(self):
        state = logic.State(2, "T1", "test")
        (a, b, c, d, e, f, g, h, i, j) = state.placements.keys()
        (g1, g2) = state.groups

        state.addToGroup(a, g1)
        self.assertEqual(g1.units, {a})
        self.assertEqual(g1.index, 1)
        self.assertEqual(state.placements[a], 1)

        state.addToGroup(b, g1)
        self.assertEqual(g1.units, {a, b})
        self.assertEqual(g1.index, 1)
        self.assertEqual(state.placements[b], 1)

        state.addToGroup(a, g2)
        self.assertEqual(g1.units, {b})
        self.assertEqual(g2.units, {a})
        self.assertEqual(g2.index, 2)
        self.assertEqual(state.placements[a], 2)

    def test_groupFor(self):
        state = logic.State(2, "T1", "test")
        (a, b, c, d, e, f, g, h, i, j) = state.placements.keys()
        (g1, g2) = state.groups

        state.addToGroup(a, g1)
        state.addToGroup(b, g1)
        state.addToGroup(c, g2)
        state.addToGroup(d, g2)

        self.assertEqual(state.getGroupFor(a), g1)
        self.assertEqual(state.getGroupFor(b), g1)
        self.assertEqual(state.getGroupFor(c), g2)
        self.assertEqual(state.getGroupFor(d), g2)

    def test_anyUnplaced(self):
        state = logic.State(2, "T1", "test")
        (a, b, c, d, e, f, g, h, i, j) = state.placements.keys()
        (g1, g2) = state.groups

        self.assertFalse(state.hasAnyUnplacedAdjacent(g1))
        g1.addUnit(a)
        self.assertTrue(state.hasAnyUnplacedAdjacent(g1))
        g1.addUnit(d)
        self.assertFalse(state.hasAnyUnplacedAdjacent(g1))
        g1.addUnit(b)
        self.assertTrue(state.hasAnyUnplacedAdjacent(g1))

    def test_generateDisconnected(self):
        state = logic.State(2, "T1", "test")
        (a, b, c, d, e, f, g, h, i, j) = state.placements.keys()
        (g1, g2) = state.groups

        state.addToGroup(a, g1)
        state.addToGroup(d, g1)
        state.addToGroup(h, g2)
        state.addToGroup(f, g2)

        self.assertEqual(list(state.generateDisconnectedGroups(g1)), [])
        disconnected = list(state.generateDisconnectedGroups(g2))
        self.assertEqual(len(disconnected), 2)
        self.assertIn({b, c, e, g}, disconnected)
        self.assertIn({i, j}, disconnected)

        state.addToGroup(b, g1)

        self.assertEqual(list(state.generateDisconnectedGroups(g1)), [])
        self.assertEqual(list(state.generateDisconnectedGroups(g2)), [{i, j}])


class PrintTests(unittest.TestCase):
    def test_percent(self):
        for numGroups in range(1, 4):
            state = logic.State(numGroups, "T1", "test")
            self.assertEqual(logic.percent(state, 0), "0.00%")
            self.assertEqual(logic.percent(state, 45), "100.00%")
            self.assertEqual(logic.percent(state, 7), "15.56%")

    def test_numWithPercent(self):
        for numGroups in range(1, 4):
            state = logic.State(numGroups, "T1", "test")
            self.assertEqual(logic.numWithPercent(state, 0), "0.00 (0.00%)")
            self.assertEqual(logic.numWithPercent(state, 45), "45.00 (100.00%)")
            self.assertEqual(logic.numWithPercent(state, 7), "7.00 (15.56%)")

    def test_infoDumpStrs(self):
        # Just confirming no crashes
        for numGroups in range(1, 4):
            state = logic.State(numGroups, "T1", "test")
            stats = logic.getStatStr(state)
            placements = logic.getPlacementStr(state)


class SolverTests(unittest.TestCase):
    @unittest.skip("TODO bring this in line with the new sorter")
    def test_sorter(self):
        state = logic.State(6, "T1", "test")
        (a, b, c, d, e, f, g, h, i, j) = state.placements.keys()
        (g1, g2, g3, g4, g5, g6) = state.groups
        # Sorted in order of metric, except j which would be too large and is deprioritized
        self.assertEqual(
            sorted(state.placements, key=lambda unit: logic.sorter(state, g1, unit), reverse=True),
            [i, h, g, f, e, d, c, b, a, j],
        )
        state.addToGroup(i, g1)
        # Sorted in order of metric, except j, and i which is placed
        self.assertEqual(
            sorted(state.placements, key=lambda unit: logic.sorter(state, g2, unit), reverse=True),
            [h, g, f, e, d, c, b, a, j, i],
        )

    # TODO: test more complex scenarios
    def test_getNext(self):
        state = logic.State(1, "T1", "test")
        (a, b, c, d, e, f, g, h, i, j) = state.placements.keys()
        expected = {
            1: {"unit": [j, i, h], "group": [0, 0, 0]},
            2: {"unit": [j, i, h], "group": [0, 1, 1]},
            3: {"unit": [j, i, h], "group": [0, 1, 2]},
        }
        for numGroup, vals in expected.items():
            state = logic.State(numGroup, "T1", "test")
            for i in range(3):
                u, gr = next(logic.getNext(state))
                self.assertIsNotNone(u)
                self.assertEqual(u, vals["unit"][i])
                self.assertEqual(gr, state.groups[vals["group"][i]])
                if u:
                    state.addToGroup(u, gr)

    # TODO: test more complex scenarios
    def test_singleGroup(self):
        state = logic.solve(1, "T1", "test")
        (a, b, c, d, e, f, g, h, i, j) = state.placements.keys()
        self.assertEqual(state.placements, {a: 1, b: 1, c: 1, d: 1, e: 1, f: 1, g: 1, h: 1, i: 1, j: 1})

    def test_valgrind(self):
        def getNextParam():
            for scale in ["states"]:  # ds.scales:
                for numGroup in range(1, 6):
                    for metricID in ds.metricNames(scale):
                        yield numGroup, metricID, scale

        for state in starmap(logic.solve, getNextParam()):
            self.assertEqual(
                state.unplacedUnits, [], f"Not all placed for {state.metricID}, {state.scale}, {len(state.groups)}"
            )
            for g in state.groups:
                self.assertLess(
                    g.metric,
                    state.avgGroupMetric * 1.315,
                    f"Group {g.index} incorrectly sized for {state.metricID}, {state.scale}, {len(state.groups)}",
                )

                self.assertTrue(
                    g.isContiguous,
                    f"Group {g.index} discontiguous for {state.metricID}, {state.scale}, {len(state.groups)}",
                )


if __name__ == "__main__":
    unittest.main()
