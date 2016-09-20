__author__ = "ftan"

from database import *


# Search by ph_product_name and search by ph_product_line part.
def get_choices_by_attribute(attribute):
    choices_list = []
    for row in SkuEntry.select():
        choices_list.append(eval("row.{0}".format(attribute)))
    choices_list = list(set(choices_list))
    choices_list.sort()
    choices = []
    for i in choices_list:
        t = (i, i)
        choices.append(t)
    choices.insert(0, ("", "ALL Products"))
    return choices
ph_product_line_choices = get_choices_by_attribute("ph_product_line")
ph_product_name_choices = get_choices_by_attribute("ph_product_name")

# Advanced Search part.
# The attributes. key is the displayed attribute name, value is the attribute name in candlepin.
Attributes_dict_list = [{"--Select Attribute--": "--Select Attribute--"},
                      {"SKU": "id"},
                      {"Product Hierarchy: Product Category": "ph_category"},
                      {"Product Hierarchy: Product Line": "ph_product_line"},
                      {"Product Hierarchy: Product Name": "ph_product_name"},
                      {"Product Name": "name"},
                      {"Virt Limit": "virt_limit"},
                      {"Socket(s)": "sockets"},
                      {"VCPU": "vcpu"},
                      {"Multiplier": "multiplier"},
                      {"Unlimited Product": "unlimited_product"},
                      {"Required Consumer Type": "requires_consumer_type"},
                      {"Product Family": "product_family"},
                      {"Management Enabled": "management_enabled"},
                      {"Variant": "variant"},
                      {"Support Level": "support_level"},
                      {"Support Type": "support_type"},
                      {"Enabled Consumer Types": "enabled_consumer_types"},
                      {"Virt-only": "virt_only"},
                      {"Cores": "cores"},
                      {"JON Management": "jon_management"},
                      {"RAM": "ram"},
                      {"Instance Based Virt Multiplier": "instance_multiplier"},
                      {"Cloud Access Enabled": "cloud_access_enabled"},
                      {"Stacking ID": "stacking_id"},
                      {"Multi Entitlement": "multi_entitlement"},
                      {"Host Limited": "host_limited"},
                      {"Derived SKU": "derived_sku"},
                      {"Eng Productid(s)": "eng_product_ids"},
                      {"Arch": "arch"},
                      {"Username": "username"}]


def handle_attribute(attribute):
    """
    The function is used to handle the attribute name display in tool and in candlepin.
    For example, "Arch" is the display, but "arch" is used when to execute sql in db.
    :return: If select "Arch", then "arch" is returned.
    """
    for i in Attributes_dict_list:
        if i.keys()[0] == attribute:
            return i[attribute]


attribute_choices = []
for i in [i.keys()[0] for i in Attributes_dict_list]:
    t = (i, i)
    attribute_choices.append(t)

# The search method.
select = ["", "contains", "does not contain", "equals", "does not equal", "greater than", "less than", "is empty or null",
          "is not empty or null", "is true", "is not true"]
select_choices = []
for i in select:
    t = (i, i)
    select_choices.append(t)





