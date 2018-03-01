#!/usr/bin/env python
import pika
import threading

identifier = "DEFAULT_WORKER"

credentials = pika.PlainCredentials('facerec', 'facerec')

def callback(ch, method, properties, body):
    print "got", len(body), "bytes"
    ch.basic_publish(exchange='',
                      routing_key='feedback',
                      body="1,"+identifier+",0,none,0,[]")

def broadcastResp(ch, method, properties, body):
   print "got", len(body), "bytes"
   ch.basic_publish(exchange='',
                      routing_key='feedback',
                      body="0,"+identifier+",0,none,0,[]")

def ch1():
	connection = pika.BlockingConnection(pika.ConnectionParameters(host='192.168.1.8', 
credentials=credentials))
	channel = connection.channel()

	channel.exchange_declare(exchange='broadcast', exchange_type='fanout')
	channel.queue_declare(queue="feedback")
	result = channel.queue_declare(exclusive=True)
	queue_name = result.method.queue

	channel.queue_bind(exchange="broadcast", queue=queue_name)


	channel.basic_consume(broadcastResp,
                      queue=queue_name,
                      no_ack=True)

	print(' [*] Waiting for messages. To exit press CTRL+C')
	channel.start_consuming()

def ch2():
	connection = pika.BlockingConnection(pika.ConnectionParameters(host='192.168.1.8', 
credentials=credentials))
	channel2 = connection.channel()

	channel2.queue_declare(queue=identifier)
	channel2.queue_declare(queue="feedback")

	channel2.basic_consume(callback,
                      queue=identifier,
                      no_ack=True)

	mq_recieve_thread = threading.Thread(target=channel2.start_consuming)
	mq_recieve_thread.daemon = True
	mq_recieve_thread.start()


ch2()
ch1()
