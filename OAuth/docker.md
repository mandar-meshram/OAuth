1. Rebuild everything from scratch
    docker-compose up --build

2.Stop and remove old container
    docker-compose down
3. Clear any cached images and volumes
    docker system prune -a
4. See Running Containers:
     docker ps
5.Remove the Container:
     docker rm auth_service_container
6. Rebuild and Restart Any Service (Docker Compose):
    docker-compose up --build anyservicename
7. Solution Steps (Safe to Follow):
    Option 1: Clean up Docker build cache
    Run this command to clear any corrupted intermediate image layers:
        docker builder prune --force
    Then rebuild your image:
        docker-compose build --no-cache
        docker-compose up or docker-compose up auth_service

8. docker builder prune --all --force 
    command removes all unused build cache, images, and networks without prompting for confirmation.

