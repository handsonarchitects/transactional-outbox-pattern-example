#!/bin/bash

# Ensure that jq is installed
if ! command -v jq &>/dev/null; then
    echo "jq is required but not installed. Please install jq and try again."
    exit 1
fi

while true; do
    clear

    # Fetch JSON data from the three endpoints
    response1=$(curl -s http://localhost:8091/info)
    response2=$(curl -s http://localhost:8092/info)
    response3=$(curl -s http://localhost:8093/info)

    # Parse JSON responses using jq
    produced=$(echo "$response1" | jq -r '.info.items_produced')
    update1=$(echo "$response1" | jq -r '.info.last_update')

    processed=$(echo "$response2" | jq -r '.info.items_processed')
    update2=$(echo "$response2" | jq -r '.info.last_update')

    consumed=$(echo "$response3" | jq -r '.info.items_consumed')
    update3=$(echo "$response3" | jq -r '.info.last_update')

    # Print the header for endpoints
    printf "%-12s | %-8s | %-30s\n" "Endpoint" "Value" "Last Update"
    printf "%s\n" "---------------------------------------------------------"
    printf "%-12s | %-8s | %-30s\n" "Produced" "$produced" "$update1"
    printf "%-12s | %-8s | %-30s\n" "Processed" "$processed" "$update2"
    printf "%-12s | %-8s | %-30s\n" "Consumed" "$consumed" "$update3"

    # Check Docker container health statuses

    # Elasticsearch
    elastic_status=$(docker inspect --format='{{.State.Health.Status}}' oubox-pattern-poc-elasticsearch-1 2>/dev/null)
    if [ $? -ne 0 ]; then
        elastic_status="not running"
    fi

    # RabbitMQ
    rabbit_status=$(docker inspect --format='{{.State.Health.Status}}' oubox-pattern-poc-rabbitmq-1 2>/dev/null)
    if [ $? -ne 0 ]; then
        rabbit_status="not running"
    fi

    # Determine display colors based on health
    if [ "$elastic_status" = "healthy" ]; then
        elastic_display="✔ UP"
    else
        elastic_display="✘ DOWN"
    fi

    if [ "$rabbit_status" = "healthy" ]; then
        rabbit_display="✔ UP"
    else
        rabbit_display="✘ DOWN"
    fi

    # Print the Docker services status below the table
    echo ""
    printf "%-15s | %-8s\n" "Elasticsearch" "$elastic_display"
    printf "%-15s | %-8s\n" "RabbitMQ" "$rabbit_display"

    sleep 3
done
