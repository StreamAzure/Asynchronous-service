
# Train Ticket：A Benchmark Microservice System
# <img src="./image/logo.png">
The project is a train ticket booking system based on microservice architecture which contains 45 microservices. The programming languages and frameworks it used are as below.
- Java - Spring Boot, Spring Cloud
- Node.js - Express (ts-ticket-office-service)
- Python - Django (ts-voucher-service, ts-avatar-service)
- Go - Webgo (ts-news-service)
- DB - Mongo、MySQL

## Global Configuration
- The root password for each MySQL instance: root; 
- The database name used in MySQL is `ts`

## Changes
- Updated the docker-compose file to allow the refactored TrainTicket to be deployed using Docker Compose
- Unified and modified the nacos, database, and other configurations of each service in the source code to fix container startup failures caused by improper configurations
- Observed issues caused by container startup order
    - If a microservice container starts before nacos, its connection to nacos will fail, causing the container to exit automatically
    - If the frontend service ts-ui-dashboard container starts before the ts-gateway-service is fully started, it will return a 502 bad gateway error due to the reverse proxy not finding ts-gateway-service (one manifestation is that the captcha image cannot be displayed)
    - Temporary solution: split into 3 docker-compose files and manually deploy them sequentially, where
        - docker-compose-base-1.yml: Nacos + all MySQL containers
        - docker-compose-base-2.yml: all microservices (except ts-ui-dashboard)
        - docker-compose-base-3.yml: ts-ui-dashboard container

## Running
### Source Code Compilation & Image Building
Run the build script:

```shell
python build_images.py
```
This script will automatically perform mvn compilation, jar packaging, and docker image building. 

Note to specify the image name prefix and version in the script

If not specified, the default image name format will be `microracer/<container-name>:base`

### Deploy with docker-compose
```shell
docker-compose -f deployment/docker-compose-base-1.yml up -d
# Check the logs to ensure that the MySQL containers, Nacos, and OAP-Server are fully started and can provide services before proceeding to the next step
docker-compose -f deployment/docker-compose-base-2.yml up -d
# Check the logs to ensure that ts-gateway-service is fully started and can provide services (i.e., log output shows Started GatewayApplication in ** seconds) before proceeding to the next step
docker-compose -f deployment/docker-compose-base-3.yml up -d
```
- Access [http://localhost:8080/client_login.html](http://localhost:8080/client_login.html). If all containers are running normally and the captcha image is displayed, the deployment is successful.
- Access SkyWalking UI: [http://localhost:8090/general](http://localhost:8090/general)

## Auto Request Script
Cloned from [train-ticket-auto-query](https://github.com/FudanSELab/train-ticket-auto-query)

Completed updates:
- Corrected the wrong key in the request script: `startingPlace` → `startPlace`. This error caused all Python requests to the /travelservice and /travelplan paths to fail