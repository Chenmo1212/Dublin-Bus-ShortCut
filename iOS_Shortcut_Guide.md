# iOS Shortcut Setup Guide

## Complete Guide for Setting Up iOS Shortcuts

### Step 1: Deploy API Server

Choose a free deployment platform:

#### Railway.app (Recommended)
1. Visit https://railway.app
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select this repository
5. Railway will auto-detect Python and deploy
6. Copy your API URL (e.g., `https://your-app.railway.app`)

#### Render.com
1. Visit https://render.com
2. Create account and sign in
3. Click "New +" → "Web Service"
4. Connect GitHub repository
5. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Click "Create Web Service"
7. Copy your API URL

### Step 2: Create iOS Shortcut

#### Method A: Simple Version (Show Summary Only)

1. Open "Shortcuts" app
2. Tap "+" in top right
3. Add these actions:

```
1. [Get Contents of URL]
   - URL: https://your-api-url.com/best-route/to-home
   - Method: GET
   
2. [Get Dictionary Value]
   - Get: summary
   - From: Contents of URL
   
3. [Show Notification]
   - Title: 🚌 Best Route Home
   - Body: Dictionary Value
```

4. Name shortcut "Best Route Home"
5. Tap Done

**What you'll see:**
```
📊 Found 5 routes in next 2 hours

⭐ FASTEST ROUTE (48 min):
🚏 14:30 - Wait for E1 at Booterstown Avenue
🚌 Ride 15 min to Westmoreland Street
🚶 Walk 6 min from Westmoreland Street to Eden Quay
⏰ Arrive at Eden Quay at 14:51
⏱️  Wait 4 min
🚏 14:55 - Take bus 15 at Eden Quay
🚌 Ride 23 min to Temple Vw Ave, Belmayne (arrive 15:18)
⏱️  Total: 48 min

📋 Other options:
1. 14:45 E2 - Wait 8min, Total 52min
2. 15:00 E1 - Wait 3min, Total 50min
```

#### Method B: Show All Routes (Choose from List)

1. Open "Shortcuts" app
2. Tap "+" in top right
3. Add these actions:

```
1. [Get Contents of URL]
   - URL: https://your-api-url.com/best-route/to-home
   - Method: GET

2. [Get Dictionary Value]
   - Get: total_routes
   - From: Contents of URL
   - Store as variable: total_routes

3. [Get Dictionary Value]
   - Get: best_route
   - From: Contents of URL

4. [Get Dictionary Value]
   - Get: e_bus
   - From: Dictionary Value

5. [Get Dictionary Value]
   - Get: departure_time
   - From: Dictionary Value
   - Store as variable: best_time

6. [Get Dictionary Value]
   - Get: total_journey_minutes
   - From: best_route
   - Store as variable: best_total

7. [Text]
   Content:
   Found [total_routes] routes
   
   FASTEST: [best_time] ([best_total] min)
   
   [summary from API]

8. [Show Notification]
   - Title: 🚌 Routes Home
   - Body: Text
```

#### Method C: With Voice Announcement

Add at the end of Method A or B:

```
[Speak Text]
- Text: Dictionary Value (or combined text)
- Language: English
```

### Step 3: Add to Home Screen

1. Long press the shortcut
2. Select "Details"
3. Tap "Add to Home Screen"
4. Customize icon and name
5. Tap "Add"

### Step 4: Set Up Automation (Optional)

#### Scenario 1: Auto-run when leaving work

1. Open "Shortcuts" app
2. Switch to "Automation" tab
3. Tap "+" in top right
4. Select "Create Personal Automation"
5. Choose trigger:
   - **Time**: Every day at 5:00 PM
   - **Location**: When leaving office
   - **Calendar**: When work event ends
6. Add action: "Run Shortcut" → Select "Best Route Home"
7. Turn off "Ask Before Running" (optional)
8. Tap Done

#### Scenario 2: Auto-run when arriving at Booterstown

1. Create automation
2. Select "Arrive"
3. Choose location: Booterstown Avenue station
4. Add action: Run "Best Route Home" shortcut

### Step 5: Add Siri Voice Command

1. Open shortcut details
2. Tap "Add to Siri"
3. Record voice command, e.g.:
   - "Route home"
   - "How to get home"
   - "Best way home"
4. Tap Done

Now you can say: "Hey Siri, route home"

## Advanced Features

### Add Error Handling

After "Get Contents of URL" add:

```
[If]
- Condition: Contents of URL contains "success"
- Then: Show result
- Otherwise: Show Notification "Unable to get route info, try again later"
```

### Add Loading Indicator

Before "Get Contents of URL" add:

```
[Show Notification]
- Title: Calculating...
- Body: Please wait
```

### Save History

After showing result add:

```
[Add to Note]
- Note: Commute Log
- Content: [Current Date Time] - [Result Text]
```

## Troubleshooting

### Issue 1: "Cannot connect to server"
- Check API URL is correct
- Confirm server is deployed and running
- Check phone network connection

### Issue 2: "Request timeout"
- Transport API might be slow
- Increase timeout to 30 seconds in "Get Contents of URL"

### Issue 3: "No buses found"
- May be outside service hours
- Check if E1/E2 and bus 15 are operating at current time

### Issue 4: Results inaccurate
- API uses real-time data, may have delays
- Recommend checking 5-10 minutes before departure

## Example Output

```
📊 Found 5 routes in next 2 hours

⭐ FASTEST ROUTE (48 min):
🚏 14:30 - Wait for E1 at Booterstown Avenue
🚌 Ride 15 min to Westmoreland Street
🚶 Walk 6 min from Westmoreland Street to Eden Quay
⏰ Arrive at Eden Quay at 14:51
⏱️  Wait 4 min
🚏 14:55 - Take bus 15 at Eden Quay
🚌 Ride 23 min to Temple Vw Ave, Belmayne (arrive 15:18)
⏱️  Total: 48 min

📋 Other options:
1. 14:45 E2 - Wait 8min, Total 52min
2. 15:00 E1 - Wait 3min, Total 50min
3. 15:15 E2 - Wait 12min, Total 58min
4. 15:30 E1 - Wait 5min, Total 53min
```

## Tips

- Run shortcut 5-10 minutes before departure
- Create multiple shortcuts for different scenarios (work/home)
- Use widgets to view on home screen
- Set up multiple automation triggers

## Understanding the Response

### Key Fields
- `total_routes`: Number of routes found in next 2 hours
- `best_route`: Fastest route with complete details
- `other_routes`: Array of alternative routes
- `summary`: Human-readable text summary

### Using Other Routes
To show alternative routes in a list:
```
[Get Dictionary Value]
- Get: other_routes
- From: Contents of URL

[Choose from List]
- Items: Dictionary Value
```

## Next Steps

When "to work" route is developed, create a second shortcut:
- URL: `https://your-api-url.com/best-route/to-work`
- Name: "Best Route to Work"