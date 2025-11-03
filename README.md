# Dublin Bus Route Optimizer

Python FastAPI service to optimize bus routes in Dublin, Ireland.

## Features

- **To Home Route**: Optimizes the journey from Booterstown to home via E1/E2 and bus 15
- Real-time bus tracking integration
- Calculates optimal transfer times to minimize waiting

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running Locally

```bash
# Run the server
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### GET `/`
Health check and API information

### GET `/best-route/to-home`
Calculate the best route from Booterstown to home.

**Response Example:**
```json
{
  "success": true,
  "route": "to_home",
  "recommendation": {
    "e_bus": {
      "service": "E1",
      "departure_time": "14:30",
      "departure_time_iso": "2025-11-03T14:30:00+00:00",
      "is_realtime": true
    },
    "westmoreland_arrival": {
      "time": "14:45",
      "time_iso": "2025-11-03T14:45:00+00:00"
    },
    "eden_quay_arrival": {
      "time": "14:51",
      "time_iso": "2025-11-03T14:51:00+00:00"
    },
    "bus_15": {
      "departure_time": "14:55",
      "departure_time_iso": "2025-11-03T14:55:00+00:00",
      "is_realtime": true,
      "destination": "Clongriffin"
    },
    "wait_minutes": 4.0,
    "total_journey_minutes": 25.0
  },
  "summary": "Take E1 at 14:30, arrive Eden Quay at 14:51, wait 4.0 minutes for bus 15"
}
```

## Route Details

### To Home Route
1. **Start**: Booterstown Avenue, Mount Merrion (Stop: 8250DB002069)
2. **Take**: E1 or E2 bus (INBOUND)
3. **Get off**: Westmoreland Street
4. **Walk**: 6 minutes to Eden Quay
5. **Take**: Bus 15 (Stop: 8220DB000299)
6. **Destination**: Home (Belmayne area)

## iOS Shortcuts Integration

Use the API with iOS Shortcuts:

1. Add "Get Contents of URL" action
2. URL: `https://your-deployed-api.com/best-route/to-home`
3. Method: GET
4. Parse the JSON response
5. Display notification with the recommendation

Example Shortcut flow:
```
Get Contents of URL → Get Dictionary Value (recommendation.summary) → Show Notification
```

## Deployment

### Railway.app (Recommended)
1. Create account at [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Railway will auto-detect Python and deploy
4. Set environment variables if needed

### Render.com
1. Create account at [render.com](https://render.com)
2. Create new Web Service
3. Connect repository
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

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
- Only checks the first 3 E1/E2 buses
- Caches are not implemented (each request is fresh)
- Consider adding caching for production use

## Troubleshooting

**No buses found**: Check if the current time is within service hours
**Timeout errors**: The Transport API might be slow, increase timeout in code
**Wrong results**: Verify stop IDs are correct for your route

## Future Enhancements

- [ ] Add "to work" route (reverse direction)
- [ ] Implement response caching
- [ ] Add multiple route options (not just best)
- [ ] Historical data analysis
- [ ] Push notifications via iOS Shortcuts
- [ ] Web interface for testing

## License

MIT