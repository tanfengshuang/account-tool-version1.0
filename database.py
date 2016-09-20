__author__ = "tcoufal"
__update__ = "ftan"

import logging

from json import dumps
try:
    from peewee import Model, CharField, Field, DoesNotExist, MySQLDatabase
except ImportError:
    print 'This script needs to have peewee installed: \"pip install peewee\"'\
        '\nMaybe you are also missing a library for MySQL and MariaDB: '\
        '\"pip install PyMySQL\" or \"pip install MySQLdb\"\n'


def check_sku(sku):
    try:
        SkuEntry.get(SkuEntry.id==sku.upper())
    except SkuEntry.DoesNotExist:
        logging.error("sku %s doesn't exist in database" % sku)
        return 1
    else:
        return 0

class _IntegerField(Field):
    db_field = 'int'
    def db_value(self, value):
        if not value or str(value).lower() in ('n/a', 'na'):
            return -1
        elif str(value).lower() == 'unlimited':
            return -2
        else:
            return int(value)
    def python_value(self, value):
        if not value or value == -1:
            return 'n/a'
        elif value == -2:
            return 'unlimited'
        else:
            return str(value)


class _BooleanField(Field):
    db_field = 'bool'
    def db_value(self, value):
        if str(value).lower() in ('y', 'yes', 'true', '1'):
            return True
        elif str(value).lower() in ('n', 'no', 'false', '0'):
            return False
        else:
            return
    def python_value(self, value):
        return bool(value)


class SkuEntry(Model):
    """
    Class for an entry in database (generated automatically by pwiz)
    ------------------------------------------------------------------------
    This will allow you to work very easy with the database. First of all we
    need to connect to the DB - for that we have Meta subclass class. Then
    all columns have their own variable, and you can easily filter, search...
    """
    arch = CharField(null=True)
    cloud_access_enabled = _BooleanField(null=True, default=0)
    cores = _IntegerField(null=True)
    derived_sku = CharField(null=True)
    enabled_consumer_types = CharField(null=True)
    eng_product_ids = CharField(null=True)
    host_limited = _BooleanField(null=True, default=0)
    instance_multiplier = _IntegerField(null=True)
    jon_management = _BooleanField(null=True, default=0)
    management_enabled = _BooleanField(null=True, default=0)
    multi_entitlement = _BooleanField(null=True, db_column='multi-entitlement')
    multiplier = _IntegerField(null=True)
    name = CharField(null=True)
    ph_category = CharField(null=True)
    ph_product_line = CharField(null=True)
    ph_product_name = CharField(null=True)
    product_family = CharField(null=True)
    ram = _IntegerField(null=True)
    requires_consumer_type = CharField(null=True)
    id = CharField(primary_key=True)
    sockets = _IntegerField(null=True)
    stacking_id = CharField(null=True)
    support_level = CharField(null=True)
    support_type = CharField(null=True)
    unlimited_product = _BooleanField(null=True, default=0)
    username = CharField(null=True)
    variant = CharField(null=True)
    vcpu = _IntegerField(null=True)
    virt_limit = _IntegerField(null=True)
    virt_only = _BooleanField(null=True, default=0)
    def dict(self):
        r = dict()
        for k in self._meta.fields.keys():
            try:
                r[k] = str(getattr(self, k))
            except:
                r[k] = dumps(getattr(self, k))
        return r
    class Meta:
        database = MySQLDatabase(
            'sku_db',
            host='account-manager-stage.app.eng.rdu2.redhat.com',
            password='redhat',
            user='account_tool')
        db_table = 'sku_attributes_all'
