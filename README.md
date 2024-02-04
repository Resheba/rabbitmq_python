# RabbitMQ Client

This Python code provides a convenient interface for interacting with RabbitMQ, a message broker that enables communication between different components of a distributed system. The library includes classes for basic RabbitMQ operations, message publishing, and RPC (Remote Procedure Call) implementation.

## Installation

Before using this code, ensure that you have the required dependencies installed. You can install them using the following command:

```bash
pip install aio-pika
```

## Usage

### 1. Initializing RabbitMQ Connection

```python
import asyncio
from your_module import RabbitClient

async def main():
    rabbit_url = "amqp://guest:guest@localhost:5672/"
    
    # Start the RabbitMQ connection
    await RabbitClient.start(url=rabbit_url)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
```

### 2. Adding Callbacks for Message Handling

```python
import asyncio
from your_module import RabbitClient, Callback

async def handle_message(message):
    print(f"Received message: {message}")

async def main():
    rabbit_url = "amqp://guest:guest@localhost:5672/"
    
    # Add a callback for handling messages from a specific queue
    callback = Callback(callback=handle_message, queue="your_queue_name")
    RabbitClient.add_callback(callback)

    # Start the RabbitMQ connection
    await RabbitClient.start(url=rabbit_url)
    
if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
```

### 3. Publishing Messages

```python
import asyncio
from your_module import RabbitClient

async def main():
    rabbit_url = "amqp://guest:guest@localhost:5672/"
    
    # Start the RabbitMQ connection
    await RabbitClient.start(url=rabbit_url)
    
    # Publish a message to a specific routing key and exchange
    await RabbitClient.publish(routing_key="your_routing_key", message="Hello, RabbitMQ!", exchange="your_exchange")

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
```

### 4. RPC (Remote Procedure Call) Implementation

```python
import asyncio
from your_module import RabbitRPC

async def main():
    rabbit_url = "amqp://guest:guest@localhost:5672/"
    
    # Start the RabbitMQ connection
    await RabbitRPC.start(url=rabbit_url)
    
    # Execute an RPC call
    response = await RabbitRPC.execute(routing_key="your_routing_key", exchange="your_exchange", param1="value1", param2="value2")
    print(f"RPC Response: {response.decode()}")

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
```

## Notes

- Ensure that RabbitMQ server is running and reachable at the specified URL.
- Customize the placeholders ("your_module", "your_queue_name", "your_routing_key", "your_exchange", etc.) with your specific values and names.

Feel free to modify and integrate this library into your project according to your requirements.
