-- ============================================================
-- Indexes for AI Query Performance
-- ============================================================
-- Run this AFTER loading data into yellow_trips.
-- Creating indexes before loading slows down the import.
-- ============================================================

-- Speed up queries filtering by pickup time (most common pattern)
CREATE INDEX IF NOT EXISTS idx_trips_pickup_dt
    ON yellow_trips (pickup_datetime);

-- Speed up queries filtering by dropoff time
CREATE INDEX IF NOT EXISTS idx_trips_dropoff_dt
    ON yellow_trips (dropoff_datetime);

-- Speed up JOINs with taxi_zones for pickup locations
CREATE INDEX IF NOT EXISTS idx_trips_pu_loc
    ON yellow_trips (pickup_location_id);

-- Speed up JOINs with taxi_zones for dropoff locations
CREATE INDEX IF NOT EXISTS idx_trips_do_loc
    ON yellow_trips (dropoff_location_id);

-- Speed up queries filtering by payment type
CREATE INDEX IF NOT EXISTS idx_trips_payment
    ON yellow_trips (payment_type);
