from os import get_terminal_size as term_size

from data_structs import State, Unit, Group
from itertools import chain
from typing import Callable

# --- Solver -----------------------------------------------------------------------------------------------------------

doprint = False


def sorter(state: State, group: Group, unit: Unit) -> tuple:
    # TODO can this be optimized? Call methods less often, or cache?
    return (
        # Prioritize unplaced units
        state.placements[unit] == 0,
        # Prioritize units that don't push this over the max metric
        unit.metric + group.metric < state.maxAcceptableMetric,
        # Prioritize units that don't push the target under the minimum size
        (oldGroup := state.getGroupFor(unit)).metric - unit.metric > state.minAcceptableMetric,
        # Prioritize stealing from a larger group
        oldGroup.metric,
        # Prioritize shorter distance
        -group.distanceSum.get(unit, float("inf")),
        unit.metric,
    )


def getNext(state: State) -> tuple[Unit | None, Group]:
    group = min(
        state.groups,
        key=lambda group: (
            # Prioritize groups that have at least one adjacent empty unit, are empty, or have no adjacent units at all
            -(state.hasAnyUnplacedAdjacent(group) or group.empty or len(group.adj) == 0),
            group.metric,
        ),
    )

    # Get the units which might be viable
    if group.empty:
        units = state.unplacedUnits
    elif any(state.placements[u] == 0 for u in group.adj):
        units = (unit for unit in group.adj if state.placements[unit] == 0)
    else:
        units = chain(
            (unit for unit in group.adj if state.getGroupFor(unit).canLose(unit)),
            state.unplacedUnits,
        )

    return max(units, key=lambda unit: sorter(state, group, unit), default=None), group


def doStep(state: State) -> tuple[State, Unit | None, int]:
    unit, group = getNext(state)

    if not unit:
        return state, unit, group.index

    if doprint:
        if (placement := state.placements[unit]) == 0:
            print(f"{group.index}: Adding {unit}")
        else:
            print(f"{group.index}: Stealing {unit} from {placement}")

    state.addToGroup(unit, group)

    if doprint:
        printState(state)

    # If every group has some adjacent units, we can start checking for enclosures
    if all(len(group.adj) > 0 for group in state.groups):
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
        len(state.unplacedUnits) != 0 or any(group.metric < state.minAcceptableMetric for group in state.groups)
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
        + f"Acceptable sizes: {numWithPercent(state, state.minAcceptableMetric)} "
        f"to {numWithPercent(state, state.maxAcceptableMetric)}"
    )


def getPlacementStr(state: State) -> str:
    results = []
    for group in sorted(state.groups, reverse=True):
        results.append(
            (
                f"Group {group.index}",
                percent(state, group.metric),
                "|".join(sorted(unit.code for unit in group.units)),
                f"{(count := len(group.units))} units ({100 * (count / len(state.placements)):.2f}% of total)",
            )
        )

    if (count := len(state.unplacedUnits)) > 0:
        results.append(
            (
                "Unplaced",
                percent(state, sum(unit.metric for unit in state.unplacedUnits)),
                "|".join(sorted(unit.code for unit in state.unplacedUnits)),
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
    printState(solve(3, scale=0))
