from datetime import timedelta

broker_url = 'pyamqp://guest@localhost//'
result_backend = 'db+mysql://user:password@localhost/mydatabase'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Europe/Oslo'
enable_utc = True
task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'
task_default_delivery_mode = 'persistent'
task_default_priority = 5
task_time_limit = 30 * 60
task_soft_time_limit = 25 * 60
task_default_rate_limit = '10/s'
beat_schedule = {
    'run-every-5-seconds': {
        'task': 'tasks.run_periodic_task',
        'schedule': timedelta(seconds=5),
    },
}
