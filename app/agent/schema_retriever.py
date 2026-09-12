"""
schema_retriever.py — Database Schema Retriever
=================================================
Retrieves the database schema and formats it for the LLM.
The LLM needs to know what tables and columns exist
so it can write correct SQL queries.

Supports:
  - Default NYC Taxi dataset (hard-coded schema)
  - Uploaded datasets (dynamic schema from registry)
"""


def get_schema_for_llm(dataset_id: str = None) -> str:
    """
    Get the database schema formatted for the LLM prompt.

    Args:
        dataset_id: Optional dataset ID. If None, returns the default
                    taxi dataset schema. If provided, returns the schema
                    for the uploaded dataset.

    Returns:
        str: Human-readable schema description
    """
    if dataset_id is None:
        return _get_taxi_schema()
    else:
        return _get_uploaded_schema(dataset_id)


def _get_uploaded_schema(dataset_id: str) -> str:
    """
    Retrieve schema for an uploaded dataset from the registry.

    Args:
        dataset_id: The dataset ID to look up

    Returns:
        str: Human-readable schema description

    Raises:
        ValueError: If the dataset is not found or not ready
    """
    from app.data.dataset_registry import get_dataset
    from app.data.schema_generator import generate_schema_for_llm

    metadata = get_dataset(dataset_id)
    if metadata is None:
        raise ValueError(f"Dataset '{dataset_id}' not found.")
    if metadata["dataset_status"] != "ready":
        raise ValueError(
            f"Dataset '{dataset_id}' is not ready (status: {metadata['dataset_status']})."
        )

    return generate_schema_for_llm(metadata)


def _get_taxi_schema() -> str:
    """
    Get the default NYC Taxi database schema.
    This is the original hard-coded schema string.

    Returns:
        str: Human-readable schema description
    """
    return """
DATABASE SCHEMA
==================================================

TABLE: taxi_zones
----------------------------------------
  location_id                    SMALLINT             NOT NULL
  borough                        VARCHAR(50)          NOT NULL
  zone                           VARCHAR(100)         NOT NULL
  service_zone                   VARCHAR(50)          NOT NULL

TABLE: yellow_trips
----------------------------------------
  trip_id                        BIGINT               NOT NULL
  vendor_id                      SMALLINT             NOT NULL
  pickup_datetime                TIMESTAMP            NOT NULL
  dropoff_datetime               TIMESTAMP            NOT NULL
  passenger_count                SMALLINT             NULL
  trip_distance                  DOUBLE PRECISION     NOT NULL
  rate_code_id                   SMALLINT             NULL
  store_and_fwd_flag             CHAR(1)              NULL
  pickup_location_id             SMALLINT             NOT NULL
  dropoff_location_id            SMALLINT             NOT NULL
  payment_type                   SMALLINT             NOT NULL
  fare_amount                    NUMERIC(10,2)        NOT NULL
  extra                          NUMERIC(10,2)        NOT NULL
  mta_tax                        NUMERIC(10,2)        NOT NULL
  tip_amount                     NUMERIC(10,2)        NOT NULL
  tolls_amount                   NUMERIC(10,2)        NOT NULL
  improvement_surcharge          NUMERIC(10,2)        NOT NULL
  total_amount                   NUMERIC(10,2)        NOT NULL
  congestion_surcharge           NUMERIC(10,2)        NULL
  airport_fee                    NUMERIC(10,2)        NULL
  cbd_congestion_fee             NUMERIC(10,2)        NOT NULL

RELATIONSHIPS:
----------------------------------------
  yellow_trips.pickup_location_id -> taxi_zones.location_id (pickup zone)
  yellow_trips.dropoff_location_id -> taxi_zones.location_id (dropoff zone)

NOTES:
  - Use taxi_zones to translate location IDs into human-readable zone/borough names
  - pickup_datetime and dropoff_datetime are TIMESTAMP columns
  - Monetary columns (fare_amount, total_amount, etc.) are NUMERIC(10,2)
  - passenger_count, rate_code_id, congestion_surcharge, airport_fee may be NULL
"""
