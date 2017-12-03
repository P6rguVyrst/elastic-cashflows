# -*- coding: utf-8 -*-

"""Console script for elastic_cashflows."""

import click
import logging
import logging.config
import configparser
from glob import glob
from pprint import pprint as pp

from elastic_cashflows.elastic_cashflows import BankStatement, ElasticLoader

APP_CONFIG = '/etc/elastic_cashflows/elastic_cashflows.cfg'
logging.config.fileConfig(APP_CONFIG)
logger = logging.getLogger('elastic_cashflows')

def find_files(source_path, filetype='csv'):
    return glob('{}/*.{}'.format(source_path, filetype))

@click.command()
@click.option('--source', prompt='Source', help='Root folder to look for bank exports')
@click.option('--delimiter', default=',')
@click.option('--dayfirst', default=False)
def main(source, delimiter, dayfirst):
    """Console script for elastic_cashflows."""

    bs = BankStatement()

    config = configparser.ConfigParser()
    config.read(APP_CONFIG)

    es_protocol = config['elastic']['protocol']
    es_host = config['elastic']['host']
    es_port = config['elastic']['port']
    es_user = config['elastic']['user']
    es_pass = config['elastic']['pass']

    elastic = ElasticLoader(
        es_host, es_port, es_user,
        es_pass, protocol=es_protocol, secure=False
    )

    files = find_files(source)
    logger.debug('Found files: {}'.format(files))
    pp('Found files: {}'.format(files))


    for f in files:
        data = bs.reader(f, delimiter)
        formatted_data = bs.formater(data, dayfirst)
        elastic.load_list(formatted_data)



if __name__ == "__main__":
    main()
