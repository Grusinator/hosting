#!/bin/bash

# Load environment variables
source .env

# Add the worker node to the swarm
docker swarm join --token $SWARM_TOKEN $SWARM_MANAGER_IP:2377
#!/bin/bash

# Load environment variables
source .env

# Add the worker node to the swarm
docker swarm join --token $SWARM_TOKEN $SWARM_MANAGER_IP:2377
