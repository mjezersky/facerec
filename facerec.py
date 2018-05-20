#!/usr/bin/python
import facerec_worker
s = facerec_worker.MQServer()


# Worker group, needs to match with main program
s.WORKER_GROUP_NAME = "default"

# Identifier of the worker in worker group, needs to be unique among the group
s.IDENTIFIER = "Worker A"

# RabbitMQ server information
s.MQ_SERVER_IP = "192.168.43.254"
s.MQ_SERVER_PORT = 5672
s.MQ_USERNAME = "facerec"
s.MQ_PASSWORD = "facerecc"

# Worker configuration
# SCALE_FACTOR 0.6 or 0.7 recommended for 1920*1080, 0.9 below 1280*720
# or even 0.9 for 1920*1080, if there are enough workers in the group
s.SCALE_FACTOR = 0.6
# confidence threshold (not vector distance!)
s.RECOG_THRESHOLD = 0.575


facerec_worker.runserver(s)
