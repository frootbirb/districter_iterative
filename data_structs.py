import sys
import csv

import assets.states.name_to_abbrev as state_converter
import assets.counties.name_to_abbrev as county_converter

# --- Globals ----------------------------------------------------------------------------------------------------------


class _Globals:
    metrics = ["Population", "Firearms", "Area (mi2)", "Land (mi2)", "GDP ($1m)", "Food ($1k)"]
    scales = ["states", "counties"]

    printcap = 31

    scale: str = ""
    metricID: str
    allowed: list
    callback = None

    unitlist: list
    abbrev_to_name: dict

    def set(self, metricID: str | int, scale: str | int, callback=None) -> None:
        # Enable MetricID to be set as a string or an index
        if isinstance(scale, str):
            newscale = scale
        elif isinstance(scale, int):
            newscale = self.scales[scale]

        scaleChanged = newscale != self.scale
        self.scale = newscale

        if self.scale == "states":
            self.banned = []
            self.abbrev_to_name = state_converter.abbrev_to_name
        elif self.scale == "counties":
            self.banned = ["Firearms", "Area (mi2)", "Land (mi2)", "GDP ($1m)", "Food ($1k)"]
            self.abbrev_to_name = county_converter.abbrev_to_name

        self.allowed = [metric for metric in self.metrics if metric not in self.banned]

        # Enable MetricID to be set as a string or an index
        if isinstance(metricID, str):
            self.metricID = metricID
        elif isinstance(metricID, int):
            self.metricID = self.allowed[metricID]

        if callback:
            self.callback = callback

        if scaleChanged:
            self.unitlist = readFile()
            self.biggest = max(self.unitlist, key=lambda u: u.metric)


globals = _Globals()


# --- Data structures --------------------------------------------------------------------------------------------------


class Unit:
    def __init__(self, code, metrics) -> None:
        self.code = code
        self.metrics = metrics
        self.adj = set()
        self.name = globals.abbrev_to_name[code]
        self.hash = hash(code)
        self.distances = {}

    @property
    def metric(self) -> int:
        return self.metrics[globals.metricID]

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return self.code

    def __eq__(self, other) -> bool:
        return self.code == other

    def __hash__(self) -> int:
        return self.hash


class Group:
    def __init__(self, index) -> None:
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
    def __init__(self, numGroup) -> None:
        self.placements = {unit: 0 for unit in globals.unitlist}
        self.unplacedUnits = sorted(globals.unitlist, key=lambda unit: unit.metric, reverse=True)
        self.groups = [Group(i + 1) for i in range(numGroup)]

        unitMetrics = [unit.metric for unit in globals.unitlist]
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

    def getPlacements(self):
        return {unit.code: self.placements[unit] for unit in globals.unitlist}

    def getDummyData(self):
        result = {new_list: [] for new_list in ["unit", "code", "group", "metric"]}
        for unit in globals.unitlist:
            result["unit"].append(unit.name)
            result["code"].append(unit.code)
            result["group"].append("0")
            result["metric"].append(unit.metric)

        return result

    def getCurrentData(self):
        result = self.getDummyData()

        for placement in self.placements.values():
            result["group"][2] = str(placement)

        return result

    def getUpdateData(self):
        return [[unit.name, unit.metric, str(self.placements[unit])] for unit in globals.unitlist]

    def getDummyUpdateData(self):
        return [[unit.name, unit.metric, "0"] for unit in globals.unitlist]

    def __percent(self, val: float) -> str:
        return "{:.2f}%".format(100 * val / self.sumUnitMetrics)

    def __numWithPercent(self, val: float) -> str:
        return "{:,.2f} ({})".format(val, self.__percent(val))

    def printResult(self):
        print("--------------- + " + ("Complete" if len(self.unplacedUnits) == 0 else "Failure") + " + ---------------")
        print("Created {} groups of {} with criteria {}".format(len(self.groups), globals.scale, globals.metricID))
        if len(self.groups) > 1:
            smallest = min(self.groups).metric
            largest = max(self.groups).metric
            print(
                "Final spread: {}, from {} to {}".format(
                    self.__numWithPercent(largest - smallest),
                    self.__numWithPercent(smallest),
                    self.__numWithPercent(largest),
                )
            )
        print(
            "Acceptable sizes: {} to {}".format(
                self.__numWithPercent(self.minAcceptableMetric),
                self.__numWithPercent(self.maxAcceptableMetric),
            )
        )
        self.printState()

    def printState(self):
        results = []
        for group in sorted(self.groups, reverse=True):
            count = len(group.units)
            results.append(
                (
                    "Group {}".format(group.index),
                    self.__percent(group.metric),
                    "{} ({:.2f}%)".format(count, 100 * (count / len(globals.unitlist)))
                    if count > globals.printcap
                    else "|".join(sorted(unit.code for unit in group.units)),
                )
            )

        if (count := len(self.unplacedUnits)) > 0:
            results.append(
                (
                    "Unplaced",
                    self.__percent(sum(unit.metric for unit in self.unplacedUnits)),
                    "{} units ({:.2f}% of total)".format(count, 100 * (count / len(globals.unitlist)))
                    if count > globals.printcap
                    else "|".join(sorted(unit.code for unit in self.unplacedUnits)),
                )
            )

        length = len(max(results, key=lambda item: len(item[0]))[0])
        for entry in results:
            print(("{:" + str(length) + "} ({}): {}").format(*entry))
        print()


# --- Helper file reading function -------------------------------------------------------------------------------------


def getDistanceStep(startUnit, units):
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
        print(
            "Calculating distances: {:10.4f}%".format(100 * list(units.keys()).index(startUnit) / len(units)),
            end="\r",
        )

    return distances


def populateDistances(units):
    # Attempt to read in distance
    try:
        with open("assets/" + globals.scale + "/distance.csv", encoding="utf8", newline="") as csvfile:
            for row in csv.DictReader(csvfile, delimiter=","):
                name = row.pop("name")
                units[name].distances = {code: int(dist) for code, dist in row.items() if dist}
    except:
        for _, unit in units.items():
            unit.distances = getDistanceStep(unit, units)
        print()
        with open("assets/" + globals.scale + "/distance.csv", "w", encoding="utf8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=",", fieldnames=["name"] + list(units.keys()))
            writer.writeheader()
            for unit in units.values():
                newRow = unit.distances.copy()
                newRow["name"] = unit.code
                writer.writerow(newRow)


def readFile():
    # Read in adjacency
    adj = {}
    with open("assets/" + globals.scale + "/adjacency.csv", encoding="utf8", newline="") as csvfile:
        for row in csv.reader(csvfile, delimiter=","):
            adj[row[0]] = row[1:]

    # Read in units
    units = {}
    with open("assets/" + globals.scale + "/data.tsv", encoding="utf8", newline="") as csvfile:
        for row in csv.DictReader(csvfile, delimiter="\t"):
            code = row["Unit"]
            # Skip the Totals row
            if code == "Total":
                continue
            # add the unit and metrics
            metrics = {
                key: int(value.strip().replace(",", "")) for (key, value) in row.items() if key in globals.allowed
            }
            units[code] = Unit(code, metrics)

    # Put adjacency in the units
    for unit in units.values():
        for adjacent in adj[unit]:
            unit.adj.add(units[adjacent])

    populateDistances(units)

    sys.setrecursionlimit(max(len(units), 1000))

    return sorted(units.values(), key=lambda u: u.code)
