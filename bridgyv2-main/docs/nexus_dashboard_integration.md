# Cisco Nexus Dashboard Expert Integration

This document describes the integration of the Cisco Nexus Dashboard expert agent into the Bridgy AI Assistant system.

## Overview

The Nexus Dashboard expert agent is specialized in handling queries related to Cisco's data center networking solutions, particularly the Nexus Dashboard platform. This expert can:

- Fetch telemetry data from Nexus Dashboard
- Retrieve information about network fabrics and devices
- Check alarm status and notifications
- Trigger automation workflows
- Provide detailed responses to operational queries

## Setup

### Environment Variables

To use the Nexus Dashboard expert, you need to set the following environment variables:

```
NEXUS_DASHBOARD_URL=https://your-nexus-dashboard-instance
NEXUS_DASHBOARD_USERNAME=your-username
NEXUS_DASHBOARD_PASSWORD=your-password
```

You can add these to your `.env` file in the project root directory.

### API Access

Ensure that the user account specified in the environment variables has appropriate API access permissions in your Nexus Dashboard instance.

## Usage

The system automatically routes queries related to Nexus Dashboard, network fabrics, switches, and telemetry to the Nexus Dashboard expert. Examples of queries that will be routed to this expert:

- "What's the status of my network fabric?"
- "Show me all critical alarms in my Nexus Dashboard"
- "What devices are registered in my Nexus Dashboard?"
- "Get telemetry data for CPU utilization on my switches"
- "Execute the network compliance check workflow"

## API Endpoints

The Nexus Dashboard API tool supports the following endpoints:

- `/api/v1/sites` - Get information about sites
- `/api/v1/fabrics` - Get information about network fabrics
- `/api/v1/devices` - Get information about network devices
- `/api/v1/telemetry` - Get telemetry data
- `/api/v1/alarms` - Get alarm information
- `/api/v1/workflows` - Get and execute automation workflows

## Troubleshooting

If you encounter issues with the Nexus Dashboard expert:

1. Verify that your environment variables are correctly set
2. Ensure that your Nexus Dashboard instance is accessible from the server running the Bridgy application
3. Check that the API credentials have sufficient permissions
4. Review the application logs for specific error messages

## Fallback Behavior

If the Nexus Dashboard API is unavailable, the system will automatically fall back to the General Expert, which will provide general information about Nexus Dashboard based on its training data.
