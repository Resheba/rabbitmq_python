import asyncio
import uuid
from json import dumps
from asyncio import Future
from typing import Callable
from aio_pika import IncomingMessage
from aio_pika import RobustConnection
from aio_pika import RobustChannel
from aio_pika import RobustQueue
from aio_pika import connect_robust
from aio_pika import Message
from aio_pika import RobustExchange
from aio_pika.exceptions import AMQPConnectionError


class Callback:
    '''
    Class representing a callback for processing messages from a queue.

    Attributes:
        callback (Callable): Callback function for processing messages.
        queue (str): Name of the queue from which messages will be consumed.
        no_ack (bool): Flag indicating whether to acknowledge receiving messages without explicit acknowledgment.
    
    ----
    
    Класс, представляющий обратный вызов (callback) для обработки сообщений из очереди.

    Attributes:
        callback (Callable): Функция обратного вызова для обработки сообщений.
        queue (str): Имя очереди, из которой будут получаться сообщения.
        no_ack (bool): Флаг, указывающий, следует ли подтверждать получение сообщений без явного подтверждения.

    '''
    def __init__(self, 
                 callback: Callable, 
                 queue: str, 
                 *, 
                 no_ack: bool = False
                 ) -> None:
        self.callback: Callable = callback
        self.queue: str = queue
        self.no_ack: bool = no_ack


class RabbitBase:
    '''
    Base class for interacting with RabbitMQ.

    Attributes:
        _connection (RobustConnection): Connection object to RabbitMQ.
        _channel (RobustChannel): Channel object for message exchange.
        _recon_delay (float): Delay between reconnection attempts.
    
    ----

    Базовый класс для взаимодействия с RabbitMQ.

    Attributes:
        _connection (RobustConnection): Объект соединения с RabbitMQ.
        _channel (RobustChannel): Объект канала для обмена сообщениями.
        _recon_delay (float): Задержка между попытками переподключения.

    '''
    _connection: RobustConnection
    _channel: RobustChannel
    _recon_delay: float = 1

    @classmethod
    async def start(cls,
                    url: str
                    ) -> None:
        '''
        Method to initiate interaction with RabbitMQ. Connects the channel to the broker.

        Args:
            url (str): Connection string to RabbitMQ.

        Returns:
            None
        
        ----

        Метод для начала взаимодействия с RabbitMQ. Подключает канал к брокеру.

        Args:
            url (str): Строка подключения к RabbitMQ.

        Returns:
            None

        '''
        await cls._connect(url=url)

    @classmethod
    async def _connect(cls, url: str) -> None:
        '''
        Internal method for connecting to RabbitMQ.

        Args:
            url (str): Connection string to RabbitMQ.

        Returns:
            None

        ----

        Технический метод для подключения к RabbitMQ.

        Args:
            url (str): Строка подключения к RabbitMQ.

        Returns:
            None

        '''
        cls._connection: RobustConnection = await connect_robust(url=url)
        cls._channel: RobustChannel = await cls._connection.channel()

    @classmethod
    async def _reconnect(cls) -> None:
        '''Internal method for reconnecting to RabbitMQ (not used because pika automatically reconnects).

        Returns:
            None

        ----

        Технический метод для переподключения к RabbitMQ (не используется, так как pika автоматически переподключается).

        Returns:
            None

        '''
        await cls._connection.reconnect()
        await asyncio.sleep(cls._recon_delay)
        await cls._channel.reopen()
        await asyncio.sleep(cls._recon_delay)
    
    @classmethod
    async def _wait_reconnect(cls) -> None:
        '''
        Internal method to wait for the completion of reconnection.

        Returns:
            None

        Raises:
            AMQPConnectionError: If reconnection takes too long.

        ----

        Технический метод для ожидания завершения переподключения.

        Returns:
            None

        Raises:
            AMQPConnectionError: Если переподключение занимает слишком много времени.


        '''
        try_count: int = 0
        while cls._channel.is_closed:
            try_count += 1
            await asyncio.sleep(cls._recon_delay)
            if try_count > 10:
                raise AMQPConnectionError('Timeout.')


class RabbitClient(RabbitBase):
    """
    Class for working with RabbitMQ as a client (sending messages and handling callbacks).

    Attributes:
        _callbacks (list[Callback]): List of callbacks for handling messages.

    ----

    Класс для работы с RabbitMQ в роли клиента (отправка сообщений и обработка обратных вызовов).

    Attributes:
        _callbacks (list[Callback]): Список обратных вызовов для обработки сообщений.

    """
    _callbacks: list[Callback] = list()

    @classmethod
    async def start(cls, url: str) -> None:
        await super().start(url)
        for callback in cls._callbacks:
            queue: RobustQueue = await cls._channel.declare_queue(name=callback.queue)
            await queue.consume(callback=callback.callback, no_ack=callback.no_ack)
        del cls._callbacks

    @classmethod
    def add_callback(cls,
                        callback: Callback
                           ) -> None:
        """
        Method to add a callback to the list.

        Args:
            callback (Callback): Callback object to add to the list.

        Returns:
            None

        ----

        Метод для добавления обратного вызова в список.

        Args:
            callback (Callback): Объект Callback для добавления в список.

        Returns:
            None


        """
        cls._callbacks.append(callback)

    @classmethod
    async def publish(cls,
                      routing_key: str,
                      message: str | Message,
                      exchange: str = ''
                      ) -> None:
        """
        Method to publish a message to RabbitMQ.

        Args:
            routing_key (str): Routing key to determine which queue or exchange to use.
            message (str | Message): Text message or Message object to send.
            exchange (str): Exchange name.

        Returns:
            None

        Raises:
            AMQPConnectionError: If sending the message fails.

        ----

        Метод для публикации сообщения в RabbitMQ.

        Args:
            routing_key (str): Ключ маршрутизации для определения, какую очередь или обменник использовать.
            message (str | Message): Текстовое сообщение или объект Message для отправки.
            exchange (str): Имя обменника.

        Returns:
            None

        Raises:
            AMQPConnectionError: Если не удается отправить сообщение.

        """
        if isinstance(message, str):
            message: Message = Message(
                body=message.encode()
            )
        try:
            await cls._send(routing_key=routing_key, exchange=exchange, message=message)
        except AMQPConnectionError:
            await cls._wait_reconnect()
            await cls._send(routing_key=routing_key, exchange=exchange, message=message)

    @classmethod
    async def _send(cls,
                    routing_key: str,
                    exchange: str,
                    message: Message
                    ) -> None:
        '''
        Internal method to send a message to RabbitMQ.

        Args:
            routing_key (str): Routing key to determine which queue or exchange to use.
            exchange (str): Exchange name.
            message (Message): Message object to send.

        Returns:
            None

        Raises:
            AMQPConnectionError: If sending the message fails.

        ----

        Технический метод для отправки сообщения в RabbitMQ.

        Args:
            routing_key (str): Ключ маршрутизации для определения, какую очередь или биржу использовать.
            exchange (str): Имя биржи.
            message (Message): Объект сообщения для отправки.

        Returns:
            None

        Raises:
            AMQPConnectionError: Если отправка сообщения не удалась.

        '''
        if exchange:
            exchange: RobustExchange = await cls._channel.get_exchange(name=exchange)
        else:
            exchange: RobustExchange = cls._channel.default_exchange
        await exchange.publish(message=message, routing_key=routing_key)


class RabbitRPC(RabbitBase):
    '''
    Class for implementing RPC (Remote Procedure Call) in RabbitMQ.

    Attributes:
        _futures (dict[str, Future]): Dictionary to store Futures for correlating responses.

    ----

    Класс для реализации RPC (удаленного вызова процедур) в RabbitMQ.

    Attributes:
        _futures (dict[str, Future]): Словарь для хранения Futures для сопоставления ответов.

    '''
    _futures: dict[str, Future] = dict()

    @classmethod
    async def _on_message(cls, 
                          message: IncomingMessage
                          ) -> None:
        '''
        Internal method to handle incoming messages in RPC.

        Args:
            message (IncomingMessage): Incoming message object.

        Returns:
            None

        ----

        Технический метод для обработки входящих сообщений в RPC.

        Args:
            message (IncomingMessage): Объект входящего сообщения.

        Returns:
            None

        '''
        future: Future = cls._futures.pop(message.correlation_id, None)
        if future is None:
            print(f'Error callback {message}')
            return
        
        future.set_result(message.body)
        await message.ack()

    @classmethod
    async def execute(cls,
                      routing_key: str,
                      exchange: str = '',
                      **kwargs
                      ) -> bytes:
        '''
        Method to execute an RPC call.

        Args:
            routing_key (str): Routing key to determine which queue or exchange to use.
            exchange (str): Exchange name.
            **kwargs: Additional keyword arguments to pass in the RPC call.

        Returns:
            bytes: Response from the RPC call.

        ----

        Метод для выполнения вызова RPC.

        Args:
            routing_key (str): Ключ маршрутизации для определения, какую очередь или биржу использовать.
            exchange (str): Имя биржи.
            **kwargs: Дополнительные именованные аргументы для передачи в вызов RPC.

        Returns:
            bytes: Ответ от вызова RPC.

        '''
        reply_queue: RobustQueue = await cls._channel.declare_queue(exclusive=True, durable=True, auto_delete=True)
        await reply_queue.consume(callback=cls._on_message)
        task_id: str = str(uuid.uuid4())
        future: Future[bytes] = cls._connection.loop.create_future()

        cls._futures.update({task_id: future})

        if exchange:
            exchange: RobustExchange = await cls._channel.get_exchange(name=exchange)
        else:
            exchange: RobustExchange = cls._channel.default_exchange

        await exchange.publish(
            message=Message(
                body=(dumps(kwargs).encode()),
                content_type='application/json',
                correlation_id=task_id,
                reply_to=reply_queue.name
            ),
            routing_key=routing_key,
            mandatory=True
        )
        response: bytes = await future

        await reply_queue.delete(if_unused=False, if_empty=False)
        
        return response
              