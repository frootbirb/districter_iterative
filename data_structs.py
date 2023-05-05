import sys
import csv
from typing import Iterator, Callable
from os import get_terminal_size as term_size

# --- Globals ----------------------------------------------------------------------------------------------------------

scales = ["states", "counties"]

_unitlists: dict[str, list["Unit"]] = {}
_metricNames: dict[str, list[str]] = {}


def unitlist(scale: str) -> list:
    global _unitlists, _metricNames
    try:
        return _unitlists[scale]
    except:
        _unitlists[scale], _metricNames[scale] = readFile(scale)
        return _unitlists[scale]


def metricNames(scale: str) -> list[str]:
    global _unitlists, _metricNames
    try:
        return _metricNames[scale]
    except:
        _unitlists[scale], _metricNames[scale] = readFile(scale)
        return _metricNames[scale]


_converters: dict[str, dict[str, str]] = {}


def abbrev_to_name(scale: str) -> dict[str, str]:
    global _converters
    try:
        return _converters[scale]
    except:
        _converters[scale] = __import__(
            f"assets.{scale}.name_to_abbrev", globals(), locals(), ["abbrev_to_name"]
        ).abbrev_to_name
        return _converters[scale]


# --- Data structures --------------------------------------------------------------------------------------------------


class Unit:
    def __init__(self, code: str, metrics: dict[str, float], scale: str):
        self.code = code
        self.metrics = metrics
        self.adj = set[Unit]()
        self.name = abbrev_to_name(scale)[code]
        self.hash = hash(code)
        self.distances = dict[Unit, int]()
        self.metric = metrics[next(iter(metrics))]

    def setCurrentMetric(self, metricID: str) -> None:
        self.metric = self.metrics[metricID]

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return self.code

    def __eq__(self, other: "str | Unit") -> bool:
        return self.code == other

    def __hash__(self) -> int:
        return self.hash


class Group:
    def __init__(self, index: int) -> None:
        self.units = set[Unit]()
        self.adj = set[Unit]()
        self.metric = 0
        self.index = index
        self.distanceSum = {}

    def __gt__(self, other: "Group") -> bool:
        return self.metric > other.metric

    @property
    def empty(self) -> bool:
        return len(self.units) == 0

    @property
    def isContiguous(self) -> bool:
        units = set(self.units)
        zones = []
        while units:
            starter = list(units)[0]
            zone = {starter}
            toCheck = {starter}
            while toCheck:
                next = toCheck.pop()
                zone.add(next)
                units.remove(next)
                toCheck = ((next.adj & self.units) - zone) | toCheck
            zones.append(zone)

        def firstOf(zone: int) -> Unit:
            return list(zones[zone])[0]

        return all(
            all(firstOf(i) not in firstOf(j).distances for j in range(i + 1, len(zones))) for i in range(len(zones))
        )

    # TODO: hyper-optimize this. Fully half of our time is spent in this one method
    def addUnit(self, unit: Unit):
        # append the unit into this group
        self.units.add(unit)
        # add the unit's metric to the group's metric
        self.metric += unit.metric
        # remove this unit from the adjacency list
        self.adj.discard(unit)
        # for each adjacent unit, add it to the adjacency list if it's not already in the group
        self.adj |= unit.adj - self.units
        for u, dist in unit.distances.items():
            if dist != 0:
                self.distanceSum[u] = dist + self.distanceSum.get(u, 0)

    def removeUnit(self, unit: Unit):
        # remove the unit from this group
        self.units.remove(unit)
        # remove the unit's metric from the group's metric
        self.metric -= unit.metric
        # if this unit is adjacent to the group, add it to the adjacency list
        if any(adjunit in self.units for adjunit in unit.adj):
            self.adj.add(unit)
        # remove units that are no longer adjacent
        for adjunit in unit.adj - self.units:
            if all(u not in self.units for u in adjunit.adj):
                self.adj.remove(adjunit)
        for u, dist in unit.distances.items():
            if self.distanceSum[u] == dist:
                self.distanceSum.pop(u)
            else:
                self.distanceSum[u] -= dist

    def canLose(self, unit: Unit) -> bool:
        border = unit.adj & self.units
        if not border:
            return True
        toCheck = {border.pop()}
        while toCheck:
            selected = toCheck.pop()
            border.discard(selected)
            toCheck |= selected.adj & border

        # If we can reach all the adjacent groups, we're good
        return len(border) == 0


class State:
    @staticmethod
    def parseScale(scale: str | int) -> str:
        # Enable MetricID to be set as a string or an index
        if isinstance(scale, str):
            return scale
        elif isinstance(scale, int):
            return scales[scale]

    @staticmethod
    def parseMetricID(scale: str, metricID: str | int) -> str:
        # Enable MetricID to be set as a string or an index
        if isinstance(metricID, str):
            return metricID
        elif isinstance(metricID, int):
            return metricNames(scale)[metricID]

    def __init__(
        self,
        numGroup: int,
        metricID: str | int,
        scale: str | int,
        callback: Callable[[str, int], None] | None = None,
    ):
        self.scale = State.parseScale(scale)
        self.metricID = State.parseMetricID(self.scale, metricID)

        self._callback = callback

        for unit in unitlist(self.scale):
            unit.setCurrentMetric(self.metricID)

        self.placements = {unit: 0 for unit in unitlist(self.scale)}
        self.unplacedUnits = sorted(unitlist(self.scale), key=lambda unit: unit.metric, reverse=True)
        self.groups = [Group(i + 1) for i in range(numGroup)]

        unitMetrics = [unit.metric for unit in unitlist(self.scale)]
        self.sumUnitMetrics = sum(unitMetrics)
        equalSplit = self.sumUnitMetrics / numGroup
        largestUnitMetric = max(unitMetrics)
        # The maximum acceptable size is 105% of an even split, or the largest single unit
        self.maxAcceptableMetric = max(equalSplit * 1.05, largestUnitMetric)
        # The minimum acceptable size is 95% of an even split
        self.minAcceptableMetric = equalSplit * 0.95

    def addToGroup(self, unit: Unit, group: Group):
        group.addUnit(unit)
        if (placement := self.placements[unit]) == 0:
            self.unplacedUnits.remove(unit)
        else:
            self.groups[placement - 1].removeUnit(unit)
        self.placements[unit] = group.index
        if self._callback:
            self._callback(unit.code, group.index)

    def getGroupFor(self, unit: Unit) -> Group:
        return self.groups[self.placements[unit] - 1]

    def hasAnyUnplacedAdjacent(self, group: Group) -> bool:
        return any(self.placements[unit] == 0 for unit in group.adj)

    # TODO: make this faster
    def generateDisconnectedGroups(self, group: Group) -> Iterator[set[Unit]]:
        # Get all units adjacent to the current group which are not in a group
        borders = []
        invalid = set()
        placed = set()
        for seed in group.adj:
            if self.placements[seed] != 0 or seed in invalid or seed in placed:
                continue

            newDisconnect = {seed}
            toCheck = set(seed.adj)
            while len(toCheck) > 0:
                unit = toCheck.pop()

                # We've hit one of our invalid groups or a placed unit - throw out this group
                if unit in invalid or (place := self.placements[unit]) != 0 and place != group.index:
                    invalid |= newDisconnect
                    newDisconnect = None
                    break
                # This unit is unplaced
                elif place == 0:
                    newDisconnect.add(unit)
                    toCheck |= unit.adj - newDisconnect

            if newDisconnect:
                borders.append(newDisconnect)
                placed |= newDisconnect

        for border in borders:
            yield border


# --- Helper file reading function -------------------------------------------------------------------------------------


def getDistanceStep(startUnit: Unit, units: dict[str, Unit]) -> dict[Unit, int]:
    distances = {startUnit: 0}
    dist = 1
    lastRow = [startUnit]
    while lastRow:
        changed = []
        for unit in lastRow:
            for adjUnit in (code for code in unit.adj if code not in distances):
                distances[adjUnit] = dist
                changed.append(adjUnit)
        dist += 1
        lastRow = changed
        print(f"Calculating distances: {100 * list(units.keys()).index(startUnit.code) / len(units):10.4f}%", end="\r")

    distances.pop(startUnit)
    return distances


def populateDistances(scale: str, units: dict[str, Unit]) -> dict[str, Unit]:
    # Attempt to read in distance
    try:
        with open(f"assets/{scale}/distance.csv", encoding="utf8", newline="") as csvfile:
            for row in csv.DictReader(csvfile, delimiter=","):
                name = row.pop("name")
                units[name].distances = {units[code]: int(dist) for code, dist in row.items() if dist}
    except:
        for _, unit in units.items():
            unit.distances = getDistanceStep(unit, units)
        print(f"Calculating distances: {100:10.4f}%")
        with open(f"assets/{scale}/distance.csv", "w", encoding="utf8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=",", fieldnames=["name"] + list(units.keys()))
            writer.writeheader()
            for unit in units.values():
                newRow = {u.code: str(dist) for u, dist in unit.distances.items()}
                newRow["name"] = unit.code
                writer.writerow(newRow)

    return units


def readFile(scale: str) -> tuple[list[Unit], list[str]]:
    # Read in adjacency
    adj = {}
    with open(f"assets/{scale}/adjacency.csv", encoding="utf8", newline="") as csvfile:
        for row in csv.reader(csvfile, delimiter=","):
            adj[row[0]] = row[1:]

    # Read in units
    units = {}
    metricNames: list[str] = []
    with open(f"assets/{scale}/data.tsv", encoding="utf8", newline="") as csvfile:
        for row in csv.DictReader(csvfile, delimiter="\t"):
            if not metricNames:
                metricNames = list(filter(lambda k: k != "Unit", row.keys()))
            code = row["Unit"]
            # Skip the Totals row
            if code == "Total":
                continue
            # add the unit and metrics
            unitMetrics = {
                key: float(value.strip().replace(",", "")) for (key, value) in row.items() if key in metricNames
            }
            units[code] = Unit(code, unitMetrics, scale)

    # Put adjacency in the units
    for unit in units.values():
        for adjacent in adj[unit]:
            unit.adj.add(units[adjacent])

    populateDistances(scale, units)

    sys.setrecursionlimit(max(len(units), 1000))

    return sorted(units.values(), key=lambda u: u.code), metricNames
