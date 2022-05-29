from data_structs import State, Unit, Group, Globals
from itertools import chain

# --- Solver -----------------------------------------------------------------------------------------------------------

doprint = False


def sorter(state: State, group: Group, unit: Unit):
    oldGroup = state.getGroupFor(unit)
    # TODO can this be optimized? Call methods less often, or cache?
    return (
        # Prioritize unplaced units
        state.placements[unit] == 0,
        # Prioritize units that don't push this over the max metric
        unit.metric + group.metric < state.maxAcceptableMetric,
        # Prioritize units that don't push the target under the minimum size
        oldGroup.metric - unit.metric > state.minAcceptableMetric,
        # Prioritize stealing from a larger group
        oldGroup.metric,
        # Prioritize shorter distance
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
    elif any(state.placements[u] == 0 for u in group.adj):
        units = (unit for unit in group.adj if state.placements[unit] == 0)
    else:
        units = chain(
            (unit for unit in group.adj if state.placements[unit] == 0 or state.getGroupFor(unit).canLose(unit)),
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


def generateDisconnectedGroups(state: State, group: Group) -> set:
    # Get all units adjacent to the current group which are not in a group
    borders = []
    invalid = set()
    placed = set()
    biggest = max(Globals.unitlist, key=lambda u: u.metric)
    for seed in group.adj:
        if state.placements[seed] != 0 or seed in invalid or seed in placed:
            continue

        newDisconnect = {seed}
        toCheck = set(seed.adj)
        while len(toCheck) > 0:
            # TODO this is super slow - is it better to just not use it?
            unit = min(toCheck, key=lambda u: (u not in invalid, state.placements[u] == 0, u.distances[biggest]))
            toCheck.discard(unit)
            #unit = toCheck.pop()

            # We've hit one of our invalid groups or a placed unit - throw out this group
            if unit in invalid or (place := state.placements[unit]) != 0 and place != group.index:
                invalid |= newDisconnect
                newDisconnect = None
                break
            # This unit is unplaced
            elif place == 0:
                newDisconnect.add(unit)
                toCheck |= (unit.adj - newDisconnect)
        
        if newDisconnect:
            borders.append(newDisconnect)
            placed |= newDisconnect
    
    for border in borders:
        yield border


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

    return state, (unit, group.index)


def solve(numGroup, metricID=0, scale=0, callback=None) -> dict:
    Globals.set(metricID, scale, callback)

    # Start the solver!
    state = State(numGroup=numGroup)
    previousMoves = []
    last = (0,0)
    while (len(state.unplacedUnits) != 0 or any(group.metric < state.minAcceptableMetric for group in state.groups)) and last not in previousMoves:
        previousMoves.insert(0, last)
        if len(previousMoves) > 5:
            previousMoves.pop()

        state, last = doStep(state)

    state.printResult()


if __name__ == "__main__":
    solve(3, scale=0)