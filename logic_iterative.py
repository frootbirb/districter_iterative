from os import get_terminal_size as term_size
from itertools import chain
from typing import Callable, Iterable

from data_structs import State, Unit, Group

# --- Solver -----------------------------------------------------------------------------------------------------------

doprint = False


def sorter(state: State, group: Group, unit: Unit) -> tuple:
    return (
        # Prioritize unplaced units
        unit in state.unplacedUnits,
        # Prioritize shorter distance
        -group.distanceSum.get(unit, float("inf")),
        # Prioritize units that bring this group as close as possible to the average
        -abs(state.avgGroupMetric - unit.metric - group.metric),
    )


def getPlaceableUnitsFor(state: State, group: Group) -> Iterable[Unit]:
    if group.empty:
        return state.unplacedUnits
    elif unplacedAdjacent := group.adj & state.unplacedUnits:
        return unplacedAdjacent
    else:
        return chain(
            (unit for unit in group.adj if state.getGroupFor(unit).canLose(unit)),
            (unit for unit in state.unplacedUnits if all(u not in unit.distances for u in group.units)),
        )


def getNext(state: State) -> Iterable[tuple[Unit | None, Group]]:
    for group in sorted(
        state.groups,
        key=lambda group: (
            # Prioritize groups that have at least one adjacent empty unit, are empty, or have no adjacent units at all
            -(state.hasAnyUnplacedAdjacent(group) or group.empty or not group.adj),
            group.metric,
        ),
    ):
        for unit in sorted(
            getPlaceableUnitsFor(state, group), key=lambda unit: sorter(state, group, unit), reverse=True
        ):
            yield unit, group

    return None, state.groups[0]


def doStep(
    state: State, previousMoves: list[tuple[Unit, int, int]]
) -> tuple[State, None, None, None] | tuple[State, Unit, int, int]:
    for unit, group in getNext(state):
        if not unit:
            break
        elif (unit, (prevPlacement := state.placements[unit]), group.index) in previousMoves:
            break

        if doprint:
            if prevPlacement == 0:
                print(f"{group.index}: Adding {unit}")
            else:
                print(f"{group.index}: Stealing {unit} from {prevPlacement}")

        state.addToGroup(unit, group)

        if doprint:
            print(getPlacementStr(state))

        # If half the units are placed, we can start checking for enclosures
        if len(state.unplacedUnits) * 2 < len(state.placements):
            for disconnectedCount in state.generateDisconnectedGroups(group):
                if doprint:
                    unplacedCount = len(disconnectedCount)
                    longEnough = term_size().columns > unplacedCount * 4 + 12
                    print(f"{group.index}: enclosed {disconnectedCount if longEnough else f'{unplacedCount} units'}")
                for unplaced in disconnectedCount:
                    state.addToGroup(unplaced, group)
                if doprint:
                    printState(state)

        return state, unit, group.index, prevPlacement

    return state, None, None, None


def solve(
    numGroup: int, metricID: str | int = 0, scale: str | int = 0, callback: Callable[[str, int], None] | None = None
) -> State:
    # Start the solver!
    state: State = State(numGroup=numGroup, metricID=metricID, scale=scale, callback=callback)
    previousMoves: list[tuple[Unit, int, int]] = []
    while state.unplacedUnits or any(group.metric < state.avgGroupMetric - state.deviation for group in state.groups):
        state, unit, placement, prevPlacement = doStep(state, previousMoves)
        if not unit or not placement or prevPlacement == None:
            break

        previousMoves.append((unit, placement, prevPlacement))
        if len(previousMoves) > 5:
            previousMoves.pop(0)

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
        f"--------------- + {'Complete' if state.unplacedUnits else 'Failure'} + ---------------\n"
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
