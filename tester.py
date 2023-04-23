import cProfile
import pstats
from multiprocessing import Pool
from logic_iterative import solve, Globals

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


def getNextParam(scale, range):
    for numGroup in range:
        for metricID in Globals.allowed:
            yield numGroup, metricID, scale


def doTests(scale, range):
    Globals.set(0, scale=scale)
    for numGroup, metricID, scale in getNextParam(scale, range):
        print("Created {} groups with criteria {}".format(numGroup, metricID))
        solve(numGroup, metricID, scale)


def doParallelTests(scale, range):
    Globals.set(0, scale=scale)
    with Pool(8) as p:
        p.starmap(solve, getNextParam(scale, range))

def stepthrough(numGroup, metricID, scale):
    callback = lambda data: input([i[0]+": "+i[2] for i in sorted(data, key=lambda i: (i[2], i[0])) if i[2] != '0'])
    solve(numGroup, metricID, scale, callback)

if __name__ == "__main__":
    profile("doTests(0, range(1,6))")
