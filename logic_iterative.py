from os import get_terminal_size as term_size

from data_structs import State, Unit, Group
from itertools import chain
from typing import Callable, Iterator, Iterable

# --- Solver -----------------------------------------------------------------------------------------------------------

doprint = False


def sorter(state: State, group: Group, unit: Unit) -> tuple:
    return (
        # Prioritize more neighbors in this group
        len(unit.adj & group.units),
        # Prioritize fewer unplaced neighbors
        -len(unit.adj & state.unplacedUnits),
        # Prioritize units that bring this group as close as possible to the average
        -abs(state.avgGroupMetric - unit.metric - group.metric),
    )


def getPlaceableUnitsFor(state: State, group: Group) -> Iterator[Unit]:
    if group.empty:
        return iter(state.unplacedUnits)
    else:
        return chain(
            (group.adj & state.unplacedUnits),
            (unit for unit in state.unplacedUnits if all(u not in unit.distances for u in group.units)),
        )


def getNext(state: State) -> Iterator[tuple[Unit, Group]]:
    unit = max(state.unplacedUnits, key=lambda u: u.metric)
    group = state.groups[0]

    # print(f"Placed {unit} into {group.index} ({len(state.unplacedUnits)} remaining)")
    yield unit, group

    while state.unplacedUnits:
        if group.metric > state.avgGroupMetric:
            group = state.groups[group.index]

        unit = max(set(state.unplacedUnits), key=lambda u: sorter(state, group, u))

        yield unit, group
        # print(f"Placed {unit} into {group.index} ({len(state.unplacedUnits)} remaining)")


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
            for unplacedUnits in state.generateDisconnectedGroups(group):
                if doprint:
                    unplacedCount = len(unplacedUnits)
                    longEnough = term_size().columns > unplacedCount * 4 + 12
                    print(f"{group.index}: enclosed {unplacedUnits if longEnough else f'{unplacedCount} units'}")
                for unplaced in unplacedUnits:
                    state.addToGroup(unplaced, group)
                if doprint:
                    printState(state)

        return state, unit, group.index, prevPlacement

    return state, None, None, None


def recurse(state: State, ineligible: set[tuple[Unit, int]]) -> bool:
    if not state.unplacedUnits:
        if all(g.isContiguous for g in state.groups):
            return True
        else:
            print("   NON CONTIGUOUS")
            return False

    if any((g := group).metric < state.avgGroupMetric for group in state.groups):
        for u in sorted(getPlaceableUnitsFor(state, g), key=lambda u: abs(state.avgGroupMetric - u.metric - g.metric)):
            if not (u, g.index) in ineligible:
                state.addToGroup(u, g)
                print(f"Placed {u} into {g.index} {joinedUnits(g.units)}")
                if recurse(state, set(ineligible)):
                    return True
                else:
                    state.removeFromGroup(u, g)
                    ineligible.add((u, g.index))
                    print(f" Removed {u} from {g.index} {joinedUnits(g.units)}")

        input(
            f"   NO ELIGIBLE UNITS FOR GROUP {g.index}: {joinedUnits(g.units)}\n"
            f"   Adjacent unplaced units: {joinedUnits(g.adj & state.unplacedUnits)}\n"
            f"   Adjacent units: {'|'.join(f'{unit}:{state.placements[unit]}' for unit in g.adj)}\n"
            f"   All unplaced ({len(state.unplacedUnits)}): {joinedUnits(state.unplacedUnits)}\n"
            f"   Ineligible: {'|'.join(f'{unit}:{placement}' for unit, placement in ineligible)}"
        )

    return False


def solve(
    numGroup: int, metricID: str | int = 0, scale: str | int = 0, callback: Callable[[str, int], None] | None = None
) -> State:
    # Start the solver!
    state: State = State(numGroup=numGroup, metricID=metricID, scale=scale, callback=callback)
    recurse(state, set())
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
