import sys
import csv
from numpy import mean
from typing import Union

import assets.states.name_to_abbrev as state_converter
import assets.counties.name_to_abbrev as county_converter

# --- Globals ----------------------------------------------------------------------------------------------------------


class Globals:
    metrics = ["Population", "Firearms", "Area (mi2)", "Land (mi2)", "GDP ($1m)", "Food ($1k)"]
    scales = ["states", "counties"]

    scale = None
    allowed = None
    callback = None

    def set(metricID: Union[str, int], scale: Union[str, int], callback=None) -> None:
        # Enable MetricID to be set as a string or an index
        if isinstance(scale, str):
            newscale = scale
        elif isinstance(scale, int):
            newscale = Globals.scales[scale]

        scaleChanged = newscale != Globals.scale
        Globals.scale = newscale

        if Globals.scale == "states":
            Globals.banned = []
            Globals.abbrev_to_name = state_converter.abbrev_to_name
        elif Globals.scale == "counties":
            Globals.banned = ["Firearms", "Area (mi2)", "Land (mi2)", "GDP ($1m)", "Food ($1k)"]
            Globals.abbrev_to_name = county_converter.abbrev_to_name

        Globals.allowed = [metric for metric in Globals.metrics if metric not in Globals.banned]

        # Enable MetricID to be set as a string or an index
        if isinstance(metricID, str):
            Globals.metricID = metricID
        elif isinstance(metricID, int):
            Globals.metricID = Globals.allowed[metricID]

        if callback:
            Globals.callback = callback

        if scaleChanged:
            Globals.unitdict = readFile()
            Globals.unitlist = Globals.unitdict.values()


# --- Data structures --------------------------------------------------------------------------------------------------


class Unit:
    def __init__(self, code, metrics, adj) -> None:
        self.code = code
        self.metrics = metrics
        self.adj = set(adj)
        self.name = Globals.abbrev_to_name[code]
        self.hash = hash(code)
        self.distances = {}

    @property
    def metric(self) -> int:
        return self.metrics[Globals.metricID]

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return self.code

    def __eq__(self, other) -> bool:
        return self.code == other

    def __hash__(self) -> str:
        return self.hash


class Group:
    def __init__(self, index) -> None:
        self.units = set()
        self.adj = set()
        self.metric = 0
        self.index = index

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
        self.adj.discard(unit.code)
        # for each adjacent unit, add it to the adjacency list if it's not already in the group
        self.adj |= unit.adj - self.units

    def removeUnit(self, unit: Unit):
        # remove the unit from this group
        self.units.remove(unit)
        # remove the unit's metric from the group's metric
        self.metric -= unit.metric
        # if this unit is adjacent to the group, add it to the adjacency list
        if any(adjunit in self.units for adjunit in unit.adj):
            self.adj.add(unit.code)
        # remove units that are no longer adjacent
        for adjunit in unit.adj - self.units:
            if all(u not in self.units for u in Globals.unitdict[adjunit].adj):
                self.adj.remove(adjunit)

    def canLose(self, unit: Unit) -> bool:
        border = unit.adj & self.units
        if not border:
            return True
        toCheck = {border.pop()}
        while toCheck:
            selected = toCheck.pop()
            border.discard(selected)
            toCheck |= Globals.unitdict[selected].adj & border

        # If we can reach all the adjacent groups, we're good
        return len(border) == 0

    def getAverageDistance(self, unit: Unit) -> float:
        return mean([unit.distances.get(inUnit) for inUnit in self.units if unit.distances.get(inUnit, False)])


class State:
    def __init__(self, numGroup) -> None:
        self.placements = {}
        self.unplacedUnits = sorted(Globals.unitlist, key=lambda unit: unit.metric, reverse=True)
        self.groups = [Group(i + 1) for i in range(numGroup)]

        unitMetrics = [unit.metric for unit in Globals.unitlist]
        self.sumUnitMetrics = sum(unitMetrics)
        equalSplit = self.sumUnitMetrics / numGroup
        largestUnitMetric = max(unitMetrics)
        # TODO confirm that this is possible before starting?
        # The maximum acceptable size is 120% of an even split, or the largest single unit
        self.maxAcceptableMetric = max(equalSplit * 1.2, largestUnitMetric)
        # The minimum acceptable size is 80% of an even split
        self.minAcceptableMetric = equalSplit * 0.8

    def isPlaced(self, unit: Unit) -> bool:
        return self.placements.get(unit, 0) != 0

    def getGroupFor(self, unit: Unit) -> Group:
        index = self.placements.get(unit, 0) - 1
        return None if index >= len(self.groups) else self.groups[index]

    def hasAnyUnplacedAdjacent(self, group: Group) -> bool:
        return any(self.placements.get(unit, 0) == 0 for unit in group.adj)

    def getDummyDataFrame():
        result = {new_list: [] for new_list in ["unit", "code", "group", "metric"]}
        for unit in Globals.unitlist:
            result["unit"].append(unit.name)
            result["code"].append(unit.code)
            result["group"].append("0")
            result["metric"].append(unit.metric)

        return result

    def getCurrentDataFrame(self):
        result = State.getDummyDataFrame()

        for placement in self.placements.values():
            result["group"][2] = str(placement)

        return result

    def getUpdateDataFrame(self):
        return sorted(([unit.name, unit.metric, str(self.placements.get(unit, 0))] for unit in Globals.unitlist))

    def getDummyUpdateDataFrame():
        return sorted(([unit.name, unit.metric, "0"] for unit in Globals.unitlist))

    def __percent(self, val: float) -> str:
        return "{:.2f}%".format(100 * val / self.sumUnitMetrics)

    def __numWithPercent(self, val: float) -> str:
        return "{:,.2f} ({})".format(val, self.__percent(val))

    def printResult(self):
        print("--------------- + Complete + ---------------")
        print("Created {} groups of {} with criteria {}".format(len(self.groups), Globals.scale, Globals.metricID))
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
            results.append(
                (
                    "Group {}".format(group.index),
                    self.__percent(group.metric),
                    "|".join(sorted(unit.code for unit in group.units)),
                )
            )

        if len(self.unplacedUnits) > 0:
            results.append(
                (
                    "Unplaced",
                    self.__percent(sum(unit.metric for unit in self.unplacedUnits)),
                    "|".join(sorted(unit.code for unit in self.unplacedUnits)),
                )
            )

        length = len(max(results, key=lambda item: len(item[0]))[0])
        if Globals.scale == Globals.scales[0]:
            for entry in results:
                print(("{:" + str(length) + "} ({}): {}").format(*entry))
        else:
            for entry in results:
                print(("{:" + str(length) + "}  ({})").format(*entry))
        print()


# --- Helper file reading function -------------------------------------------------------------------------------------


def getDistanceStep(distCode, units):
    dist = 0
    distances = {unit: (0 if unit == distCode else -1) for unit in units}
    changed = True
    while changed:
        changed = False
        for unit in (unit for unit in units if unit.code in distances and distances[unit.code] == dist):
            for code in (code for code in unit.adj if code in distances and distances[code] == -1):
                changed = True
                distances[code] = dist + 1
        dist += 1
        print(
            "Calculating distances: {:10.4f}%".format(100 * list(units.keys()).index(distCode) / len(units)),
            end="\r",
        )

    return {code: dist for code, dist in distances.items() if dist > 0}


def populateDistances(units):
    # Attempt to read in distance
    try:
        with open("assets/" + Globals.scale + "/distance.csv", encoding="utf8", newline="") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")
            for row in reader:
                name = row.pop("name")
                units[name].distances = {code: int(dist) for code, dist in row.items() if dist}
    except:
        for code, unit in units.items():
            unit.distances = getDistanceStep(code, units)
        print()
        with open(
            "assets/" + Globals.scale + "/distance.csv",
            "w",
            encoding="utf8",
            newline="",
        ) as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=",", fieldnames=["name"] + list(units.keys()))
            writer.writeheader()
            for unit in units:
                newRow = unit.distances.copy()
                newRow["name"] = unit.code
                writer.writerow(newRow)


def readFile():
    # Read in adjacency
    adj = {}
    with open("assets/" + Globals.scale + "/adjacency.csv", encoding="utf8", newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for row in reader:
            adj[row[0]] = row[1:]

    # Read in units
    units = {}
    with open("assets/" + Globals.scale + "/data.tsv", encoding="utf8", newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for row in reader:
            code = row["Unit"]
            # Skip the Totals row
            if code == "Total":
                continue
            # add the unit and metrics
            metrics = {
                key: int(value.strip().replace(",", "")) for (key, value) in row.items() if key in Globals.allowed
            }
            units[code] = Unit(code, metrics, adj[code])

    populateDistances(units)

    sys.setrecursionlimit(max(len(units), 1000))

    return units
