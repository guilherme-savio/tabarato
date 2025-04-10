from core.extract.angeloni import AngeloniExtractor
from datetime import datetime
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator


sys.path.append('/opt/airflow/dags/core')

with DAG("angeloni_extract_dag", start_date = datetime(2025, 3, 15), schedule_interval = None, catchup = False) as dag:
    extract_task = PythonOperator(
        task_id = "extract_task",
        python_callable = AngeloniExtractor.extract
    )

    load_task = PythonOperator(
        task_id = "load_task",
        python_callable = AngeloniExtractor.load
    )

    trigger_transform_task = TriggerDagRunOperator(
        task_id = "trigger_transform_task",
        trigger_dag_id = "angeloni_transform_dag"
    )

    extract_task >> load_task >> trigger_transform_task