import cProfile
import pstats
from multiprocessing import Pool
import logic_iterative as logic
import data_structs as ds

# --- Profiler ---------------------------------------------------------------------------------------------------------


def printUnitTestMap():
    print(
        f"+---+  +-----+-----+\n"
        f"| A |  |  B  |  C  |\n"
        f"+---+  +---+-+-+---+\n"
        f"| D |  | E | F | G |\n"
        f"+---+  +---+-+-+---+\n"
        f"             |  H  |\n"
        f"           +-+-----+\n"
        f"           | I | J |\n"
        f"           +---+---+"
    )


def printUnitTestPlacements(state: logic.State):
    p = state.placements
    print(
        f"+---+  +-----+-----+\n"
        f"| {p['A']} |  |  {p['B']}  |  {p['C']}  |\n"
        f"+---+  +---+-+-+---+\n"
        f"| {p['D']} |  | {p['E']} | {p['F']} | {p['G']} |\n"
        f"+---+  +---+-+-+---+\n"
        f"             |  {p['H']}  |\n"
        f"           +-+-----+\n"
        f"           | {p['I']} | {p['J']} |\n"
        f"           +---+---+"
    )


def profile(string: str):
    filename = "stats.profile"
    cProfile.run(string, filename)
    stats = pstats.Stats(filename)
    stats.strip_dirs()
    stats.sort_stats("cumtime")
    stats.print_stats(10)
    print()
    stats.sort_stats("tottime")
    stats.print_stats(10)


def getNextParam(scale: str, range: range):
    for numGroup in range:
        for metricID in ds.metricNames(scale):
            yield numGroup, metricID, scale


def doTests(scale: str | int, range: range):
    scale = logic.State.parseScale(scale)
    for numGroup, metricID, scale in getNextParam(scale, range):
        print(f"Created {numGroup} groups with criteria {metricID}")
        ds.printResult(logic.solve(numGroup, metricID, scale))


def doParallelTests(scale: str | int, range: range):
    scale = logic.State.parseScale(scale)
    with Pool(8) as p:
        p.starmap(logic.solve, getNextParam(scale, range))


def stepthrough(numGroup: int, metricID: str | int, scale: str | int):
    def callback(s: str, i: int):
        input()

    logic.doprint = True
    logic.solve(numGroup, metricID, scale, callback)


if __name__ == "__main__":
    # printUnitTestMap()
    # printUnitTestPlacements(logic.solve(2, "T1", "test"))
    # stepthrough(3, "T1", "test")
    profile("doTests(1, range(1,6))")
