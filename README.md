# Tempbot
Discord bot to report the temperature in various areas of the space to Discord

# How to run the container
```
docker run \
    -d \
    -v $(pwd)/config.ini:/app/config.ini:ro \
    --name tempbot \
    --log-driver=local \
    --restart unless-stopped \
    --network host \
   tempbot:latest
```
