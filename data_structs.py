import sys
import csv
from os import get_terminal_size as term_size

import assets.states.name_to_abbrev as state_converter
import assets.counties.name_to_abbrev as county_converter

# --- Globals ----------------------------------------------------------------------------------------------------------

scales = ["states", "counties"]

_unitlistStates: list
_unitlistCounties: list


def unitlist(scale: str) -> list:
    global _unitlistStates, _unitlistCounties
    if scale == "states":
        try:
            return _unitlistStates
        except:
            _unitlistStates = readFile(scale)
            return _unitlistStates
    elif scale == "counties":
        try:
            return _unitlistCounties
        except:
            _unitlistCounties = readFile(scale)
            return _unitlistCounties
    else:
        return []


def metricNames(scale: str) -> list[str]:
    if scale == "states":
        return ["Population", "Firearms", "Area (mi2)", "Land (mi2)", "GDP ($1m)", "Food ($1k)"]
    elif scale == "counties":
        return ["Population"]
    else:
        return []


def abbrev_to_name(scale: str) -> dict[str, str]:
    if scale == "states":
        return state_converter.abbrev_to_name
    elif scale == "counties":
        return county_converter.abbrev_to_name
    else:
        return {}


# --- Data structures --------------------------------------------------------------------------------------------------


class Unit:
    def __init__(self, code: str, metrics: dict[str, int], scale: str):
        self.code = code
        self.metrics = metrics
        self.adj = set()
        self.name = abbrev_to_name(scale)[code]
        self.hash = hash(code)
        self.distances = {}
        self.metric = self.metrics[metricNames(scale)[0]]

    def setCurrentMetric(self, metricID: str) -> None:
        self.metric = self.metrics[metricID]

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return self.code

    def __eq__(self, other) -> bool:
        return self.code == other

    def __hash__(self) -> int:
        return self.hash


class Group:
    def __init__(self, index: int) -> None:
        self.units = set()
        self.adj = set()
        self.metric = 0
        self.index = index
        self.distances = {}

    def __gt__(self, other) -> bool:
        return self.metric > other.metric

    def empty(self) -> bool:
        return len(self.units) == 0

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
            if u in self.distances:
                self.distances[u] += dist
            else:
                self.distances[u] = dist

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
            self.distances[u] -= dist

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

    def __init__(self, numGroup: int, metricID: str | int, scale: str | int, callback=None):
        self.scale = State.parseScale(scale)
        self.metricID = State.parseMetricID(self.scale, metricID)

        self.callback = callback

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

    def getGroupFor(self, unit: Unit) -> Group:
        return self.groups[self.placements[unit] - 1]

    def hasAnyUnplacedAdjacent(self, group: Group) -> bool:
        return any(self.placements[unit] == 0 for unit in group.adj)

    def getDummyData(self) -> dict[str, list[str]]:
        result = {new_list: [] for new_list in ["unit", "code", "group", "metric"]}
        for unit in unitlist(self.scale):
            result["unit"].append(unit.name)
            result["code"].append(unit.code)
            result["group"].append("0")
            result["metric"].append(unit.metric)

        return result

    def getCurrentData(self) -> dict[str, list[str]]:
        result = self.getDummyData()

        for placement in self.placements.values():
            result["group"][2] = str(placement)

        return result

    def getUpdateData(self) -> list[tuple[str, int, str]]:
        return [(unit.name, unit.metric, str(self.placements[unit])) for unit in unitlist(self.scale)]

    def getDummyUpdateData(self) -> list[tuple[str, int, str]]:
        return [(unit.name, unit.metric, "0") for unit in unitlist(self.scale)]

    def __percent(self, val: float) -> str:
        return f"{100 * val / self.sumUnitMetrics:.2f}%"

    def __numWithPercent(self, val: float) -> str:
        return f"{val:,.2f} ({self.__percent(val)})"

    def printResult(self):
        print(f"--------------- + {'Complete' if len(self.unplacedUnits) == 0 else 'Failure'} + ---------------")
        print(f"Created {len(self.groups)} groups of {self.scale} with criteria {self.metricID}")
        if len(self.groups) > 1:
            smallest = min(self.groups).metric
            largest = max(self.groups).metric
            print(
                f"Final spread: {self.__numWithPercent(largest - smallest)}, "
                + f"from {self.__numWithPercent(smallest)} to {self.__numWithPercent(largest)}"
            )
        print(
            f"Acceptable sizes: {self.__numWithPercent(self.minAcceptableMetric)} "
            + f"to {self.__numWithPercent(self.maxAcceptableMetric)}"
        )
        self.printState()

    def printState(self):
        results = []
        for group in sorted(self.groups, reverse=True):
            results.append(
                (
                    f"Group {group.index}",
                    self.__percent(group.metric),
                    "|".join(sorted(unit.code for unit in group.units)),
                    f"{(count := len(group.units))} units ({100 * (count / len(unitlist(self.scale))):.2f}% of total)",
                )
            )

        if (count := len(self.unplacedUnits)) > 0:
            results.append(
                (
                    "Unplaced",
                    self.__percent(sum(unit.metric for unit in self.unplacedUnits)),
                    "|".join(sorted(unit.code for unit in self.unplacedUnits)),
                    f"{count} units ({100 * (count / len(unitlist(self.scale))):.2f}% of total)",
                )
            )

        length = len(max(results, key=lambda item: len(item[0]))[0])
        max_unit_space = term_size().columns - (length + 11)
        for entry in results:
            (name, percent, units, summary) = entry
            print(f"{name:{str(length)}} ({percent:6}): {units if len(units) < max_unit_space else summary}")
        print()


# --- Helper file reading function -------------------------------------------------------------------------------------


def getDistanceStep(startUnit: Unit, units: dict[str, Unit]) -> dict[Unit, int]:
    distances = {startUnit: 0}
    dist = 1
    lastRow = [startUnit]
    while lastRow:
        changed = []
        for unit in lastRow:
            for adjUnit in (units[code] for code in unit.adj if code not in distances):
                distances[adjUnit] = dist
                changed.append(adjUnit)
        dist += 1
        lastRow = changed
        print(f"Calculating distances: {100 * list(units.keys()).index(startUnit.code) / len(units):10.4f}%", end="\r")

    return distances


def populateDistances(scale: str, units: dict[str, Unit]) -> dict[str, Unit]:
    # Attempt to read in distance
    try:
        with open(f"assets/{scale}/distance.csv", encoding="utf8", newline="") as csvfile:
            for row in csv.DictReader(csvfile, delimiter=","):
                name = row.pop("name")
                units[name].distances = {code: int(dist) for code, dist in row.items() if dist}
    except:
        for _, unit in units.items():
            unit.distances = getDistanceStep(unit, units)
        print()
        with open(f"assets/{scale}/distance.csv", "w", encoding="utf8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=",", fieldnames=["name"] + list(units.keys()))
            writer.writeheader()
            for unit in units.values():
                newRow = unit.distances.copy()
                newRow["name"] = unit.code
                writer.writerow(newRow)

    return units


def readFile(scale: str) -> list[Unit]:
    # Read in adjacency
    adj = {}
    with open(f"assets/{scale}/adjacency.csv", encoding="utf8", newline="") as csvfile:
        for row in csv.reader(csvfile, delimiter=","):
            adj[row[0]] = row[1:]

    # Read in units
    units = {}
    with open(f"assets/{scale}/data.tsv", encoding="utf8", newline="") as csvfile:
        for row in csv.DictReader(csvfile, delimiter="\t"):
            code = row["Unit"]
            # Skip the Totals row
            if code == "Total":
                continue
            # add the unit and metrics
            unitMetrics = {
                key: int(value.strip().replace(",", "")) for (key, value) in row.items() if key in metricNames(scale)
            }
            units[code] = Unit(code, unitMetrics, scale)

    # Put adjacency in the units
    for unit in units.values():
        for adjacent in adj[unit]:
            unit.adj.add(units[adjacent])

    populateDistances(scale, units)

    sys.setrecursionlimit(max(len(units), 1000))

    return sorted(units.values(), key=lambda u: u.code)
