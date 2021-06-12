from datetime import timedelta
import json
import os
import sys

from airflow import DAG

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from task_creator.task_creator import TaskCreator
from task_creator.strategies.python_operator_strategy import PythonOperatorStrategy
from operator_factory.airflow_operator_factory import AirflowOperatorFactory


class DAGFactory:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.type_casting()
        self.dag = DAG(**kwargs)

    def type_casting(self) -> None:
        if 'user_defined_macros' in self.kwargs:
            self.kwargs.update(default_args = json.loads(self.kwargs['user_defined_macros']))
        if 'user_defined_filters' in self.kwargs:
            self.kwargs.update(default_args = json.loads(self.kwargs['user_defined_filters']))
        if 'default_args' in self.kwargs:
            self.kwargs.update(default_args = json.loads(self.kwargs['default_args']))
        if 'params' in self.kwargs:
            self.kwargs.update(default_args = json.loads(self.kwargs['params']))
        if 'access_control' in self.kwargs:
            self.kwargs.update(default_args = json.loads(self.kwargs['access_control']))
        if 'jinja_environment_kwargs' in self.kwargs:
            self.kwargs.update(default_args = json.loads(self.kwargs['jinja_environment_kwargs']))

    def get_airflow_dag(self, tasks):
        #dag = self.create_dag(self.dag_id, self.default_args, self.schedule, self.catchup)

        start = AirflowOperatorFactory.get_dummy_operator(self.dag, 'start')
        end = AirflowOperatorFactory.get_dummy_operator(self.dag, 'end')

        tasks_dict = {}
        tasks_dict['start'] = start
        tasks_dict['end'] = end

        for task in tasks:
            if task['strategy'] == 'PythonOperatorStrategy':
                strategy = PythonOperatorStrategy(
                    task['name'],
                    task['args'])
                task_creator = TaskCreator(strategy)
                tasks_dict[task['name']] = task_creator.create_task(self.dag)
            else:
                msg = "Estrategia desconocida: {}"
                raise NameError(msg.format(task['strategy']))

        all_depends_on = []
        for task in tasks:
            task_depends_on = 'start' if task['depends_on'] is None else task['depends_on'] # !
            depends_on_list = task_depends_on.split(',') # !
            all_depends_on.extend(depends_on_list)
            for depends_on in depends_on_list:
                tasks_dict[depends_on] >> tasks_dict[task['name']]

        name_list = [task['name'] for task in tasks]
        # no_blocking_tasks = list(set(name_list) - set(all_depends_on))
        no_blocking_tasks = list(filter(lambda task: task not in all_depends_on, name_list))

        for task_name in no_blocking_tasks:
            tasks_dict[task_name] >> end

        return self.dag