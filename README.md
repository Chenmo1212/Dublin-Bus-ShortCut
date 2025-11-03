# Dublin Bus Route Optimizer

Python Flask service to optimize bus routes in Dublin, Ireland.

## Features

- **To Home Route**: Calculates ALL possible routes from Booterstown to home in the next 2 hours
- **Multiple Route Options**: Shows fastest route plus all alternatives
- **Real-time Tracking**: Uses live GPS data for accurate journey times
- **Smart Filtering**: Automatically excludes cancelled buses
- **Detailed Journey Info**: Complete breakdown of each leg of the journey

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running Locally

```bash
# Run the server
python main.py

# Or with gunicorn for production
gunicorn main:app --bind 0.0.0.0:8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### GET `/`
Health check and API information

### GET `/best-route/to-home`
Calculate ALL possible routes from Booterstown to home within specified time window.

**Query Parameters:**
- `h` (optional): Number of hours to look ahead (default: 1, min: 0.5, max: 12)
  - Example: `/best-route/to-home?h=2` (look ahead 2 hours)
  - Example: `/best-route/to-home` (default 1 hour)

**Response Example:**
```json
{
  "success": true,
  "route": "to_home",
  "total_routes": 5,
  "best_route": {
    "e_bus": {
      "service": "E1",
      "departure_time": "14:30",
      "departure_stop": "Booterstown Avenue",
      "arrival_stop": "Westmoreland Street",
      "duration_minutes": 15.0,
      "is_realtime": true
    },
    "walk": {
      "from": "Westmoreland Street",
      "to": "Eden Quay",
      "duration_minutes": 6
    },
    "bus_15": {
      "service": "15",
      "departure_time": "14:55",
      "departure_stop": "Eden Quay",
      "arrival_stop": "Temple Vw Ave, Belmayne",
      "arrival_time": "15:18",
      "duration_minutes": 23.0,
      "is_realtime": true
    },
    "wait_minutes": 4.0,
    "total_journey_minutes": 48.0
  },
  "other_routes": [
    {
      "departure_time": "14:45",
      "service": "E2",
      "wait_minutes": 8.0,
      "total_minutes": 52.0,
      "summary": "14:45 E2 - Wait 8min, Total 52min"
    }
  ],
  "summary": "📊 Found 5 routes in next 2 hours\n\n⭐ FASTEST ROUTE (48 min):\n..."
}
```

**Key Response Fields:**
- `total_routes`: Number of possible routes found
- `best_route`: Complete details of the fastest route
- `other_routes`: Summary of all alternative routes
- `all_routes`: Full details of every route (for advanced use)
- `summary`: Human-readable text summary

### GET `/best-route/to-date`
Calculate ALL possible routes from home to Booterstown within specified time window.

**Query Parameters:**
- `h` (optional): Number of hours to look ahead (default: 1, min: 0.5, max: 12)
  - Example: `/best-route/to-date?h=2` (look ahead 2 hours)
  - Example: `/best-route/to-date` (default 1 hour)

## Route Details

### To Home Route
1. **Start**: Booterstown Avenue, Mount Merrion (Stop: 8250DB002069)
2. **Take**: E1 or E2 bus (INBOUND)
3. **Get off**: Westmoreland Street
4. **Walk**: 6 minutes to Eden Quay
5. **Take**: Bus 15 (Stop: 8220DB000299)
6. **Destination**: Temple Vw Ave, Belmayne (Stop: 8220DB004595)

### To Date Route
1. **Start**: Temple Vw Ave, Clare Hall (Stop: 8220DB004595)
2. **Take**: Bus 15 (OUTBOUND)
3. **Get off**: Hawkins Street
4. **Walk**: 5 minutes to D'Olier Street
5. **Take**: E1 or E2 bus (Stop: 8220DB000334)
6. **Destination**: Booterstown Avenue (Stop: 8250DB002069)

### How It Works
1. Fetches all relevant bus departures within specified time window (default 1 hour)
2. For each possible first bus:
   - Gets real-time arrival at transfer point
   - Adds walking time to next stop
   - Finds next available connecting bus
   - Gets real-time arrival at destination
3. Calculates total journey time for each option
4. Sorts by fastest total time
5. Returns best route + all alternatives

## iOS Shortcuts Integration

Use the API with iOS Shortcuts:

1. Add "Get Contents of URL" action
2. URL: `https://your-deployed-api.com/best-route/to-home?h=2` (adjust `h` parameter as needed)
3. Method: GET
4. Parse the JSON response
5. Display notification with the recommendation

Example Shortcut flow:
```
Get Contents of URL → Get Dictionary Value (summary) → Show Notification
```

**Pro Tip:** Use different `h` values based on time of day:
- Morning rush: `h=0.5` (30 minutes)
- Normal times: `h=1` (1 hour, default)
- Planning ahead: `h=2` (2 hours)

## Deployment

### Vercel (Recommended) ⚡
Deploy to Vercel with zero configuration:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/YOUR_REPO)

**Manual Deployment:**
1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in project directory
3. Follow the prompts
4. Your API will be live at `https://your-project.vercel.app`

**Features:**
- ✅ Automatic deployments from Git
- ✅ Serverless functions (no cold starts)
- ✅ Free tier available
- ✅ Global CDN
- ✅ Zero configuration needed

### Railway.app
1. Create account at [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Railway will auto-detect Python and deploy
4. Set environment variables if needed

### Render.com
1. Create account at [render.com](https://render.com)
2. Create new Web Service
3. Connect repository
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn main:app --bind 0.0.0.0:$PORT`

### Fly.io
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and launch
fly auth login
fly launch

# Deploy
fly deploy
```

## Environment Variables

No environment variables required - API key is included in the code.

## API Rate Limits

The Transport for Ireland API has rate limits. The service:
- Checks ALL E1/E2 buses within next 2 hours
- Each route requires 2 API calls (E1/E2 timetable + bus 15 timetable)
- No caching implemented (each request is fresh)
- **Recommendation**: Add 1-2 minute caching for production use

## Troubleshooting

**No buses found**: Check if the current time is within service hours
**Timeout errors**: The Transport API might be slow, increase timeout in code
**Wrong results**: Verify stop IDs are correct for your route

## Future Enhancements

- [ ] Add "to work" route (reverse direction)
- [ ] Implement response caching (1-2 minutes)
- [x] Add multiple route options (DONE - shows all routes in 2 hours)
- [ ] Historical data analysis
- [ ] Push notifications via iOS Shortcuts
- [ ] Web interface for testing
- [ ] Filter routes by maximum wait time
- [ ] Add weather-aware recommendations

## License

MIT