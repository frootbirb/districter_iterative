from os import get_terminal_size as term_size

from data_structs import State, Unit, Group
from itertools import chain
from typing import Callable, Iterator, Iterable

# --- Solver -----------------------------------------------------------------------------------------------------------

doprint = False


def sorter(state: State, group: Group, unit: Unit) -> tuple:
    return (
        # Prioritize unplaced units
        state.placements[unit] == 0,
        # Prioritize shorter distance
        -group.distanceSum.get(unit, float("inf")),
        # Prioritize units that bring this group as close as possible to the average
        -abs(state.avgGroupMetric - unit.metric - group.metric),
    )


def getPlaceableUnitsFor(state: State, group: Group) -> Iterator[Unit]:
    if group.empty:
        return iter(state.unplacedUnits)
    elif any(state.placements[u] == 0 for u in group.adj):
        return (unit for unit in group.adj if state.placements[unit] == 0)
    else:
        return chain(
            (unit for unit in group.adj if state.getGroupFor(unit).canLose(unit)),
            (unit for unit in state.unplacedUnits if all(u not in unit.distances for u in group.units)),
        )


def getNext(state: State) -> tuple[Unit | None, Group]:
    for group in sorted(
        state.groups,
        key=lambda group: (
            # Prioritize groups that have at least one adjacent empty unit, are empty, or have no adjacent units at all
            -(state.hasAnyUnplacedAdjacent(group) or group.empty or len(group.adj) == 0),
            group.metric,
        ),
    ):
        retMax = (
            max(getPlaceableUnitsFor(state, group), key=lambda unit: sorter(state, group, unit), default=None),
            group,
        )

        if retMax:
            return retMax

    return None, state.groups[0]


def doStep(state: State) -> tuple[State, Unit | None, int]:
    unit, group = getNext(state)

    if not unit:
        return state, unit, 0

    if doprint:
        if (placement := state.placements[unit]) == 0:
            print(f"{group.index}: Adding {unit}")
        else:
            print(f"{group.index}: Stealing {unit} from {placement}")

    state.addToGroup(unit, group)

    if doprint:
        print(getPlacementStr(state))

    # If half the units are placed, we can start checking for enclosures
    if len(state.unplacedUnits) * 2 < len(state.placements):
        for unplacedUnits in state.generateDisconnectedGroups(group):
            if doprint:
                unplacedCount = len(unplacedUnits)
                longEnough = term_size().columns > unplacedCount * 4 + 12
                print(f"{group.index}: enclosed {unplacedUnits if longEnough else f'{unplacedCount} units'}")
            for unplaced in unplacedUnits:
                state.addToGroup(unplaced, group)
            if doprint:
                printState(state)

    return state, unit, group.index


def solve(
    numGroup: int, metricID: str | int = 0, scale: str | int = 0, callback: Callable[[str, int], None] | None = None
) -> State:
    # Start the solver!
    state = State(numGroup=numGroup, metricID=metricID, scale=scale, callback=callback)
    previousMoves = []
    last = (0, 0)
    while (
        len(state.unplacedUnits) != 0
        or any(group.metric < state.avgGroupMetric - state.deviation for group in state.groups)
    ) and last not in previousMoves:
        previousMoves.insert(0, last)
        if len(previousMoves) > 5:
            previousMoves.pop()

        state, *last = doStep(state)

    return state


# --- Printing methods -------------------------------------------------------------------------------------------------


def percent(state: State, val: float) -> str:
    return f"{100 * val / state.sumUnitMetrics:.2f}%"


def numWithPercent(state: State, val: float) -> str:
    return f"{val:,.2f} ({percent(state, val)})"


def joinedUnits(units: Iterable[Unit]) -> str:
    return "|".join(sorted(unit.code for unit in units))


def getStatStr(state: State) -> str:
    return (
        f"--------------- + {'Complete' if len(state.unplacedUnits) == 0 else 'Failure'} + ---------------\n"
        f"Created {len(state.groups)} groups of {state.scale} with criteria {state.metricID}\n"
        + (
            f"Final spread: "
            f"{numWithPercent(state, (largest := max(state.groups).metric) - (smallest := min(state.groups).metric))}, "
            f"from {numWithPercent(state, smallest)} to {numWithPercent(state, largest)}\n"
            if len(state.groups) > 1
            else ""
        )
        + f"Acceptable sizes: {numWithPercent(state, state.avgGroupMetric - state.deviation)} "
        f"to {numWithPercent(state, state.avgGroupMetric + state.deviation)}"
    )


def getPlacementStr(state: State) -> str:
    results = []
    for group in sorted(state.groups, reverse=True):
        results.append(
            (
                f"Group {group.index}",
                percent(state, group.metric),
                joinedUnits(group.units),
                f"{(count := len(group.units))} units ({100 * (count / len(state.placements)):.2f}% of total)",
            )
        )

    if (count := len(state.unplacedUnits)) > 0:
        results.append(
            (
                "Unplaced",
                percent(state, sum(unit.metric for unit in state.unplacedUnits)),
                joinedUnits(state.unplacedUnits),
                f"{count} units ({100 * (count / len(state.placements)):.2f}% of total)",
            )
        )

    length = len(max(results, key=lambda item: len(item[0]))[0])
    max_unit_space = term_size().columns - (length + 12)
    return "\n".join(
        f" {name:{str(length)}} ({pct:6}): {units if len(units) < max_unit_space else summary}"
        for (name, pct, units, summary) in results
    )


def printState(state: State):
    print(getStatStr(state))
    print(getPlacementStr(state))
    print()


if __name__ == "__main__":
    state = solve(5, "Area (mi2)", scale=0)
    printState(state)

    for g in state.groups:
        print(joinedUnits(getPlaceableUnitsFor(state, g)))
