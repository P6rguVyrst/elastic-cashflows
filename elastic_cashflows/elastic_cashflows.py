# -*- coding: utf-8 -*-
"""Main module."""
import re
import urllib3
import csv
import hashlib
import logging
from elasticsearch import Elasticsearch
from pprint import pprint as pp
from dateutil.parser import parse

logger = logging.getLogger(__name__)

class BankStatement(object):

    def __init__(self):
        re_time = '^(\d{1,2})(:\d{1,2})'
        re_date = '^(\d{2})[/.-](\d{2})[/.-](\d{4})'
        self.is_date = re.compile(re_date)
        self.is_time = re.compile(re_time)

    def reader(self, f, delimiter):
        fieldnames = (
            "account_id",
            "document_nr",
            "date",
            "payee_account_id",
            "payee_name",
            "payee_bank_code",
            "transaction_type",
            "transaction",
            "ammount",
            "reference_nr",
            "archive_id",
            "description",
            "service_fee",
            "currency",
            "registry_id",
            "payee_BIC",
            "transaction_initiator_name",
            "transaction_ref",
            "account_ref"
        )
        csvfile = open(f, 'r')
        return csv.DictReader(csvfile, fieldnames, delimiter=delimiter)

    def formater(self, data, dayfirst):
        formatted_data = []
        next(data, None) #Skip first line
        for row in data:
            row = self.format_row(row, dayfirst)
            id_seed = '{}{}{}{}{}'.format(
                row.get('date'),
                row.get('account_id'),
                row.get('archive_id'),
                row.get('transaction_type'),
                row.get('currency')
            )
            desc = row.get('description')
            if desc:
                dt = self.analyze_description(desc)
                if dt.get('transaction_time'):
                    row['transaction_time'] = parse(dt['transaction_time'], dayfirst=True)
                if dt.get('tags'):
                    row['tags'] = dt['tags']

            row['id'] = self.generate_hash(id_seed)
            logger.info(row)
            formatted_data.append(row)

        return formatted_data

    def format_row(self, row, dayfirst):
        x = {k: ' '.join(v.split()) for k, v in row.items() if v}
        x['date'] = parse(x['date'], dayfirst=dayfirst)
        x['ammount'] = float(x['ammount'].replace(',', '.').strip('-'))
        x['service_fee'] = float(x['service_fee'].replace(',', '.').strip('-'))
        return x

    def analyze_description(self, description):
        desc = description.split()
        datetime = []
        for item in desc:
            if self.is_date.match(item):
                datetime.append(item)
            elif self.is_time.match(item):
                datetime.append(item)

            if '...' in item:
                desc.extend(item.split('...'))
                desc.remove(item)

        description = [x.lower() for x in  desc if x not in datetime]
        datetime = ' '.join(datetime)
        return {'transaction_time': datetime, 'tags': description}

    def generate_hash(self, data):
        return hashlib.sha1(str.encode(data)).hexdigest()

class ElasticLoader(object):

    def __init__(self, host, port, usr, pwd, protocol='https', secure=True):
        try:
            self.es = self.connection(protocol, host, port, usr, pwd, secure)
        except elasticsearch.exceptions.AuthenticationException:
            print('Check your Elasticsearch connection parameters at /etc/elastic_cashflows/elastic_cashlows.cfg')

    def connection(self, protocol, host, port, usr, pwd, secure):
        if secure:
            return Elasticsearch(
                ['{0}://{1}:{2}@{3}:{4}'.format(protocol, usr, pwd, host, port)]
            )
        else:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            conn = Elasticsearch(
                    ['{0}://{1}:{2}@{3}:{4}'.format(protocol, usr, pwd, host, port)],
                    verify_certs=False
                )
            return conn


    def load_list(self, data):
        [self.load(line) for line in data]

    def load(self, data):

        e = self.es.index(
            index='personal-finances',
            doc_type='transactions',
            id=data['id'],
            body=data
        )
        pp(e)
        logger.info(e)



