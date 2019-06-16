import boto3

def run():
  print('Watching for messages')
  sqs = boto3.resource('sqs')
  queue = sqs.get_queue_by_name(QueueName='keda-test')

  while True:
    for message in queue.receive_messages(WaitTimeSeconds=20):
      print(f"Message from queue {message.body}")
      message.delete()

if __name__ == '__main__':
  run()