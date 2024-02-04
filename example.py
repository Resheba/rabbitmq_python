import asyncio
from aio_pika import IncomingMessage, Message
from client import RabbitClient, Callback


async def callback(message: IncomingMessage) -> None:
    print(message)
    print(message.body.decode())
    await message.ack()
    routing_key: str = message.reply_to or input('RoutingKey: ')
    text: str = input('Message: ')
    await RabbitClient.publish(routing_key=routing_key, 
                               message=Message(
                                   body=text.encode(),
                                   correlation_id=message.correlation_id,
                                   )
                                        )


async def main():
    RabbitClient.add_callback(callback=Callback(callback=callback, queue='test'))
    await RabbitClient.start(url='amqp://localhost:5672')
    

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
