import os

from sekg.graph.factory import GraphInstanceFactory
from sekg.mysql.factory import MysqlSessionFactory

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
NEO4J_CONFIG_PATH = os.path.join(ROOT_DIR, 'neo4j_config.json')
GRAPH_FACTORY = GraphInstanceFactory(NEO4J_CONFIG_PATH)
MYSQL_CONFIG_PATH = os.path.join(ROOT_DIR, 'mysql_config.json')
MYSQL_FACTORY = MysqlSessionFactory(MYSQL_CONFIG_PATH)
# the data dir
DATA_DIR = os.path.join(ROOT_DIR, 'data')
# the output dir
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output')
# the so dir
SO_DIR = os.path.join(OUTPUT_DIR, 'so')
SCENARIO_NUM = 8
KNOWLEDGE_NUM = 17
