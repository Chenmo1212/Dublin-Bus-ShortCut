from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import requests
from typing import Optional, List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dublin Bus Route Optimizer")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Configuration
API_BASE_URL = "https://api-lts.transportforireland.ie/lts/lts/v1/public"
API_KEY = "630688984d38409689932a37a8641bb9"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Ocp-Apim-Subscription-Key": API_KEY,
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
}

# Stop IDs
STOPS = {
    "booterstown": "8250DB002069",  # Booterstown Avenue, Mount Merrion
    "eden_quay": "8220DB000299",     # Eden Quay, Dublin
    "temple_view": "8220DB004595",   # Temple Vw Ave, Clare Hall
    "dolier_street": "8220DB000334",  # D'Olier Street, Dublin City South
    "belmayne": "8220DB004595"  # Temple Vw Ave, Belmayne (home)
}

# Route configurations
WALK_TIME_WESTMORELAND_TO_EDEN = 6  # minutes


def get_departures(stop_id: str, stop_name: str) -> List[Dict]:
    """Get departures from a specific stop"""
    now = datetime.utcnow()
    
    payload = {
        "clientTimeZoneOffsetInMS": 0,
        "departureDate": now.isoformat() + "Z",
        "departureTime": now.isoformat() + "Z",
        "stopIds": [stop_id],
        "stopType": "BUS_STOP",
        "stopName": stop_name,
        "requestTime": now.isoformat() + "Z",
        "departureOrArrival": "DEPARTURE",
        "refresh": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/departures",
            json=payload,
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status", {}).get("success"):
            return data.get("stopDepartures", [])
        else:
            logger.error(f"API returned unsuccessful status: {data}")
            return []
    except Exception as e:
        logger.error(f"Error getting departures: {e}")
        return []


def get_estimated_timetable(
    timetable_id: str,
    direction: str,
    origin_stop_ref: str,
    origin_departure_time: str,
    origin_departure_realtime: str,
    data_frame_ref: str,
    dated_vehicle_journey_ref: str
) -> Optional[Dict]:
    """Get estimated timetable for a specific journey"""
    now = datetime.utcnow()
    
    payload = {
        "clientTimeZoneOffsetInMS": 0,
        "dateAndTime": now.isoformat() + "Z",
        "includeNonTimingPoints": True,
        "maxColumnsToFetch": 1,
        "timetableId": timetable_id,
        "timetableDirection": direction,
        "originStopReference": origin_stop_ref,
        "originDepartureTime": origin_departure_time,
        "originDepartureRealtime": origin_departure_realtime,
        "dataFrameRef": data_frame_ref,
        "datedVehicleJourneyRef": dated_vehicle_journey_ref
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/estimatedTimetable",
            json=payload,
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status", {}).get("success"):
            return data
        else:
            logger.error(f"API returned unsuccessful status: {data}")
            return None
    except Exception as e:
        logger.error(f"Error getting timetable: {e}")
        return None


def find_stop_arrival_time(timetable_data: Dict, stop_name_keyword: str) -> Optional[datetime]:
    """Find arrival time at a specific stop from timetable data"""
    rows = timetable_data.get("rows", [])
    columns = timetable_data.get("columns", [])
    
    if not columns:
        return None
    
    events = columns[0].get("events", {})
    
    # Find the stop by name
    for row in rows:
        if stop_name_keyword.lower() in row.get("stopName", "").lower():
            row_index = str(row.get("rowIndex"))
            event = events.get(row_index)
            
            if event:
                # Prefer realtime, fallback to scheduled
                time_str = event.get("realTimeOfEvent") or event.get("timeOfEvent")
                if time_str:
                    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    
    return None


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string from API"""
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


@app.get("/")
async def root():
    return {
        "message": "Dublin Bus Route Optimizer API",
        "endpoints": {
            "/best-route/to-home": "Get best route from Booterstown to home",
            "/best-route/to-work": "Get best route from home to Booterstown (coming soon)"
        }
    }


@app.get("/best-route/to-home")
async def get_best_route_to_home():
    """
    Calculate the best route from Booterstown to home
    Route: Booterstown (E1/E2) -> Westmoreland St -> walk 6min -> Eden Quay (15) -> Home
    """
    try:
        logger.info("Starting route calculation for to-home")
        
        # Step 1: Get E1/E2 departures from Booterstown
        departures = get_departures(STOPS["booterstown"], "Booterstown Avenue, Mount Merrion")
        
        if not departures:
            raise HTTPException(status_code=503, detail="Unable to fetch departure data")
        
        # Filter for E1 and E2 only, and exclude cancelled buses
        e_buses = [d for d in departures
                   if d.get("serviceNumber") in ["E1", "E2"]
                   and not d.get("cancelled", False)]
        
        if not e_buses:
            raise HTTPException(status_code=404, detail="No E1/E2 buses found")
        
        logger.info(f"Found {len(e_buses)} E1/E2 buses")
        
        # Step 2: Get 15 bus departures from Eden Quay
        bus_15_departures = get_departures(STOPS["eden_quay"], "Eden Quay, Dublin")
        bus_15_departures = [d for d in bus_15_departures
                            if d.get("serviceNumber") == "15"
                            and not d.get("cancelled", False)]
        
        if not bus_15_departures:
            raise HTTPException(status_code=404, detail="No 15 buses found at Eden Quay")
        
        logger.info(f"Found {len(bus_15_departures)} bus 15 departures")
        
        # Step 3: Calculate best option
        best_option = None
        min_wait_time = float('inf')
        
        # Check first 3 E buses
        for e_bus in e_buses[:3]:
            service_num = e_bus.get("serviceNumber")
            vehicle = e_bus.get("vehicle", {})
            
            # Skip if no vehicle data
            if not vehicle.get("dataFrameRef") or not vehicle.get("datedVehicleJourneyRef"):
                logger.warning(f"Skipping {service_num} - no vehicle tracking data")
                continue
            
            # Get departure time
            departure_time_str = e_bus.get("realTimeDeparture") or e_bus.get("scheduledDeparture")
            if not departure_time_str:
                continue
            
            departure_time = parse_datetime(departure_time_str)
            
            # Get timetable to find Westmoreland arrival
            timetable_id = e_bus.get("serviceID")
            timetable_data = get_estimated_timetable(
                timetable_id=timetable_id,
                direction="INBOUND",
                origin_stop_ref=STOPS["booterstown"],
                origin_departure_time=e_bus.get("scheduledDeparture"),
                origin_departure_realtime=e_bus.get("realTimeDeparture") or e_bus.get("scheduledDeparture"),
                data_frame_ref=vehicle.get("dataFrameRef"),
                dated_vehicle_journey_ref=vehicle.get("datedVehicleJourneyRef")
            )
            
            if not timetable_data:
                logger.warning(f"Could not get timetable for {service_num}")
                continue
            
            # Find Westmoreland arrival time
            westmoreland_arrival = find_stop_arrival_time(timetable_data, "Westmoreland")
            
            if not westmoreland_arrival:
                logger.warning(f"Could not find Westmoreland stop for {service_num}")
                continue
            
            # Calculate Eden Quay arrival (add walk time)
            eden_arrival = westmoreland_arrival + timedelta(minutes=WALK_TIME_WESTMORELAND_TO_EDEN)
            
            logger.info(f"{service_num}: Depart {departure_time.strftime('%H:%M')}, "
                       f"Westmoreland {westmoreland_arrival.strftime('%H:%M')}, "
                       f"Eden Quay {eden_arrival.strftime('%H:%M')}")
            
            # Find next available bus 15 (not cancelled)
            next_bus_15 = None
            for bus_15 in bus_15_departures:
                # Skip cancelled buses
                if bus_15.get("cancelled", False):
                    continue
                    
                bus_15_time_str = bus_15.get("realTimeDeparture") or bus_15.get("scheduledDeparture")
                if bus_15_time_str:
                    bus_15_time = parse_datetime(bus_15_time_str)
                    if bus_15_time >= eden_arrival:
                        next_bus_15 = bus_15
                        break
            
            if not next_bus_15:
                logger.warning(f"No bus 15 available after {service_num}")
                continue
            
            bus_15_time_str = next_bus_15.get("realTimeDeparture") or next_bus_15.get("scheduledDeparture")
            bus_15_time = parse_datetime(bus_15_time_str)
            
            # Get bus 15 timetable to find Belmayne arrival time
            bus_15_vehicle = next_bus_15.get("vehicle", {})
            bus_15_duration = 25  # Default fallback
            belmayne_arrival = None
            
            if bus_15_vehicle.get("dataFrameRef") and bus_15_vehicle.get("datedVehicleJourneyRef"):
                bus_15_timetable = get_estimated_timetable(
                    timetable_id=next_bus_15.get("serviceID"),
                    direction="INBOUND",
                    origin_stop_ref=STOPS["eden_quay"],
                    origin_departure_time=next_bus_15.get("scheduledDeparture"),
                    origin_departure_realtime=next_bus_15.get("realTimeDeparture") or next_bus_15.get("scheduledDeparture"),
                    data_frame_ref=bus_15_vehicle.get("dataFrameRef"),
                    dated_vehicle_journey_ref=bus_15_vehicle.get("datedVehicleJourneyRef")
                )
                
                if bus_15_timetable:
                    # Find Belmayne arrival time
                    belmayne_arrival = find_stop_arrival_time(bus_15_timetable, "Belmayne")
                    if belmayne_arrival:
                        bus_15_duration = (belmayne_arrival - bus_15_time).total_seconds() / 60
                        logger.info(f"Bus 15 duration to Belmayne: {bus_15_duration:.1f} minutes")
            
            # Calculate wait time
            wait_time = (bus_15_time - eden_arrival).total_seconds() / 60
            
            logger.info(f"{service_num}: Wait time for bus 15: {wait_time:.1f} minutes")
            
            if wait_time < min_wait_time:
                min_wait_time = wait_time
                
                # Calculate journey durations
                e_bus_duration = (westmoreland_arrival - departure_time).total_seconds() / 60
                
                best_option = {
                    "e_bus": {
                        "service": service_num,
                        "departure_time": departure_time.strftime("%H:%M"),
                        "departure_time_iso": departure_time.isoformat(),
                        "is_realtime": e_bus.get("realTimeDeparture") is not None,
                        "departure_stop": "Booterstown Avenue",
                        "arrival_stop": "Westmoreland Street",
                        "duration_minutes": round(e_bus_duration, 1)
                    },
                    "westmoreland_arrival": {
                        "time": westmoreland_arrival.strftime("%H:%M"),
                        "time_iso": westmoreland_arrival.isoformat()
                    },
                    "walk": {
                        "from": "Westmoreland Street",
                        "to": "Eden Quay",
                        "duration_minutes": WALK_TIME_WESTMORELAND_TO_EDEN
                    },
                    "eden_quay_arrival": {
                        "time": eden_arrival.strftime("%H:%M"),
                        "time_iso": eden_arrival.isoformat()
                    },
                    "bus_15": {
                        "service": "15",
                        "departure_time": bus_15_time.strftime("%H:%M"),
                        "departure_time_iso": bus_15_time.isoformat(),
                        "is_realtime": next_bus_15.get("realTimeDeparture") is not None,
                        "departure_stop": "Eden Quay",
                        "arrival_stop": "Temple Vw Ave, Belmayne",
                        "arrival_time": belmayne_arrival.strftime("%H:%M") if belmayne_arrival else None,
                        "destination": next_bus_15.get("destination"),
                        "duration_minutes": round(bus_15_duration, 1)
                    },
                    "wait_minutes": round(wait_time, 1),
                    "total_journey_minutes": round((bus_15_time - departure_time).total_seconds() / 60 + bus_15_duration, 1)
                }
        
        if not best_option:
            raise HTTPException(status_code=404, detail="Could not calculate optimal route")
        
        logger.info(f"Best option: {best_option['e_bus']['service']} with {best_option['wait_minutes']} min wait")
        
        # Create detailed summary
        e_bus = best_option['e_bus']
        walk = best_option['walk']
        bus_15 = best_option['bus_15']
        
        arrival_info = f" ({bus_15['arrival_time']} 到达)" if bus_15.get('arrival_time') else ""
        
        summary = (
            f"🚏 {e_bus['departure_time']} Wait for {e_bus['service']} at {e_bus['departure_stop']}\n"
            f"🚌 Ride {e_bus['duration_minutes']:.0f} minutes to {e_bus['arrival_stop']}\n"
            f"🚶 Walk {walk['duration_minutes']} minutes from {walk['from']} to {walk['to']}\n"
            f"⏰ Arrive at {walk['to']} at {best_option['eden_quay_arrival']['time']}\n"
            f"⏱️  Wait {best_option['wait_minutes']:.0f} minutes\n"
            f"🚏 {bus_15['departure_time']} Wait for {bus_15['service']} at {bus_15['departure_stop']}\n"
            f"🚌 Ride {bus_15['duration_minutes']:.0f} minutes to {bus_15['arrival_stop']}{arrival_info}\n"
            f"⏱️  Total journey time: {best_option['total_journey_minutes']:.0f} minutes"
        )
        
        return {
            "success": True,
            "route": "to_home",
            "recommendation": best_option,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Made with Bob
