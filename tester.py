import cProfile
import pstats
from multiprocessing import Pool
import logic_iterative as logic
from data_structs import metricNames, State

# --- Profiler ---------------------------------------------------------------------------------------------------------


def profile(string):
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
        for metricID in metricNames(scale):
            yield numGroup, metricID, scale


def doTests(scale: str | int, range: range):
    scale = State.parseScale(scale)
    for numGroup, metricID, scale in getNextParam(scale, range):
        print(f"Created {numGroup} groups with criteria {metricID}")
        logic.solve(numGroup, metricID, scale).printResult()


def doParallelTests(scale: str | int, range: range):
    scale = State.parseScale(scale)
    with Pool(8) as p:
        p.starmap(logic.solve, getNextParam(scale, range))


def stepthrough(numGroup: int, metricID: str | int, scale: str | int):
    callback = lambda _: input()
    logic.doprint = True
    logic.solve(numGroup, metricID, scale, callback)


if __name__ == "__main__":
    profile("doTests(0, range(1,6))")
