from data_structs import State, Unit, Group, Globals

# --- Solver -----------------------------------------------------------------------------------------------------------


def sorter(state: State, group: Group, unit: Unit):
    return (
        -state.isPlaced(unit),
        # Prioritize units that don't push this over the max metric
        unit.metric + group.metric > state.maxAcceptableMetric,
        # Prioritize stealing from a larger group
        state.getGroupFor(unit).metric,
        # Prioritize shorter distance
        -group.getAverageDistance(unit),
        unit.metric,
    )


def getNext(state: State) -> tuple[Unit, Group]:
    baseUnits = state.unplacedUnits[:]

    group = min(
        state.groups,
        key=lambda group: (
            # Prioritize groups that have at least one adjacent empty unit, are empty, or have no adjacent units at all
            -(state.hasAnyUnplacedAdjacent(group) or group.empty() or len(group.adj) == 0),
            group.metric,
        ),
    )

    # If one of the groups is too big, we will allow stealing from it
    for othergroup in state.groups:
        if othergroup.metric > state.maxAcceptableMetric or (
            othergroup.metric > group.metric and not state.hasAnyUnplacedAdjacent(group)
        ):
            baseUnits += {unit for unit in othergroup.units if othergroup.canLose(unit)}

    # Get the units which might be viable - unplaced units adjacent to a given group, or those with no adjacent, like AK
    if group.empty() or len(group.adj) == 0:
        units = baseUnits
    else:
        units = (unit for unit in baseUnits if (unit in group.adj or len(unit.adj) == 0))

    return (
        max(units, key=lambda unit: sorter(state, group, unit)),
        group,
    )


def addToGroup(state: State, unit: Unit, group: Group) -> None:
    group.addUnit(unit)
    if (placement := state.placements.get(unit, 0)) == 0:
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
    for unit in filter(lambda unit: unit not in units, Globals.unitdict[seed].adj):
        if (placement := state.placements.get(unit, 0)) != 0:
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
doprint = False


def doStep(state: State) -> State:
    unit, group = getNext(state)

    if doprint:
        print("{}: Adding {}".format(group.index, unit))
        print("  Average distance {:.2f}".format(group.getAverageDistance(unit)))

    addToGroup(state, unit, group)

    if doprint:
        state.printState()

    # If every group has some adjacent units, we can start checking for enclosures
    if all(len(group.adj) > 0 for group in state.groups):
        for unplacedunits in generateDisconnectedGroups(state, group):
            if doprint:
                print("{}: enclosed {}".format(group.index, unplacedunits))
            for unplaced in unplacedunits:
                addToGroup(state, Globals.unitdict[unplaced], group)
            if doprint:
                state.printState()

    if Globals.callback:
        Globals.callback(state.getUpdateDataFrame())

    return state


def solve(numUnit, metricID=0, scale=0, callback=None) -> dict:
    Globals.set(metricID, scale, callback)

    # Start the solver!
    state = State(numUnit=numUnit)
    while len(state.unplacedUnits) != 0 or any(group.metric > state.maxAcceptableMetric for group in state.groups):
        state = doStep(state)

    state.printResult()


if __name__ == "__main__":
    solve(4, metricID="Area (mi2)")
