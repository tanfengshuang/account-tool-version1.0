__author__ = "ftan"

import logging.handlers
import json
import commands
import requests
import time
import os
import sys

from peewee import fn
from xml.dom.minidom import Document

from rhsm import connection
from environments import *
from database import *

# Set default encoding
reload(sys)
sys.setdefaultencoding('utf-8')

####################################
##          Base Functions        ##
####################################
def str_append(str1, str2):
    if str1 == "":
        str1 += str2
    else:
        str1 += ',' + str2
    return str1


def get_orgId(account):
    # curl -s -X GET -k 'http://servicejava.edge.stage.ext.phx2.redhat.com/svcrest/user/v3/login={username}' | python -mjson.tool
    # curl -s -X GET -u candlepin_admin:candlepin_admin  -k 'http://candlepin.dist.stage.ext.phx2.redhat.com/candlepin/users/{username}/owners' | python -mjson.tool
    r = requests.get(REST_USER + "/login=%s" % account)
    if r.content == '[]':
        print "Account %s doesn't exist" % account
        return None
    else:
        org_id = str(json.loads(r.content[1:-1])['orgId'])
        return org_id


def get_multiplier_from_db(sku):
    logging.info("Get multiplier of sku %s from db." % sku)
    multiplier = 1
    instance_multiplier = 1
    for row in SkuEntry.select().where(fn.Lower(SkuEntry.id) == sku.upper()):
        multiplier = int(row.multiplier)
        instance_multiplier = int(row.instance_multiplier)
    return multiplier, instance_multiplier


def get_multiplier_from_curl(username, password, sku):
    # Get the value of multiplier
    # Command: curl -s -u ftan_test_30:redhat -k https://subscription.rhn.stage.redhat.com/subscription/products/MCT3115 | python -mjson.tool
    multiplier = 1
    instance_multiplier = 1
    url = "https://" + stage_candlepin_server + "/subscription/products/" + sku
    cmd = 'curl -s -u %s:%s -k %s | python -mjson.tool' % (username, password, url)
    ret, output = commands.getstatusoutput(cmd)
    logging.info(cmd)
    logging.info("%s" % output)
    i = 0
    while i < 5 and ret != 0:
        time.sleep(10)
        logging.info("Try to get info with curl command again - %s.\n" % i)
        ret, output = commands.getstatusoutput(cmd)
        logging.info("%s" % output)
        i += 1
    if ret == 0:
        multiplier = json.loads(output)["multiplier"]
        attributes = json.loads(output)["attributes"]
        for attr in attributes:
            if attr["name"] == "instance_multiplier":
                instance_multiplier = int(attr["value"])
        logging.info("multiplier of sku %s: %s" % (sku, multiplier))
        logging.info("instance_multiplier of sku %s: %s" % (sku, instance_multiplier))
    return multiplier, instance_multiplier


def check_password(username, password):
    try:
        con = connection.UEPConnection(stage_candlepin_server, username=username, password=password)
        con.getOwnerList(con.username)
    except connection.RestlibException, e:
        if "You must first accept Red Hat's Terms and conditions" in str(e):
            # Didn't accept Red Hat's Terms and conditions
            #   RestlibException: You must first accept Red Hat's Terms and conditions.
            #   Please visit https://www.redhat.com/wapps/ugc . You may have to log out of and back into
            #   the Customer Portal in order to see the terms.
            org_id = get_orgId(username)
            i = 0
            while check_accept_terms(username, password):
                logging.info("Accept Terms")
                accept_terms(org_id, username, password)
                logging.info("Refresh")
                i += 1
                if i == 5:
                    break
            refresh_account(username)
        if "Invalid username or password" in str(e):
            # Incorrect password
            #   RestlibException: Invalid username or password. To create a login,
            #   please visit https://www.redhat.com/wapps/ugc/register.html
            return 1
    except connection.BadCertificateException, e:
        if "BadCertificateException" in str(e):
            #raise BadCertificateException(cert_path)
            #rhsm.connection.BadCertificateException: Bad certificate at /etc/rhsm/ca/candlepin-stage.pem
            # Correct Password although the bad certificate
            return 0
    # Correct Password
    return 0


def check_user(username):
    r = requests.get(REST_USER + "/login=%s" % username)
    logging.info("To check if account %s exists:" % username)
    if username in r.content:
        # the requested account already exists, return 0
        logging.info("Account %s exists." % username)
        return 0
    else:
        # the requested account doesn't exist, return 1
        logging.info("Account %s doesn't exist." % username)
        return 1


def find_or_create_user(username, password, first_name="first_name", last_name="last_name"):
    user_info = {
        "login": username,
        "loginUppercase": username.upper(),
        "password": password,
        "system": "WEB",
        "userType": "P",
        "personalInfo": {
            "company": "Default User",
            "locale": "en_US",
            "phoneNumber": "1234567890",
            "email": "test@redhat.com",
            "firstName": first_name,
            "lastName": last_name,
            "greeting": "Mr."
        },
        "personalSite": {
            "siteType": "MARKETING",
            "address": {
                "address1": "100 E. Davie St.",
                "city": "Raleigh",
                "state": "NC",
                "county": "Wake",
                "countryCode": "US",
                "postalCode": "27601"
            },
            "contactInfo": {
                    "emailAddress": "test@redhat.com",
                    "phoneNumber": "1234567890"
            }
        }
    }
    logging.info("** Begin Fun find_or_create_user")
    r = requests.get(REST_USER + "/login=%s" % username)
    if username not in r.content:
        logging.info("Account %s doesn't exist, create it now!" % username)
        requests.post(REST_USER+"/create", headers={'content-type': 'application/json'}, data=json.dumps(user_info))
        r = requests.get(REST_USER + "/login=%s" % username)
    org_id = str(json.loads(r.content[1:-1])['orgId'])
    logging.info("The organization id for account %s is %s" % (username, org_id))
    logging.info("** End Fun find_or_create_user")
    return org_id

def hock_sku(username, sku, quantity, start_date):
    hock_info = {
        "regnumType": "entitlement",
        "satelliteVersion": "",
        "login": username,
        "vendor": "REDHAT",
        "sendMail": False,
        "notifyVendor": False,
        "header": {
            "companyName": "",
            "customerNumber": 1234567890,
            "customerContactName": "Hockeye",
            "customerContactEmail": "dev-null@redhat.com",
            "customerRhLoginId": "qa@redhat.com",
            "opportunityNumber": 0,
            "emailType": "ENGLISH",
            "industry": "Software",
            "salesRepName": "Salesguy",
            "salesRepEmail": "dev-null@redhat.com",
            "rhPartnerDevMgrName": "DevManager",
            "rhPartnerDevMgrEmail": "dev-null@redhat.com",
            "partnerClassification": "",
            "classificationOther": "",
            "promocode": "",
            "revPublication": "",
            "rhManagerName": "Manager",
            "rhManagerEmail": "dev-null@redhat.com",
            "yourHockerName": "Genie",
            "yourHockerEmail": "dev-null@redhat.com",
            "publicationTitle": "",
            "publisher": "",
            "expectedPublicationDate": "",
            "program": {
                "id": 1,
                "shortName": "PRODUCTION",
                "name": "Production Hock",
                "description": "Product Code Creation for Subscription Operations",
                "active": True,
                "quota": 100,
                "group": "staff:pm:hock",
                "bccEmails": "dev-null@redhat.com",
                "addtEmails": "dev-null@redhat.com"
            }
        },
        "lines": [{
            "productSKU": sku,
            "serviceTagHashed": False,
            "additionalEmails": [],
            "ccList": [],
            "bccList": [],
            "numSuperRegnums": 1,
            "lineItem": {
                "sku": sku,
                "opUnit": "",
                "quantity": quantity,
                "zuper": True,
                "replicator": {"replicatorId": 30},
                "reason": {"id": "14"},
                "subject": "",
                "comments": "",
                "completed": False,
                "renew": False,
                "entitlementStartDate": "{0}".format(start_date),
                "satelliteVersion": "",
                "poNumber": "",
                "salesOrderNumber": "",
                "emailCc": "",
                "emailBcc": "",
                "emailType": "ENDUSER",
                "recipient": "",
                "webContactId": "",
                "groupIdentifier": "",
                "duration": "365 days", #"1 year",
                "opUnitId": 103,
                "userAcctNumber": "",
                "partnerAcctNumber": "",
                "replicatorAcctNumber": ""
            }
        }]
    }
    logging.info("** Begin Fun hock_sku")
    logging.info("Hock sku: %s,%s" % (sku, quantity))
    regnum = None
    try:
        regnum_response = requests.put(REST_REGNUM+'/hock/order', headers={'content-type': 'application/json'}, data=json.dumps(hock_info))
        regnum = str(json.loads(regnum_response.content)['regNumbers'][0][0]['regNumber'])
    except Exception, e:
        # ('Connection aborted.', error(104, 'Connection reset by peer'))
        logging.error(e)
        logging.error("Failed to add SKU %s into Account %s" % (sku, username))
    logging.info("Register Number for account %s: %s" % (username, regnum))
    logging.info("** End Fun hock_sku")
    return regnum


def activate_regnum(username, org_id, regnum, start_date=time.strftime('%Y-%m-%d', time.localtime(time.time()))):
    logging.info("** Begin Fun activate_regnum for user %s" % username)
    activation_info = {
        "activationKey": regnum,
        "vendor": "REDHAT",
        "startDate": "{0}".format(start_date),
        "userName": username,
        "webCustomerId": org_id,
        "systemName": "genie"
    }
    response = requests.post(REST_ACTIVATION+'/activate', headers={'content-type': 'application/json'}, data=json.dumps(activation_info))
    logging.info("%s" % response.content)
    if "Reg number product not active for SKU" in response.content:
        logging.info("Failed to active register number %s" % regnum)
        logging.info("** End Fun activate_regnum")
        return 1
    else:
        logging.info("Succeed to active register number %s" % regnum)
        logging.info("** End Fun activate_regnum")
        return 0


def check_accept_terms(username, password):
    try:
        con = connection.UEPConnection(stage_candlepin_server, username=username, password=password)
        con.getOwnerList(con.username)
    except connection.RestlibException, e:
        if "You must first accept Red Hat's Terms and conditions" in str(e):
            return 1


def accept_terms(org_id, username, password):
    logging.info("** Begin Fun accept_terms")
    user_content = requests.get(REST_USER+"/orgId=%s" % org_id)
    user_id = json.loads(user_content.content)[0]["id"]
    oracleCustomerNumber = json.loads(user_content.content)[0]["customer"]["oracleCustomerNumber"]
    #logging.debug("user content response:")
    #logging.debug("%s" % user_content)
    logging.info("user id: %s" % user_id)
    logging.info("oracleCustomerNumber: %s" % oracleCustomerNumber)

    customer_content = requests.get(REST_USER+"/customers/search?oracleCustomerNumber=%s&max=10" % oracleCustomerNumber)
    customer_id = json.loads(customer_content.content)[0]["id"]
    logging.info("customer_id: %s" % customer_id)

    terms_content = requests.get(REST_TERMS+"/status/userId=%s" % user_id)
    unacknowledged_terms = json.loads(terms_content.content)["unacknowledged"]
    if unacknowledged_terms == [] and check_accept_terms(username, password):
        acknowledged_terms = json.loads(terms_content.content)["acknowledged"]
        logging.info("acknowledged_terms: %s" % acknowledged_terms)
        unacknowledged_terms.append(acknowledged_terms)
    logging.info("unacknowledged_terms: %s" % unacknowledged_terms)

    for term in unacknowledged_terms:
        term_id = term["id"]
        requests.put(REST_TERMS+"/ack/terms_id=%s/userid=%s/customerid=%s/type=ACCEPT" % (term_id, user_id, customer_id))
        logging.info("Accept Terms %s." % term_id)
    logging.info("** End Fun accept_terms")

def refresh_account(username):
    logging.info("** Begin Fun refresh_account for user %s" % username)
    result = 0
    org_id = get_orgId(username)
    logging.info("Get the organization id of account %s: %s" % (username, org_id))
    cmd = "curl -k -X PUT -u candlepin_admin:candlepin_admin http://candlepin.dist.stage.ext.phx2.redhat.com/candlepin/owners/%s/subscriptions?auto_create_owner=true" % org_id
    ret, output = commands.getstatusoutput(cmd)
    if "ERROR" in output:
        result = 3
        logging.info("Refresh organization id %s." % org_id)
    logging.info("** End Fun refresh_account")
    return result


def account_info(account_info_list):
    pass_info = ""
    error_info = ""
    empty_info = ""
    quantity_unlimited = ""
    quantity_mark = False
    # test_ftan_1,redhat,test_ftan_2,redhat
    length = len(account_info_list)
    for account_info in account_info_list[::2]:
        username = account_info.strip()
        if username == "":
            break
        index = account_info_list.index(account_info) + 1
        if index < length:
            password = account_info_list[index].strip()
            if password == "":
                password = "redhat"
        else:
            error_info += "%s - **ERROR: No password or username was provided\n" % username
            continue
        org_id = ""
        try:
            con = connection.UEPConnection(stage_candlepin_server, username=username, password=password)
            org_id = con.getOwnerList(con.username)[0]['key']
        except connection.RestlibException, e:
            if "You must first accept Red Hat's Terms and conditions" in str(e):
                # Didn't accept Red Hat's Terms and conditions
                #   RestlibException: You must first accept Red Hat's Terms and conditions.
                #   Please visit https://www.redhat.com/wapps/ugc . You may have to log out of and back into
                #   the Customer Portal in order to see the terms.
                logging.error("%s - RestlibException: You must first accept Red Hat's Terms and conditions." % username)
                org_id = get_orgId(username)
                i = 0
                while check_accept_terms(username, password):
                    logging.info("Accept Terms")
                    accept_terms(org_id, username, password)
                    logging.info("Refresh")
                    i += 1
                    if i == 5:
                        break
                refresh_account(username)
                if check_accept_terms(username, password):
                    error_info += "%s,%s - **ERROR: You must first accept Red Hat's Terms and conditions.\n" % (username, password)
                    continue
            if "Invalid username or password" in str(e):
                # Incorrect password
                #   RestlibException: Invalid username or password. To create a login,
                #   please visit https://www.redhat.com/wapps/ugc/register.html
                logging.error("%s - RestlibException: Invalid username or password. To create a login," % username)
                if check_user(username):
                    error_info += "%s,%s - **ERROR: Invalid username, this account doesn't exist\n" % (username, password)
                else:
                    error_info += "%s,%s - **ERROR: Invalid password\n" % (username, password)
                continue
        except IndexError:
            # Traceback (most recent call last):
            #  File "<stdin>", line 1, in <module>
            # IndexError: list index out of range
            error_info += "%s,%s - **ERROR: Failed to get SKUs, please check if account %s exists\n" % (username, password, username)
            continue
        except connection.BadCertificateException, e:
            if "BadCertificateException" in str(e):
                #raise BadCertificateException(cert_path)
                #rhsm.connection.BadCertificateException: Bad certificate at /etc/rhsm/ca/candlepin-stage.pem
                error_info += "%s,%s - **ERROR: Failed to get SKUs, please check if account %s exists\n" % (username, password, username)
                continue

        try:
            pool_list = con.getPoolsList(owner=org_id)
            pass_info_new = ""
            if len(pool_list) > 0:
                pass_info_new += "%s,%s," % (username, password)
                for pool in pool_list:
                    # pool["productId"], pool["quantity"]
                    # RV0145582 10
                    # RH0103708 10
                    if pool["type"] == "NORMAL":
                        sku = pool["productId"]
                        quantity = pool["quantity"]
                        multiplier, instance_multiplier = get_multiplier_from_curl(username, password, sku)
                        # pool["quantity"] = quantity * instance_multiplier * multiplier
                        quantity = quantity/multiplier/instance_multiplier
                        if quantity == -1:
                            quantity = 10000
                            quantity_mark = True
                        pass_info_new += "%s,%s," % (sku, quantity)
                if quantity_mark is True:
                    quantity_unlimited += "%s," % sku
                pass_info_new = handle_long_str(pass_info_new)
                pass_info = pass_info + pass_info_new + "\n"
            else:
                empty_info += "%s,%s - **Empty: No SKUs\n" % (username, password)
        except Exception:
            pass
    info = error_info + empty_info + pass_info
    return info, quantity_mark, quantity_unlimited


def handle_long_str(info):
    """
    The function is used to handle long str. For eg: 111222333444555 -> 111\n222\n333\n444\n555\n
    """
    step = 150   # Max characters that one line can display.
    if len(info) > step:
        return '\n'.join(info[i:i+step] for i in range(0, len(info), step))
    else:
        return info


def log_file():
    # Write log into specified files
    path = './log/'
    if not os.path.exists(path):
        os.mkdir(path)
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)5s|%(filename)18s:%(lineno)3d|%(threadName)s|: %(message)s',
                        datefmt='%d %b %Y %H:%M:%S'
                        )
    nor = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(levelname)5s|%(filename)18s:%(lineno)3d|%(threadName)s|: %(message)s')
    filehandler = logging.handlers.TimedRotatingFileHandler("./log/account_tool.log", "midnight", 1, 0)
    filehandler.suffix = "%Y-%m-%d"
    filehandler.setFormatter(formatter)
    nor.addHandler(filehandler)


def log_console():
    # print log on the console
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)5s|%(filename)18s:%(lineno)3d|%(threadName)s|: %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def search_arch_or_engproductid(attribute, input_datas):
    """
    The function is used to compose str that used in sql sentence of search Eng Product Id(s) or arch.
    Handle like this: (69,180,271) or (x86,x86_64,ppc64)
    :return: str
    """
    search_str = ""
    for input_data in input_datas.split(","):
        input_data = input_data.strip()
        if input_data != "":
            search_str_tmp = "(fn.Lower(SkuEntry.{0}) % '{1}%' |" \
                             "fn.Lower(SkuEntry.{0}) % '{1},%' |" \
                             "fn.Lower(SkuEntry.{0}) % '%,{1},%' |" \
                             "fn.Lower(SkuEntry.{0}) % '%,{1}') &".format(attribute, input_data)
        else:
            search_str_tmp = "(fn.Lower(SkuEntry.id) % '%') &"
        search_str += search_str_tmp
    contain_search_str = str(search_str + "&").replace("&&", "")
    not_contain_search_str = "~({0})".format(contain_search_str)
    return contain_search_str, not_contain_search_str


def advanced_search_str(attribute_select, attribute, attribute_text):
    """
    This function is used to compose the sql sentence for advanced search.
    :param attribute_select: search method, such as contains, equals and so on.
    :param attribute: attribute name, such as arch, multiplier and so on.
    :param attribute_text: input text value, such as 25, x86_64 and so on.
    :return:
    """
    search_attribute_text = ""
    if attribute == "--Select Attribute--":
        search_attribute_text = '(fn.Lower(SkuEntry.id) % "%")'.format(attribute)
    else:
        if attribute_select == "contains":
            if attribute == "arch" or attribute == "eng_product_ids":
                search_attribute_text = search_arch_or_engproductid(attribute, attribute_text.lower())[0]
            else:
                search_attribute_text = '(fn.Lower(SkuEntry.{0}) % "%{1}%")'.format(attribute, attribute_text.lower())
        elif attribute_select == "does not contain":
            if attribute == "arch" or attribute == "eng_product_ids":
                search_attribute_text = search_arch_or_engproductid(attribute, attribute_text.lower())[1]
            else:
                search_attribute_text = '~(fn.Lower(SkuEntry.{0}) % "%{1}%")'.format(attribute, attribute_text.lower())
        elif attribute_select == "equals":
            search_attribute_text = '(fn.Lower(SkuEntry.{0}) == "{1}")'.format(attribute, attribute_text.lower())
        elif attribute_select == "does not equal":
            search_attribute_text = '~(fn.Lower(SkuEntry.{0}) == "{1}")'.format(attribute, attribute_text.lower())
        elif attribute_select == "greater than":
            search_attribute_text = '((fn.Lower(SkuEntry.{0}) > {1}) | (fn.Lower(SkuEntry.{0}) == "-2"))'.format(attribute, attribute_text.lower())
        elif attribute_select == "less than":
            search_attribute_text = '~((fn.Lower(SkuEntry.{0}) > {1}) | (fn.Lower(SkuEntry.{0}) == "-2"))'.format(attribute, attribute_text.lower())
        elif attribute_select == "is empty or null":
            search_attribute_text = '((fn.Lower(SkuEntry.{0}) == "-1") | (fn.Lower(SkuEntry.{0}) == "n/a"))'.format(attribute)
        elif attribute_select == "is not empty or null":
            search_attribute_text = '~((fn.Lower(SkuEntry.{0}) == "-1") | (fn.Lower(SkuEntry.{0}) == "n/a"))'.format(attribute)
        elif attribute_select == "is true":
            search_attribute_text = '(fn.Lower(SkuEntry.{0}) == "1")'.format(attribute)
        elif attribute_select == "is not true":
            search_attribute_text = '~(fn.Lower(SkuEntry.{0}) == "1")'.format(attribute)
    return search_attribute_text


def advanced_search_default_choice(attribute1, choice1, attribute1_text, attribute2, choice2, attribute2_text,
                                   attribute3, choice3, attribute3_text, attribute4, choice4, attribute4_text):
    # Handle the default attribute choice.
    display_str = ""
    attribute_list = []
    attributes = [[attribute1, choice1, attribute1_text], [attribute2, choice2, attribute2_text],
                  [attribute3, choice3, attribute3_text], [attribute4, choice4, attribute4_text]]
    for attribute in attributes:
        if attribute[0] == "--Select Attribute--":
            display_str_tmp = ""
        else:
            display_str_tmp = "{0} - {1}: {2};".format(attribute[0], attribute[1], attribute[2])
        display_str += display_str_tmp
        attribute_list.append(attribute[0])
    return attribute_list, display_str


class XMLWriter(Document):
    def __init__(self):
        Document.__init__(self)

    def xml_generator(self, data):
        self.data = data
        # Set tag to "content"
        tag = self.createElement("content")
        self.appendChild(tag)

        # For every sku.
        for i in self.data:
            sku = self.createElement(i["SKU"])
            tag.appendChild(sku)
            # For every attribute in sku.
            for j in i.keys():
                attribute = self.createElement("attribute")
                sku.appendChild(attribute)
                name = self.createElement("name")
                attribute.appendChild(name)
                name_text = self.createTextNode(j)
                name.appendChild(name_text)
                # value
                value = self.createElement("value")
                attribute.appendChild(value)
                value_text = self.createTextNode(str(i[j]))
                value.appendChild(value_text)

        return self.toprettyxml(indent="    ")


class FileFormatConvert():
    def __init__(self, content):
        self.content = content

    def __get_header(self):
        return self.content[0].keys()

    def csv_format(self):
        # The first line of csv file.
        if len(self.content) == 0:
            return ",,,,"
        else:
            csv_str = str_header = ""
            for i in self.__get_header():
                str_header += "{0}{1}".format(i, ",")

            # Other lines.
            for i in self.content:
                s = ""
                for j in self.__get_header():
                    if (type(i[j]) is str or type(i[j]) is unicode) and ("," in i[j]):
                        z = '"{0}"'.format(i[j])
                        s += "{0}{1}".format(z, ",")
                    else:
                        s += "{0}{1}".format(i[j], ",")
                csv_str += "{0}\n".format(s)
            csv_str = "{0}\n{1}".format(str_header, csv_str)
            return csv_str

    def json_format(self):
        return json.dumps(self.content, indent=4).replace("[", "{").replace("]", "}")

    def xml_format(self):
        return XMLWriter().xml_generator(self.content)

    def save(self, file_format, file_path, file_name):
        content_str = name = ""
        if file_format == "csv":
            content_str = self.csv_format()
            name = "{0}.{1}".format(file_name, "csv")
        elif file_format == "json":
            content_str = self.json_format()
            name = "{0}.{1}".format(file_name, "json")
        elif file_format == "xml":
            name = "{0}.{1}".format(file_name, "xml")
        # Save the str into the file.
        name = file_path + name
        with open(name, "r") as f:
            f.write(content_str)

if __name__ == "__main__":
    username = "test_ftan_2"
    password = "redhat"
    first_name = "Default"
    last_name = "User"
    skus = "RH0103708"
    hock_sku("ftan_test_2", "RH0103708", 100)



