from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import requests
from typing import Optional, List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
WALK_TIME_WESTMORELAND_TO_EDEN = 6  # minutes (to-home route)
WALK_TIME_HAWKINS_TO_DOLIER = 5  # minutes (to-work route)


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


@app.route("/")
def root():
    return jsonify({
        "message": "Dublin Bus Route Optimizer API",
        "endpoints": {
            "/best-route/to-home": "Get best route from Booterstown to home",
            "/best-route/to-work": "Get best route from home to Booterstown"
        }
    })


@app.route("/best-route/to-home")
def get_best_route_to_home():
    """
    Calculate all possible routes from Booterstown to home within next 2 hours
    Route: Booterstown (E1/E2) -> Westmoreland St -> walk 6min -> Eden Quay (15) -> Home
    """
    try:
        logger.info("Starting route calculation for to-home")
        now = datetime.utcnow().replace(tzinfo=None)  # Make timezone-naive for comparison
        two_hours_later = now + timedelta(hours=2)
        
        # Step 1: Get E1/E2 departures from Booterstown
        departures = get_departures(STOPS["booterstown"], "Booterstown Avenue, Mount Merrion")
        
        if not departures:
            return jsonify({
                "success": False,
                "error": "Unable to fetch departure data"
            }), 503
        
        # Filter for E1 and E2 only, exclude cancelled, and within 2 hours
        e_buses = []
        for d in departures:
            if d.get("serviceNumber") not in ["E1", "E2"]:
                continue
            if d.get("cancelled", False):
                continue
            
            dep_time_str = d.get("realTimeDeparture") or d.get("scheduledDeparture")
            if dep_time_str:
                dep_time = parse_datetime(dep_time_str).replace(tzinfo=None)  # Make timezone-naive
                if dep_time <= two_hours_later:
                    e_buses.append(d)
        
        if not e_buses:
            return jsonify({
                "success": False,
                "error": "No E1/E2 buses found in next 2 hours"
            }), 404
        
        logger.info(f"Found {len(e_buses)} E1/E2 buses in next 2 hours")
        
        # Step 2: Get 15 bus departures from Eden Quay
        bus_15_departures = get_departures(STOPS["eden_quay"], "Eden Quay, Dublin")
        bus_15_departures = [d for d in bus_15_departures
                            if d.get("serviceNumber") == "15"
                            and not d.get("cancelled", False)]
        
        if not bus_15_departures:
            return jsonify({
                "success": False,
                "error": "No 15 buses found at Eden Quay"
            }), 404
        
        logger.info(f"Found {len(bus_15_departures)} bus 15 departures")
        
        # Step 3: Calculate ALL possible routes
        all_routes = []
        
        # Check all E buses within 2 hours
        for e_bus in e_buses:
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
            
            # Calculate journey durations
            e_bus_duration = (westmoreland_arrival - departure_time).total_seconds() / 60
            
            route_option = {
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
            
            all_routes.append(route_option)
            logger.info(f"Route {len(all_routes)}: {service_num} at {departure_time.strftime('%H:%M')}, "
                       f"wait {wait_time:.1f}min, total {route_option['total_journey_minutes']:.0f}min")
        
        if not all_routes:
            return jsonify({
                "success": False,
                "error": "Could not calculate any routes"
            }), 404
        
        # Sort routes by total journey time (fastest first)
        all_routes.sort(key=lambda x: x['total_journey_minutes'])
        
        best_route = all_routes[0]
        other_routes = all_routes[1:]
        
        logger.info(f"Found {len(all_routes)} total routes. Best: {best_route['e_bus']['service']} "
                   f"at {best_route['e_bus']['departure_time']}")
        
        # Create detailed summary for best route
        e_bus = best_route['e_bus']
        walk = best_route['walk']
        bus_15 = best_route['bus_15']
        
        arrival_info = f" (arrive {bus_15['arrival_time']})" if bus_15.get('arrival_time') else ""
        
        best_route_summary = (
            f"🚏 {e_bus['departure_time']} - Wait for {e_bus['service']} at {e_bus['departure_stop']}\n"
            f"🚌 Ride {e_bus['duration_minutes']:.0f} min to {e_bus['arrival_stop']}\n"
            f"🚶 Walk {walk['duration_minutes']} min from {walk['from']} to {walk['to']}\n"
            f"⏰ Arrive at {walk['to']} at {best_route['eden_quay_arrival']['time']}\n"
            f"⏱️  Wait {best_route['wait_minutes']:.0f} min\n"
            f"🚏 {bus_15['departure_time']} - Take bus {bus_15['service']} at {bus_15['departure_stop']}\n"
            f"🚌 Ride {bus_15['duration_minutes']:.0f} min to {bus_15['arrival_stop']}{arrival_info}\n"
            f"⏱️  Total: {best_route['total_journey_minutes']:.0f} min"
        )
        
        # Create summary for other routes
        other_routes_summary = []
        for route in other_routes:
            other_routes_summary.append({
                "departure_time": route['e_bus']['departure_time'],
                "service": route['e_bus']['service'],
                "wait_minutes": route['wait_minutes'],
                "total_minutes": route['total_journey_minutes'],
                "summary": f"{route['e_bus']['departure_time']} {route['e_bus']['service']} - Wait {route['wait_minutes']:.0f}min, Total {route['total_journey_minutes']:.0f}min"
            })
        
        # Overall summary
        summary = f"📊 Found {len(all_routes)} routes in next 2 hours\n\n"
        summary += f"⭐ FASTEST ROUTE ({best_route['total_journey_minutes']:.0f} min):\n"
        summary += best_route_summary
        
        if other_routes_summary:
            summary += f"\n\n📋 Other options:\n"
            for i, other in enumerate(other_routes_summary, 1):
                summary += f"{i}. {other['summary']}\n"
        
        return jsonify({
            "success": True,
            "route": "to_home",
            "total_routes": len(all_routes),
            "best_route": best_route,
            "other_routes": other_routes_summary,
            "all_routes": all_routes,
            "summary": summary
        })
        
    except Exception as e:
        logger.error(f"Error calculating route: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@app.route("/best-route/to-date")
def get_best_route_to_date():
    """
    Calculate all possible routes from home to Booterstown within next 2 hours
    Route: Home (15) -> Hawkins St -> walk 5min -> D'Olier Street (E1/E2) -> Booterstown
    """
    try:
        logger.info("Starting route calculation for to-date")
        now = datetime.utcnow().replace(tzinfo=None)
        two_hours_later = now + timedelta(hours=2)
        
        # Step 1: Get bus 15 departures from Temple Vw Ave (home)
        departures = get_departures(STOPS["temple_view"], "Temple Vw Ave, Clare Hall")
        
        if not departures:
            return jsonify({
                "success": False,
                "error": "Unable to fetch departure data"
            }), 503
        
        # Filter for bus 15 only, exclude cancelled, and within 2 hours
        bus_15_list = []
        for d in departures:
            if d.get("serviceNumber") != "15":
                continue
            if d.get("cancelled", False):
                continue
            
            dep_time_str = d.get("realTimeDeparture") or d.get("scheduledDeparture")
            if dep_time_str:
                dep_time = parse_datetime(dep_time_str).replace(tzinfo=None)
                if dep_time <= two_hours_later:
                    bus_15_list.append(d)
        
        if not bus_15_list:
            return jsonify({
                "success": False,
                "error": "No bus 15 found in next 2 hours"
            }), 404
        
        logger.info(f"Found {len(bus_15_list)} bus 15 departures in next 2 hours")
        
        # Step 2: Get E1/E2 departures from D'Olier Street
        e_bus_departures = get_departures(STOPS["dolier_street"], "D'Olier Street, Dublin City South")
        e_bus_departures = [d for d in e_bus_departures
                           if d.get("serviceNumber") in ["E1", "E2"]
                           and not d.get("cancelled", False)]
        
        if not e_bus_departures:
            return jsonify({
                "success": False,
                "error": "No E1/E2 buses found at D'Olier Street"
            }), 404
        
        logger.info(f"Found {len(e_bus_departures)} E1/E2 departures")
        
        # Step 3: Calculate ALL possible routes
        all_routes = []
        
        # Check all bus 15 within 2 hours
        for bus_15 in bus_15_list:
            vehicle = bus_15.get("vehicle", {})
            
            # Skip if no vehicle data
            if not vehicle.get("dataFrameRef") or not vehicle.get("datedVehicleJourneyRef"):
                logger.warning(f"Skipping bus 15 - no vehicle tracking data")
                continue
            
            # Get departure time
            departure_time_str = bus_15.get("realTimeDeparture") or bus_15.get("scheduledDeparture")
            if not departure_time_str:
                continue
            
            departure_time = parse_datetime(departure_time_str)
            
            # Get timetable to find Hawkins St arrival
            timetable_id = bus_15.get("serviceID")
            timetable_data = get_estimated_timetable(
                timetable_id=timetable_id,
                direction="OUTBOUND",  # Going towards city center
                origin_stop_ref=STOPS["temple_view"],
                origin_departure_time=bus_15.get("scheduledDeparture"),
                origin_departure_realtime=bus_15.get("realTimeDeparture") or bus_15.get("scheduledDeparture"),
                data_frame_ref=vehicle.get("dataFrameRef"),
                dated_vehicle_journey_ref=vehicle.get("datedVehicleJourneyRef")
            )
            
            if not timetable_data:
                logger.warning(f"Could not get timetable for bus 15")
                continue
            
            # Find Hawkins St arrival time
            hawkins_arrival = find_stop_arrival_time(timetable_data, "Hawkins")
            
            if not hawkins_arrival:
                logger.warning(f"Could not find Hawkins St stop for bus 15")
                continue
            
            # Calculate D'Olier Street arrival (add walk time)
            dolier_arrival = hawkins_arrival + timedelta(minutes=WALK_TIME_HAWKINS_TO_DOLIER)
            
            logger.info(f"Bus 15: Depart {departure_time.strftime('%H:%M')}, "
                       f"Hawkins {hawkins_arrival.strftime('%H:%M')}, "
                       f"D'Olier {dolier_arrival.strftime('%H:%M')}")
            
            # Find next available E1/E2 (not cancelled)
            next_e_bus = None
            for e_bus in e_bus_departures:
                if e_bus.get("cancelled", False):
                    continue
                    
                e_bus_time_str = e_bus.get("realTimeDeparture") or e_bus.get("scheduledDeparture")
                if e_bus_time_str:
                    e_bus_time = parse_datetime(e_bus_time_str)
                    if e_bus_time >= dolier_arrival:
                        next_e_bus = e_bus
                        break
            
            if not next_e_bus:
                logger.warning(f"No E1/E2 available after bus 15")
                continue
            
            e_bus_time_str = next_e_bus.get("realTimeDeparture") or next_e_bus.get("scheduledDeparture")
            e_bus_time = parse_datetime(e_bus_time_str)
            service_num = next_e_bus.get("serviceNumber")
            
            # Get E bus timetable to find Booterstown arrival time
            e_bus_vehicle = next_e_bus.get("vehicle", {})
            e_bus_duration = 15  # Default fallback
            booterstown_arrival = None
            
            if e_bus_vehicle.get("dataFrameRef") and e_bus_vehicle.get("datedVehicleJourneyRef"):
                e_bus_timetable = get_estimated_timetable(
                    timetable_id=next_e_bus.get("serviceID"),
                    direction="OUTBOUND",
                    origin_stop_ref=STOPS["dolier_street"],
                    origin_departure_time=next_e_bus.get("scheduledDeparture"),
                    origin_departure_realtime=next_e_bus.get("realTimeDeparture") or next_e_bus.get("scheduledDeparture"),
                    data_frame_ref=e_bus_vehicle.get("dataFrameRef"),
                    dated_vehicle_journey_ref=e_bus_vehicle.get("datedVehicleJourneyRef")
                )
                
                if e_bus_timetable:
                    # Find Booterstown arrival time
                    booterstown_arrival = find_stop_arrival_time(e_bus_timetable, "Booterstown")
                    if booterstown_arrival:
                        e_bus_duration = (booterstown_arrival - e_bus_time).total_seconds() / 60
                        logger.info(f"{service_num} duration to Booterstown: {e_bus_duration:.1f} minutes")
            
            # Calculate wait time
            wait_time = (e_bus_time - dolier_arrival).total_seconds() / 60
            
            logger.info(f"Bus 15: Wait time for {service_num}: {wait_time:.1f} minutes")
            
            # Calculate journey durations
            bus_15_duration = (hawkins_arrival - departure_time).total_seconds() / 60
            
            route_option = {
                "bus_15": {
                    "service": "15",
                    "departure_time": departure_time.strftime("%H:%M"),
                    "departure_time_iso": departure_time.isoformat(),
                    "is_realtime": bus_15.get("realTimeDeparture") is not None,
                    "departure_stop": "Temple Vw Ave, Clare Hall",
                    "arrival_stop": "Hawkins Street",
                    "duration_minutes": round(bus_15_duration, 1)
                },
                "hawkins_arrival": {
                    "time": hawkins_arrival.strftime("%H:%M"),
                    "time_iso": hawkins_arrival.isoformat()
                },
                "walk": {
                    "from": "Hawkins Street",
                    "to": "D'Olier Street",
                    "duration_minutes": WALK_TIME_HAWKINS_TO_DOLIER
                },
                "dolier_arrival": {
                    "time": dolier_arrival.strftime("%H:%M"),
                    "time_iso": dolier_arrival.isoformat()
                },
                "e_bus": {
                    "service": service_num,
                    "departure_time": e_bus_time.strftime("%H:%M"),
                    "departure_time_iso": e_bus_time.isoformat(),
                    "is_realtime": next_e_bus.get("realTimeDeparture") is not None,
                    "departure_stop": "D'Olier Street",
                    "arrival_stop": "Booterstown Avenue",
                    "arrival_time": booterstown_arrival.strftime("%H:%M") if booterstown_arrival else None,
                    "destination": next_e_bus.get("destination"),
                    "duration_minutes": round(e_bus_duration, 1)
                },
                "wait_minutes": round(wait_time, 1),
                "total_journey_minutes": round((e_bus_time - departure_time).total_seconds() / 60 + e_bus_duration, 1)
            }
            
            all_routes.append(route_option)
            logger.info(f"Route {len(all_routes)}: Bus 15 at {departure_time.strftime('%H:%M')}, "
                       f"wait {wait_time:.1f}min, total {route_option['total_journey_minutes']:.0f}min")
        
        if not all_routes:
            return jsonify({
                "success": False,
                "error": "Could not calculate any routes"
            }), 404
        
        # Sort routes by total journey time (fastest first)
        all_routes.sort(key=lambda x: x['total_journey_minutes'])
        
        best_route = all_routes[0]
        other_routes = all_routes[1:]
        
        logger.info(f"Found {len(all_routes)} total routes. Best: bus 15 at {best_route['bus_15']['departure_time']}")
        
        # Create detailed summary for best route
        bus_15 = best_route['bus_15']
        walk = best_route['walk']
        e_bus = best_route['e_bus']
        
        arrival_info = f" (arrive {e_bus['arrival_time']})" if e_bus.get('arrival_time') else ""
        
        best_route_summary = (
            f"🚏 {bus_15['departure_time']} - Wait for bus {bus_15['service']} at {bus_15['departure_stop']}\n"
            f"🚌 Ride {bus_15['duration_minutes']:.0f} min to {bus_15['arrival_stop']}\n"
            f"🚶 Walk {walk['duration_minutes']} min from {walk['from']} to {walk['to']}\n"
            f"⏰ Arrive at {walk['to']} at {best_route['dolier_arrival']['time']}\n"
            f"⏱️  Wait {best_route['wait_minutes']:.0f} min\n"
            f"🚏 {e_bus['departure_time']} - Take {e_bus['service']} at {e_bus['departure_stop']}\n"
            f"🚌 Ride {e_bus['duration_minutes']:.0f} min to {e_bus['arrival_stop']}{arrival_info}\n"
            f"⏱️  Total: {best_route['total_journey_minutes']:.0f} min"
        )
        
        # Create summary for other routes
        other_routes_summary = []
        for route in other_routes:
            other_routes_summary.append({
                "departure_time": route['bus_15']['departure_time'],
                "service": f"15→{route['e_bus']['service']}",
                "wait_minutes": route['wait_minutes'],
                "total_minutes": route['total_journey_minutes'],
                "summary": f"{route['bus_15']['departure_time']} 15→{route['e_bus']['service']} - Wait {route['wait_minutes']:.0f}min, Total {route['total_journey_minutes']:.0f}min"
            })
        
        # Overall summary
        summary = f"📊 Found {len(all_routes)} routes in next 2 hours\n\n"
        summary += f"⭐ FASTEST ROUTE ({best_route['total_journey_minutes']:.0f} min):\n"
        summary += best_route_summary
        
        if other_routes_summary:
            summary += f"\n\n📋 Other options:\n"
            for i, other in enumerate(other_routes_summary, 1):
                summary += f"{i}. {other['summary']}\n"
        
        return jsonify({
            "success": True,
            "route": "to_work",
            "total_routes": len(all_routes),
            "best_route": best_route,
            "other_routes": other_routes_summary,
            "all_routes": all_routes,
            "summary": summary
        })
        
    except Exception as e:
        logger.error(f"Error calculating route: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

# Made with Bob
