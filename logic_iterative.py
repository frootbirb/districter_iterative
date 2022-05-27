from data_structs import State, Unit, Group, Globals
from multiprocessing import Pool
from itertools import chain

# --- Solver -----------------------------------------------------------------------------------------------------------

doprint = False


def sorter(state: State, group: Group, unit: Unit):
    oldGroup = state.getGroupFor(unit)
    # TODO can this be optimized?
    return (
        # Prioritize unplaced units
        not state.isPlaced(unit),
        # Prioritize units that don't push this over the max metric
        unit.metric + group.metric < state.maxAcceptableMetric,
        # Prioritize units that don't push the target under the minimum size
        oldGroup.metric - unit.metric > state.minAcceptableMetric,
        # Prioritize stealing from a larger group
        oldGroup.metric,
        # Prioritize shorter distance
        #sum(1 for u in unit.adj if u in group.units),
        -group.getAverageDistance(unit),
        unit.metric,
    )


def getNext(state: State) -> tuple[Unit, Group]:

    group = min(
        state.groups,
        key=lambda group: (
            # Prioritize groups that have at least one adjacent empty unit, are empty, or have no adjacent units at all
            -(state.hasAnyUnplacedAdjacent(group) or group.empty() or len(group.adj) == 0),
            group.metric,
        ),
    )

    # Get the units which might be viable
    if group.empty():
        units = state.unplacedUnits
    elif any(not state.isPlaced(u) for u in group.adj):
        units = (unit for unit in group.adj if not state.isPlaced(unit))
    else:
        units = chain(
            (unit for unit in group.adj if not state.isPlaced(unit) or state.getGroupFor(unit).canLose(unit)),
            state.unplacedUnits,
        )

    return (max(units, key=lambda unit: sorter(state, group, unit)), group)


def addToGroup(state: State, unit: Unit, group: Group) -> None:
    group.addUnit(unit)
    if (placement := state.placements[unit]) == 0:
        state.unplacedUnits.remove(unit)
    else:
        state.groups[placement - 1].removeUnit(unit)
    state.placements[unit] = group.index


def removeFromGroup(state: State, unit: Unit, group: Group) -> None:
    state.unplacedUnits.append(unit)
    group.removeUnit(unit)
    state.placements[unit] = 0


def generateUnplaced(
    state: State, borders: set, seed: Unit = None, units: set = None, adjgroups: set = None
) -> tuple[set, set]:
    if not seed:
        seed = next(iter(borders))
    if not units:
        units = set()
    if not adjgroups:
        adjgroups = set()

    units.add(seed)
    for unit in filter(lambda unit: unit not in units, seed.adj):
        if (placement := state.placements[unit]) != 0:
            adjgroups.add(placement)
        else:
            downstream = generateUnplaced(state, borders, unit, units, adjgroups)
            units |= downstream[0]
            adjgroups |= downstream[1]

        # Shortcut out of the loop if we've seen at least two groups
        if len(adjgroups) > 1:
            return units, adjgroups

    return units, adjgroups


def generateDisconnectedGroups(state: State, group: Group) -> set:
    # Get all units adjacent to the current group which are not in a group
    borders = {unit for unit in group.adj if not state.isPlaced(unit)}

    while len(borders) > 0:
        unplaced, adjgroups = generateUnplaced(state, borders)
        borders -= unplaced
        if len(adjgroups) == 1:
            yield unplaced


g_callback = None


def doStep(state: State) -> State:
    unit, group = getNext(state)

    if doprint:
        print("{}: Adding {}".format(group.index, unit))

    addToGroup(state, unit, group)

    if doprint:
        state.printState()

    # If every group has some adjacent units, we can start checking for enclosures
    if all(len(group.adj) > 0 for group in state.groups):
        for unplacedunits in generateDisconnectedGroups(state, group):
            if doprint:
                unplacedCount = len(unplacedunits)
                if unplacedCount > Globals.printcap:
                    print("{}: enclosed {} units".format(group.index, unplacedCount))
                else:
                    print("{}: enclosed {}".format(group.index, unplacedunits))
            for unplaced in unplacedunits:
                addToGroup(state, unplaced, group)
            if doprint:
                state.printState()

    if Globals.callback:
        Globals.callback(state.getUpdateDataFrame())

    return state


def solve(numGroup, metricID=0, scale=0, callback=None) -> dict:
    Globals.set(metricID, scale, callback)

    # Start the solver!
    state = State(numGroup=numGroup)
    # todo: can this hinge on a "close enough"? e.g. when swapping a district flips the relative positions of two groups?
    while len(state.unplacedUnits) != 0 or any(group.metric > state.maxAcceptableMetric for group in state.groups):
        state = doStep(state)

    state.printResult()


if __name__ == "__main__":
    solve(2, scale=0)
