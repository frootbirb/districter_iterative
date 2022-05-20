import cProfile
import pstats
from multiprocessing import Pool
from logic_iterative import getNext, solve, Globals

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


def getNextParam(scale):
    for numUnit in range(1, 8):
        for metricID in Globals.allowed:
            yield numUnit, metricID, scale


def doTests(scale):
    Globals.set(0, scale=scale)
    for numUnit, metricID, scale in getNextParam(scale):
        print("Created {} groups of {} with criteria {}".format(numUnit, scale, metricID))
        solve(numUnit, metricID, scale)


def doParallelTests(scale):
    Globals.set(0, scale=scale)
    with Pool(8) as p:
        p.starmap(solve, getNextParam(scale))


if __name__ == "__main__":
    profile("doTests(0)")
