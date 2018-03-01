#!/usr/bin/env python
import pika

credentials = pika.PlainCredentials('facerec', 'facerec')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='192.168.0.111', credentials=credentials))
channel = connection.channel()

channel.queue_declare(queue='default')

def callback(ch, method, properties, body):
    print "got", len(body), "bytes"

channel.basic_consume(callback,
                      queue='default',
                      no_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
