
DOIT_CONFIG = {
    'default_tasks': ['default'],
    'verbosity': 2,
}

def task_default():
    return {
        'actions': ['doit list'],
    }

def task_dev():
    return {
        'actions': ['poetry run fastapi dev src/lockss/projectoscope/main.py'],
    }
