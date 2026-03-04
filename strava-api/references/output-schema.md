# Output Schema

## `athlete`

```json
{
  "generated_at": "ISO-8601",
  "athlete": {
    "id": 123,
    "firstname": "...",
    "lastname": "..."
  }
}
```

## `recent`

```json
{
  "generated_at": "ISO-8601",
  "filters": {"days": 7, "type": "Run", "limit": 30},
  "activities": [
    {
      "id": 123,
      "name": "Morning Run",
      "type": "Run",
      "sport_type": "Run",
      "start_date": "ISO-8601",
      "start_date_local": "ISO-8601",
      "timezone": "(GMT+00:00) Europe/London",
      "distance_km": 6.42,
      "moving_time_min": 41.8,
      "elapsed_time_min": 44.0,
      "average_speed_mps": 2.56,
      "pace_min_per_km": 6.51,
      "total_elevation_gain_m": 53,
      "trainer": false
    }
  ]
}
```

## `week`

```json
{
  "generated_at": "ISO-8601",
  "timezone": "Europe/London",
  "week_start": "YYYY-MM-DD",
  "week_end_exclusive": "YYYY-MM-DD",
  "type": "Run",
  "count": 2,
  "distance_km": 12.7,
  "moving_time_min": 86.2,
  "activities": ["...same shape as recent..."]
}
```

## `last-run`

```json
{
  "generated_at": "ISO-8601",
  "timezone": "Europe/London",
  "last_activity": {
    "id": 123,
    "start_date_local": "ISO-8601",
    "distance_km": 6.4,
    "moving_time_min": 41.8,
    "pace_min_per_km": 6.51
  },
  "hours_since": 27.4
}
```

## `summary`

```json
{
  "generated_at": "ISO-8601",
  "timezone": "Europe/London",
  "window_days": 28,
  "type": "Run",
  "count": 9,
  "distance_km": 58.3,
  "moving_time_min": 398.5,
  "avg_distance_km": 6.48,
  "avg_pace_min_per_km": 6.83
}
```
