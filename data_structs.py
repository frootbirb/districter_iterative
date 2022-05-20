
import sys
import csv 
from numpy import mean
from typing import Union

import assets.states.name_to_abbrev as state_converter
import assets.counties.name_to_abbrev as county_converter

# --- Globals ----------------------------------------------------------------------------------------------------------

class Globals:
    #           0            1          2            3            4           5
    metrics = ["Population","Firearms","Area (mi2)","Land (mi2)","GDP ($1m)","Food ($1k)"]
    scales = ["states", "counties"]
    
    scale = None
    allowed = None

    def set(metricID: Union[str, int], scale: Union[str, int], callback = None) -> None:
        # Enable MetricID to be set as a string or an index
        if isinstance(scale, str):
            newscale = scale
        elif isinstance(scale, int):
            newscale = Globals.scales[scale]
        
        scaleChanged = newscale != Globals.scale
        Globals.scale = newscale

        if (Globals.scale == "states"):
            Globals.banned = []
            Globals.abbrev_to_name = state_converter.abbrev_to_name
        elif (Globals.scale == "counties"):
            Globals.banned = ["Firearms","Area (mi2)","Land (mi2)","GDP ($1m)","Food ($1k)"]
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
            Globals.regiondict = readFile()
            Globals.regionlist = Globals.regiondict.values()

# --- Data structures --------------------------------------------------------------------------------------------------

class Region:
    def __init__(self, code, metrics, adj) -> None:
        self.code = code
        self.metrics = metrics
        self.adj = set(adj)
        self.name = Globals.abbrev_to_name[code]
        self.hash = hash(code)
        self.distances = { }

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

class District:
    def __init__(self, index) -> None:
        self.regions = set()
        self.adj = set()
        self.metric = 0
        self.index = index

    def __gt__(self, other) -> bool:
        return self.metric > other.metric

    def empty(self) -> bool:
        return len(self.regions) == 0

    def addRegion(self, region: Region):
        # append the region into this district
        self.regions.add(region)
        # add the region's metric to the district's metric
        self.metric += region.metric
        # remove this region from the adjacency list
        self.adj.discard(region.code)
        # for each adjacent region, add it to the adjacency list if it's not already in the district
        self.adj |= (region.adj - self.regions)

    def removeRegion(self, region: Region):
        # remove the region from this district
        self.regions.remove(region)
        # remove the region's metric from the district's metric
        self.metric -= region.metric
        # if this region is adjacent to the district, add it to the adjacency list
        if any(reg in self.regions for reg in region.adj):
            self.adj.add(region.code)
        # remove regions that are no longer adjacent
        for adjregion in region.adj - self.regions:
            if all(reg not in self.regions for reg in region.adj):
                self.adj.remove(adjregion)

    def canLose(self, region: Region) -> bool:
        border = region.adj & self.regions
        if not border:
            return True
        toCheck = { border.pop() }
        while toCheck:
            selected = toCheck.pop()
            border.discard(selected)
            toCheck |= Globals.regiondict[selected].adj & border

        # If we can reach all the adjacent districts, we're good
        return len(border) == 0

    def getAverageDistance(self, region: Region) -> float:
        return mean([region.distances.get(inRegion) for inRegion in self.regions if region.distances.get(inRegion, False)])

class State:
    def __init__(self, numDist) -> None:
        self.placements = {}
        self.unplacedRegions = sorted(Globals.regionlist, key=lambda region: region.metric, reverse=True)
        self.districts = [District(i+1) for i in range(numDist)]

        regionMetrics = [ region.metric for region in Globals.regionlist ]
        self.sumRegionMetrics = sum(regionMetrics)
        equalSplit = self.sumRegionMetrics/numDist
        largestRegionMetric = max(regionMetrics)
        # The maximum acceptable size is 120% of an even split, or the largest single region
        self.maxAcceptableMetric = max(equalSplit * 1.2, largestRegionMetric)
        # The minimum acceptable size is 80% of an even split
        self.minAcceptableMetric = equalSplit * 0.8

    def isPlaced(self, region: Region) -> bool:
        return self.placements.get(region, 0) != 0
    
    def getDistrictFor(self, region: Region) -> District:
        index = self.placements.get(region, 0)-1
        return None if index >= len(self.districts) else self.districts[index]

    def hasAnyUnplacedAdjacent(self, district: District) -> bool:
        return any(self.placements.get(region, 0) == 0 for region in district.adj)

    def getDummyDataFrame():
        result = { new_list: [] for new_list in ["region","code","district","metric"] }
        for region in Globals.regionlist:
            result["region"].append(region.name)
            result["code"].append(region.code)
            result["district"].append('0')
            result["metric"].append(region.metric)

        return result

    def getCurrentDataFrame(self):
        result = State.getDummyDataFrame()

        for placement in self.placements.values():
            result["district"][2] = str(placement)

        return result
    
    def getUpdateDataFrame(self):
        return sorted(([region.name, region.metric, str(self.placements.get(region, 0))] for region in Globals.regionlist))

    def getDummyUpdateDataFrame():
        return sorted(([region.name, region.metric, '0'] for region in Globals.regionlist))

    def __percent(self, val: float) -> str:
        return "{:.2f}%".format(100*val/self.sumRegionMetrics)

    def __numWithPercent(self, val: float) -> str:
        return "{:,.2f} ({})".format(  val, self.__percent(val))

    def printResult(self):
        print("--------------- + Complete + ---------------")
        smallest = min(self.districts).metric
        largest = max(self.districts).metric
        print("Final spread: {}, from {} to {}".format(
            self.__numWithPercent(largest - smallest),
            self.__numWithPercent(smallest),
            self.__numWithPercent(largest)
        ))
        print("Acceptable sizes: {} to {}".format(
            self.__numWithPercent(self.minAcceptableMetric),
            self.__numWithPercent(self.maxAcceptableMetric)
        ))
        self.printState()

    def printState(self):
        results = []
        for district in sorted(self.districts, reverse=True):
            results.append((
                "District {} ({}):".format(district.index, self.__percent(district.metric)),
                "|".join(sorted(region.code for region in district.regions))
            ))
        
        if len(self.unplacedRegions) > 0:
            results.append((
                "Unplaced ({}):".format(self.__percent(sum(region.metric for region in self.unplacedRegions))),
                "|".join(sorted(region.code for region in self.unplacedRegions))
            ))

        length = len(max(results, key=lambda item: len(item[0]))[0])
        for entry in results:
            print(("{:" + str(length) + "} {}").format(*entry))
        print()
        
# --- Helper file reading function -------------------------------------------------------------------------------------

def getDistanceStep(distCode, regions):
    dist = 0
    distances = {region: (0 if region == distCode else -1) for region in regions}
    changed = True
    while changed:
        changed = False
        for region in (region for region in regions if region.code in distances and distances[region.code] == dist):
            for code in (code for code in region.adj if code in distances and distances[code] == -1):
                changed = True
                distances[code] = dist + 1
        dist += 1
        print("Calculating distances: {:10.4f}%".format(100*list(regions.keys()).index(distCode)/len(regions)), end="\r")

    return { code: dist for code, dist in distances.items() if dist > 0 }

def populateDistances(regions):
    # Attempt to read in distance
    try:
        with open("assets/" + Globals.scale + "/distance.csv", encoding='utf8', newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                name = row.pop("name")
                regions[name].distances = { code: int(dist) for code, dist in row.items() if dist }
    except:
        for code, region in regions.items():
            region.distances = getDistanceStep(code, regions)
        print()
        with open("assets/" + Globals.scale + "/distance.csv", "w", encoding='utf8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=',', fieldnames=["name"] + list(regions.keys()))
            writer.writeheader()
            for region in regions:
                newRow = region.distances.copy()
                newRow["name"] = region.code
                writer.writerow(newRow)

def readFile():
    # Read in adjacency
    adj = {}
    with open("assets/" + Globals.scale + "/adjacency.csv", encoding='utf8', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            adj[row[0]] = row[1:]

    # Read in regions
    regions = {}
    with open("assets/" + Globals.scale + "/data.tsv", encoding='utf8', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            code = row["Region"]
            # Skip the Totals row
            if code == "Total":
                continue
            # add the region and metrics
            metrics = {key: int(value.strip().replace(',','')) for (key, value) in row.items() if key in Globals.allowed}
            regions[code] = Region(code, metrics, adj[code])

    populateDistances(regions)

    sys.setrecursionlimit(max(len(regions), 1000))

    return regions