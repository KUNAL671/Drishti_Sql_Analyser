-- ============================================================
-- Supabase PostgreSQL Schema
-- AI Taxi Database Analyst
-- ============================================================
-- Run this in the Supabase SQL Editor to create the tables.
-- ============================================================

-- Table 1: taxi_zones (lookup table — load first)
-- Maps location IDs to human-readable borough/zone names.
CREATE TABLE IF NOT EXISTS taxi_zones (
    location_id     SMALLINT PRIMARY KEY,
    borough         VARCHAR(50)  NOT NULL,
    zone            VARCHAR(100) NOT NULL,
    service_zone    VARCHAR(50)  NOT NULL
);

-- Table 2: yellow_trips (main trip records)
-- Contains all NYC Yellow Taxi trip data from the Parquet file.
-- Column names are normalized to snake_case from the Parquet's mixed case.
CREATE TABLE IF NOT EXISTS yellow_trips (
    trip_id                 BIGSERIAL PRIMARY KEY,
    vendor_id               SMALLINT        NOT NULL,
    pickup_datetime         TIMESTAMP       NOT NULL,
    dropoff_datetime        TIMESTAMP       NOT NULL,
    passenger_count         SMALLINT,
    trip_distance           DOUBLE PRECISION NOT NULL,
    rate_code_id            SMALLINT,
    store_and_fwd_flag      CHAR(1),
    pickup_location_id      SMALLINT        NOT NULL,
    dropoff_location_id     SMALLINT        NOT NULL,
    payment_type            SMALLINT        NOT NULL,
    fare_amount             NUMERIC(10,2)   NOT NULL,
    extra                   NUMERIC(10,2)   NOT NULL,
    mta_tax                 NUMERIC(10,2)   NOT NULL,
    tip_amount              NUMERIC(10,2)   NOT NULL,
    tolls_amount            NUMERIC(10,2)   NOT NULL,
    improvement_surcharge   NUMERIC(10,2)   NOT NULL,
    total_amount            NUMERIC(10,2)   NOT NULL,
    congestion_surcharge    NUMERIC(10,2),
    airport_fee             NUMERIC(10,2),
    cbd_congestion_fee      NUMERIC(10,2)   NOT NULL
);
