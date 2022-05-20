from data_structs import State, Region,  District, Globals

# Solver

def getNext(state: State) -> tuple[Region, District]:
    baseRegions = state.unplacedRegions[:]

    # Prioritize districts that have at least one adjacent empty region or are empty
    district = min(state.districts, key=lambda district: (-(state.hasAnyUnplacedAdjacent(district) or district.empty()), district.metric))

    # If one of the districts is too big, we will allow stealing from it
    # If this district has no available adjacent districts, we will allow stealing from any larger neighbor
    noneAdjacent = not state.hasAnyUnplacedAdjacent(district) and not district.empty()
    for otherdist in state.districts:
        if otherdist.metric > state.maxAcceptableMetric or (otherdist.metric > district.metric and noneAdjacent):
            baseRegions += { region for region in otherdist.regions if otherdist.canLose(region) }

    # Get the regions which might be viable - unplaced regions adjacent to a given district, or those with no adjacent 
    # (e.g. AK) which aren't too big for the remaining overhead of the district
    if district.empty():
        regions = baseRegions
    else:
        regions = (region for region in baseRegions if (region in district.adj or
                                                        len(region.adj) == 0))
    return max(regions, key=lambda region: (
        region.metric + district.metric > state.maxAcceptableMetric,
        state.getDistrictFor(region).metric,
        -district.getAverageDistance(region), 
        region.metric)), district

def addToDistrict(state: State, region: Region, district: District) -> None:
    district.addRegion(region)
    if (placement := state.placements.get(region, 0)) == 0:
        state.unplacedRegions.remove(region)
    else:
        state.districts[placement-1].removeRegion(region)
    state.placements[region] = district.index

def removeFromDistrict(state: State, region: Region, district: District) -> None:
    state.unplacedRegions.append(region)
    district.removeRegion(region)
    state.placements[region] = 0

def generateUnplaced(state: State, borders: set, seed: Region = None, regions: set = None, adjdists: set = None) -> tuple[set, set]:
    if not seed:
        seed = next(iter(borders))
    if not regions:
        regions = set()
    if not adjdists:
        adjdists = set()

    regions.add(seed)
    for region in filter(lambda region: region not in regions, Globals.regiondict[seed].adj):
        if (placement := state.placements.get(region, 0)) != 0:
            adjdists.add(placement)
        else:
            downstream = generateUnplaced(state, borders, region, regions, adjdists)
            regions |= downstream[0]
            adjdists |= downstream[1]
            
        # Shortcut out of the loop if we've seen at least two districts
        if len(adjdists) > 1:
            return regions, adjdists
    
    return regions, adjdists

def generateDisconnectedDistricts(state: State, district: District) -> set:
    # Get all regions adjacent to the current district which are not in a district
    borders = { region for region in district.adj if not state.isPlaced(region) }

    while len(borders) > 0:
        unplaced, adjdists = generateUnplaced(state, borders)
        borders -= unplaced
        if len(adjdists) == 1:
            yield unplaced

g_callback = None
doprint = False

def doStep(state: State) -> State:
    region, district = getNext(state)

    if doprint:
        print("{}: Adding {}".format(district.index, region))
        print("  Average distance {:.2f}".format(district.getAverageDistance(region)))

    addToDistrict(state, region, district)

    if doprint:
        state.printState()
    
    # If every district has some adjacent regions, we can start checking for enclosures
    if all(len(district.adj) > 0 for district in state.districts):
        for unplacedregions in generateDisconnectedDistricts(state, district):
            if doprint:
                print("{}: enclosed {}".format(district.index, unplacedregions))
                state.printState()
            for unplaced in unplacedregions:
                addToDistrict(state, Globals.regiondict[unplaced], district)

    if Globals.callback:
        Globals.callback(state.getUpdateDataFrame())

    return state
    
def solve(numDist, metricID = 0, scale = 0, callback = None) -> dict:
    Globals.set(metricID, scale, callback)

    #Start the solver!
    state = State(numDist=numDist)
    while len(state.unplacedRegions) != 0 or any(district.metric > state.maxAcceptableMetric for district in state.districts):
        state = doStep(state)

    state.printResult()

if __name__ == "__main__":
    solve(3)