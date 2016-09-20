__author__ = "ftan"

import csv
import datetime

from flask import Flask, render_template, request
from flask.ext.script import Manager
from flask.ext.bootstrap import Bootstrap
from flask.ext.moment import Moment
from werkzeug import secure_filename
from peewee import fn

from forms import *
from utils import *


app = Flask(__name__)

# Don't use CSRF
# app.config['SECRET_KEY'] = 'hard to guess string'

manager = Manager(app)
bootstrap = Bootstrap(app)
moment = Moment(app)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/index.html', methods=['GET', 'POST'])
def index():
    create_form = CreateAccount(csrf_enabled=False)
    entitle_form = EntitleAccount(csrf_enabled=False)
    csv_form = CreateFormCSV(csrf_enabled=False)
    search_ph_product_line_form = SearchByPHProductLine(csrf_enabled=False)
    search_ph_product_name_form = SearchByPHProductName(csrf_enabled=False)
    search_sku_name_form = SearchBySKUName(csrf_enabled=False)
    search_attribute_form = SearchBySkuAttribute(csrf_enabled=False)
    refresh_form = RefreshAccount(csrf_enabled=False)
    view_form = ViewAccount(csrf_enabled=False)
    export_form = ExportAccount(csrf_enabled=False)
    delete_form = DeletePool(csrf_enabled=False)

    #######################
    # Create Accounts Tab #
    #######################
    if create_form.validate_on_submit():
        # Account create process
        # Check if account exists
        # Create account if not exist, create it and return orgID - find_or_create_user
        # Hock SKU, and return regNum - hock_sku
        # Activate regNum - activate_regnum
        # Accept Terms - accept_terms
        # Refresh - refresh_account

        logging.info("====== Create an account ======")

        # Get input value from web page
        username = str(create_form.username_create.data).strip()
        password = str(create_form.password_create.data).strip()
        first_name = str(create_form.first_name_create.data).strip()
        last_name = str(create_form.last_name_create.data).strip()
        skus = str(create_form.sku_create.data).strip()
        quantity = create_form.quantity_create.data
        duration = str(create_form.duration_create.data).strip()
        accept = create_form.accept_create.data

        # Set Start Date according to Duration
        today_date = datetime.date(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day)
        if duration == "":
            start_date = str(today_date)
        else:
            start_date = str(today_date - datetime.timedelta(365 - int(duration)))
        logging.info("Start Date: {0}".format(start_date))

        sku_pass = ""
        sku_fail = ""
        sku_con_fail = ""
        sku_inactive = ""
        sku_not_exist = ""
        if first_name == "":
            first_name = "Default"
        if last_name == "":
            last_name = "User"

        logging.info("*Username: %s" % username)
        logging.info("*Password: %s" % password)
        logging.info("First Name: %s" % first_name)
        logging.info("Last Name: %s" % last_name)
        logging.info("Subscription SKUs: %s" % skus)
        logging.info("Quantity: %s" % quantity)

        result = 0

        # Check if user exists - only new account can be created in this page
        # If yes, return
        # If no, continue
        check_result = check_user(username)
        if check_result == 5 or check_result == 0:
            if check_result == 5:
                # 5 - no response from server - Connection reset by peer
                result = 5
            else:
                # 4 - account already exists
                result = 4
            return render_template(
                        'create.html',
                        username=username,
                        host=host,
                        result=result
                        )

        # Get orgID of account
        org_id = find_or_create_user(username, password, first_name, last_name)
        logging.info("Org Id for user %s : %s" % (username, org_id))

        # If fail to get org_id of account, return
        if org_id == None:
            result = 5
            return render_template(
                        'create.html',
                        username=username,
                        host=host,
                        result=result
                        )

        # If quantity <= 0, and the sku into error list sku_fail
        if int(quantity) <= 0:
            sku_fail = str_append(sku_fail, skus.upper())
        # Continue when quantity > 0
        # Continue when skus and quantity are both not empty
        elif skus != "" and quantity != "":
            for sku in [i.strip() for i in skus.split(',')]:
                try:
                    # Check if sku exists in database
                    # If yes, try to add this sku into account
                    # If no, add this sku into error list sku_not_exist
                    if check_sku(sku) == 1:
                        sku_not_exist = str_append(sku_not_exist, sku.upper())
                        continue

                    # Get regNum
                    regnum = hock_sku(username, sku, quantity, start_date)

                    # If regnum is None, add this sku into error list sku_con_fail
                    if regnum == None:
                        sku_con_fail = str_append(sku_con_fail, sku.upper())
                        logging.error("Failed to add SKU %s into Account %s" % (sku, username))
                        continue

                    # Activate regNum
                    if activate_regnum(username, org_id, regnum, start_date):
                        sku_inactive = str_append(sku_inactive, sku.upper())
                        logging.error("Failed to add SKU %s into Account %s" % (sku, username))
                        continue

                    # Append sku added successfully into list sku_pass
                    sku_pass = str_append(sku_pass, sku.upper())
                except Exception:
                    sku_fail = str_append(sku_fail, sku.upper())
                    logging.error("Failed to add SKU %s into Account %s" % (sku, username))

        # Accept Terms
        accept_result = 0
        if accept == True:
            i = 0
            # To resolve 'Failed to accept term error by once', add a loop(max is 5) here
            while check_accept_terms(username, password):
                logging.info("Accept Terms")
                accept_result = accept_terms(org_id, username, password)
                logging.info("Refresh")
                i += 1
                if i == 5:
                    break
            # Refresh Account
            result = refresh_account(username)

        logging.info("====== End: Create an account ======")
        return render_template(
                        'create.html',
                        username=username,
                        host=host,
                        result=result,
                        accept_result=accept_result,
                        skus=skus,
                        sku_pass=sku_pass,
                        sku_fail=sku_fail,
                        sku_con_fail=sku_con_fail,
                        sku_inactive=sku_inactive,
                        sku_not_exist=sku_not_exist
                        )

    ##############################
    # Add Subscription Pools Tab #
    ##############################
    if entitle_form.validate_on_submit():
        # Subscription add process
        # Check if password is correct
        # Get orgID of existing account, return orgID - find_or_create_user
        # Check if sku exists in database, if yes, add it, if no, add it to error list
        # Hock SKU, and return regNum - hock_sku
        # Activate regNum - activate_regnum
        # Accept Terms - accept_terms
        # Refresh - refresh_account

        logging.info("====== Add Subscriptions Pool ======")

        # Get input value from web page
        username = str(entitle_form.username_entitle.data).strip()
        password = str(entitle_form.password_entitle.data).strip()
        skus = str(entitle_form.sku_entitle.data).strip()
        quantity = entitle_form.quantity_entitle.data
        duration = str(entitle_form.duration_entitle.data).strip()
        accept = entitle_form.accept_entitle.data

        # Set Start Date according to Duration
        today_date = datetime.date(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day)
        if duration == "":
            start_date = str(today_date)
        else:
            start_date = str(today_date - datetime.timedelta(365 - int(duration)))
        logging.info("Start Date: {0}".format(start_date))

        result = 0
        sku_pass = ""
        sku_fail = ""
        sku_con_fail = ""
        sku_inactive = ""
        sku_not_exist = ""

        logging.info("*Username: %s" % username)
        logging.info("*Password: %s" % password)
        logging.info("Subscription SKUs: %s" % skus)
        logging.info("Quantity: %s" % quantity)

        # Check if password is correct
        # If yes, continue
        # If no, return
        if check_password(username, password):
            result = 2
            return render_template(
                            'entitle.html',
                            username=username,
                            sku=skus,
                            result=result
                            )

        # Get orgID of account
        org_id = find_or_create_user(username, password)
        logging.info("Org Id for user %s : %s" % (username, org_id))

        # If fail to get orgId of account, return
        if org_id == None:
            result = 5
            return render_template(
                            'entitle.html',
                            username=username,
                            sku=skus,
                            result=result
                            )

        if skus != "" and quantity != "":
            for sku in [i.strip() for i in skus.split(',')]:
                try:
                    # Check if sku exists in database
                    # If yes, try to add this sku into account
                    # If no, add it into error list - sku_not_exist
                    if check_sku(sku) == 1:
                        sku_not_exist = str_append(sku_not_exist, sku.upper())
                        continue

                    # Get reNum
                    regnum = hock_sku(username, sku, quantity, start_date)

                    # If regnum is None, add this sku into error list sku_con_fail
                    if regnum == None:
                        sku_con_fail = str_append(sku_con_fail, sku.upper())
                        logging.error("Failed to add SKU %s into Account %s" % (sku, username))
                        continue

                    # Activate regNum
                    if activate_regnum(username, org_id, regnum, start_date):
                        sku_inactive = str_append(sku_inactive, sku.upper())
                        logging.error("Failed to add SKU %s into Account %s" % (sku, username))
                        continue

                    # Append sku added successfully into list sku_pass
                    sku_pass = str_append(sku_pass, sku.upper())
                except Exception:
                    sku_fail = str_append(sku_fail, sku.upper())
                    logging.error("Failed to add SKU %s into Account %s" % (sku, username))

        # Accept Terms
        accept_result = 0
        if accept == True:
            i = 0
            # To resolve 'Failed to accept term error by once', add a loop(max is 5) here
            while check_accept_terms(username, password):
                logging.info("Accept Terms")
                accept_result = accept_terms(org_id, username, password)
                logging.info("Refresh")
                i += 1
                if i == 5:
                    break
            # Refresh Account
            result = refresh_account(username)

        logging.info("====== End: Add Subscriptions Pool ======")
        return render_template(
                            'entitle.html',
                            username=username,
                            sku=skus,
                            sku_pass=sku_pass,
                            sku_fail=sku_fail,
                            sku_con_fail=sku_con_fail,
                            sku_inactive=sku_inactive,
                            sku_not_exist=sku_not_exist,
                            result=result,
                            accept_result=accept_result
                            )

    ################################
    # Create Accounts from CSV Tab #
    ################################
    if csv_form.validate_on_submit():
        logging.info("====== Create Accounts from CSV ======")

        # The uploaded csv file will be saved into directory ./log/csv/
        csv_par_path = './log/'
        csv_path = 'csv/'
        csv_filename = "%s%scsv-%s.csv" % (csv_par_path, csv_path, time.strftime('%Y-%m-%d-%H-%I-%M-%S',time.localtime(time.time())))
        if not os.path.exists(csv_par_path):
            os.mkdir(csv_par_path)
        if not os.path.exists(csv_par_path+csv_path):
            os.mkdir(csv_par_path + csv_path)

        # Get csv file content and save csv file
        file = request.files['file_csv']
        filename = secure_filename(file.filename)
        file.save("{0}".format(csv_filename))
        csv_file = csv.reader(open("{0}".format(csv_filename), 'rb'))

        # Get accept terms value
        accept = csv_form.accept_csv.data

        # Set Start Date
        start_date = str(datetime.date(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day))

        result = 0
        accept_result = 0
        failed_account = ""
        summary_list = []
        failed_refresh = []
        logging.info("CSV File: %s" % filename)
        logging.debug("Content of CSV file %s:" % filename)
        logging.debug(csv_file)

        for line in csv_file:
            logging.info("*** Line: %s" % line)
            # ignore blank line
            if line == []:
                continue

            # Get username and password, if password is not set, set it to "redhat"
            username = line[0].strip()
            password = line[1].strip()
            if password == "":
                password = "redhat"

            summary = {}
            summary["user_info"] = "%s, %s" % (username, password)
            failed_sku = ""
            passed_sku = ""
            failed_account = ""
            length = len(line)

            # Get orgID of account
            org_id = find_or_create_user(username, password)
            logging.info("Org Id for user %s : %s" % (username, org_id))

            # If fail to get org_id of account, return
            if org_id == None:
                result = 5
                failed_account = str_append(failed_account, sku.upper())
            else:
                logging.info("Created - user_info: %s" % summary["user_info"])


            for data in line[2::2]:
                try:
                    # Get sku name, if sku is empty, skip
                    sku = data.strip()
                    if sku == "":
                        continue

                    # Check if sku exists in database
                    # If yes, try to add it into account
                    # If no, add it into error list failed_sku
                    if check_sku(sku) == 1:
                        failed_sku = str_append(failed_sku, sku.upper())
                        continue

                    # Get quantity
                    index = line.index(data) + 1
                    if index < length:
                        quantity = line[index]
                        if int(quantity) <= 0:
                            failed_sku = str_append(failed_sku, sku.upper())
                            continue
                    else:
                        continue

                    # Get regNum
                    regnum = hock_sku(username, sku, quantity, start_date)

                    # If regnum is None, add this sku into error list failed_sku
                    if regnum == None:
                        failed_sku = str_append(failed_sku, sku.upper())
                        logging.error("Failed to add SKU %s into Account %s" % (sku, username))
                        continue

                    # Activate regNum
                    if activate_regnum(username, org_id, regnum):
                        failed_sku = str_append(failed_sku, sku.upper())
                        logging.error("Failed to add SKU %s into Account %s" % (sku, username))
                        continue

                    # Append sku added successfully into list sku_pass
                    passed_sku = str_append(passed_sku, sku.upper())
                except Exception:
                    failed_sku = str_append(failed_sku, sku.upper())
                    logging.error("Failed to add SKU %s into Account %s" % (sku, username))

            # Accept Terms
            if accept == True:
                i = 0
                # To resolve 'Failed to accept term error by once', add a loop(max is 5) here
                while check_accept_terms(username, password):
                    accept_result = accept_terms(org_id, username, password)
                    i += 1
                    if i == 5:
                        break
                # Refresh Account
                result = refresh_account(username)
                if result == 3:
                    failed_refresh.append(username)
            if failed_sku != "":
                summary["fail"] = "Failed to add SKUs: %s" % failed_sku
                logging.info("%s - %s" % (username, summary["fail"]))
            else:
                summary["fail"] = ""
            if passed_sku != "":
                summary["pass"] = "Succeed to add SKUs: %s" % passed_sku
                logging.info("%s - %s" % (username, summary["pass"]))
            else:
                summary["pass"] = ""
            summary_list.append(summary)
        logging.info("====== End: Create Accounts from CSV ======")
        return render_template(
                            'csv.html',
                            file=filename,
                            summary_list=summary_list,
                            failed_refresh=failed_refresh,
                            failed_account=failed_account,
                            result=result,
                            accept_result=accept_result
                            )


    ###########################################################
    ##  Search Subscription SKUs - Search by Product Hierarchy: Product Line  ##
    ###########################################################
    if search_ph_product_line_form.validate_on_submit():
        logging.info("====== Search Subscription SKUs - Search by Product Family ======")
        data = search_ph_product_line_form.data_search_product.data
        logging.info("Product Name to search: %s" % data)
        sku_matrix = []
        sku_failed_matrix = ""
        search_data = "%%%s%%" % data.lower()
        for row in SkuEntry.select().where(fn.Lower(SkuEntry.ph_product_line) % search_data):
            meta = {}
            meta["SKU"] = row.id
            meta['Product Hierarchy: Product Category'] = row.ph_category
            meta['Product Hierarchy: Product Line'] = row.ph_product_line
            meta['Product Hierarchy: Product Name'] = row.ph_product_name
            meta['Product Name'] = row.name
            meta['Virt Limit'] = row.virt_limit
            meta['Socket(s)'] = row.sockets
            meta['VCPU'] = row.vcpu
            meta['Multiplier'] = row.multiplier
            meta['Unlimited Product'] = row.unlimited_product
            meta['Required Consumer Type'] = row.requires_consumer_type
            meta['Product Family'] = row.product_family
            meta['Management Enabled'] = row.management_enabled
            meta['Variant'] = row.variant
            meta['Support Level'] = row.support_level
            meta['Support Type'] = row.support_type
            meta['Enabled Consumer Types'] = row.enabled_consumer_types
            meta['Virt-only'] = row.virt_only
            meta['Cores'] = row.cores
            meta['JON Management'] = row.jon_management
            meta['RAM'] = row.ram
            meta['Instance Based Virt Multiplier'] = row.instance_multiplier
            meta['Cloud Access Enabled'] = row.cloud_access_enabled
            meta['Stacking ID'] = row.stacking_id
            meta['Multi Entitlement'] = row.multi_entitlement
            meta['Host Limited'] = row.host_limited
            meta['Derived SKU'] = row.derived_sku
            meta['Eng Productid(s)'] = row.eng_product_ids
            meta['Arch'] = row.arch
            meta['Username'] = row.username
            sku_matrix.append(meta)
        if data == "":
            data = "ALL Products"
        logging.info("====== End: Search Subscription SKUs - Search by Product Family ======")
        # Convert the result into csv format.
        sku_matrix_csv = FileFormatConvert(sku_matrix).csv_format()
        return render_template(
                        'search.html',
                        data=data,
                        sku_matrix=sku_matrix,
                        sku_failed_matrix=sku_failed_matrix,
                        sku_matrix_csv=sku_matrix_csv
                        )


    ###########################################################
    ##  Search Subscription SKUs - Search by Product Hierarchy: Product Name  ##
    ###########################################################
    if search_ph_product_name_form.validate_on_submit():
        logging.info("====== Search Subscription SKUs - Search by Product Family ======")
        data = search_ph_product_name_form.data_search_product.data
        logging.info("Product Name to search: %s" % data)
        sku_matrix = []
        sku_failed_matrix = ""
        search_data = "%%%s%%" % data.lower()
        for row in SkuEntry.select().where(fn.Lower(SkuEntry.ph_product_name) % search_data):
            meta = {}
            meta["SKU"] = row.id
            meta['Product Hierarchy: Product Category'] = row.ph_category
            meta['Product Hierarchy: Product Line'] = row.ph_product_line
            meta['Product Hierarchy: Product Name'] = row.ph_product_name
            meta['Product Name'] = row.name
            meta['Virt Limit'] = row.virt_limit
            meta['Socket(s)'] = row.sockets
            meta['VCPU'] = row.vcpu
            meta['Multiplier'] = row.multiplier
            meta['Unlimited Product'] = row.unlimited_product
            meta['Required Consumer Type'] = row.requires_consumer_type
            meta['Product Family'] = row.product_family
            meta['Management Enabled'] = row.management_enabled
            meta['Variant'] = row.variant
            meta['Support Level'] = row.support_level
            meta['Support Type'] = row.support_type
            meta['Enabled Consumer Types'] = row.enabled_consumer_types
            meta['Virt-only'] = row.virt_only
            meta['Cores'] = row.cores
            meta['JON Management'] = row.jon_management
            meta['RAM'] = row.ram
            meta['Instance Based Virt Multiplier'] = row.instance_multiplier
            meta['Cloud Access Enabled'] = row.cloud_access_enabled
            meta['Stacking ID'] = row.stacking_id
            meta['Multi Entitlement'] = row.multi_entitlement
            meta['Host Limited'] = row.host_limited
            meta['Derived SKU'] = row.derived_sku
            meta['Eng Productid(s)'] = row.eng_product_ids
            meta['Arch'] = row.arch
            meta['Username'] = row.username
            sku_matrix.append(meta)
        if data == "":
            data = "ALL Products"
        logging.info("====== End: Search Subscription SKUs - Search by Product Family ======")
        # Convert the result into csv format.
        sku_matrix_csv = FileFormatConvert(sku_matrix).csv_format()
        return render_template(
                        'search.html',
                        data=data,
                        sku_matrix=sku_matrix,
                        sku_failed_matrix=sku_failed_matrix,
                        sku_matrix_csv=sku_matrix_csv
                        )

    #####################################################
    ##  Search Subscription SKUs - Search by SKU Name  ##
    #####################################################
    if search_sku_name_form.validate_on_submit():
        logging.info("====== Search Subscription SKUs - Search by SKU Name ======")
        skus = search_sku_name_form.data_search_name.data
        logging.info("SKU Name to search: %s" % skus)
        sku_matrix = []
        sku_failed_matrix = ""
        for sku in set(skus.split(',')):
            success = 1
            for row in SkuEntry.select().where(fn.Lower(SkuEntry.id) == sku.strip().lower()):
                success = 0
                meta = {}
                meta["SKU"] = row.id
                meta['Product Hierarchy: Product Category'] = row.ph_category
                meta['Product Hierarchy: Product Line'] = row.ph_product_line
                meta['Product Hierarchy: Product Name'] = row.ph_product_name
                meta['Product Name'] = row.name
                meta['Virt Limit'] = row.virt_limit
                meta['Socket(s)'] = row.sockets
                meta['VCPU'] = row.vcpu
                meta['Multiplier'] = row.multiplier
                meta['Unlimited Product'] = row.unlimited_product
                meta['Required Consumer Type'] = row.requires_consumer_type
                meta['Product Family'] = row.product_family
                meta['Management Enabled'] = row.management_enabled
                meta['Variant'] = row.variant
                meta['Support Level'] = row.support_level
                meta['Support Type'] = row.support_type
                meta['Enabled Consumer Types'] = row.enabled_consumer_types
                meta['Virt-only'] = row.virt_only
                meta['Cores'] = row.cores
                meta['JON Management'] = row.jon_management
                meta['RAM'] = row.ram
                meta['Instance Based Virt Multiplier'] = row.instance_multiplier
                meta['Cloud Access Enabled'] = row.cloud_access_enabled
                meta['Stacking ID'] = row.stacking_id
                meta['Multi Entitlement'] = row.multi_entitlement
                meta['Host Limited'] = row.host_limited
                meta['Derived SKU'] = row.derived_sku
                meta['Eng Productid(s)'] = row.eng_product_ids
                meta['Arch'] = row.arch
                meta['Username'] = row.username
                sku_matrix.append(meta)
            if success == 1:
                sku_failed_matrix = str_append(sku_failed_matrix, sku)
        if len(sku_failed_matrix) != 0:
            logging.error("Failed to get sku %s" % sku_failed_matrix)
        logging.info("====== End: Search Subscription SKUs - Search by SKU Name ======")
        # Convert the result into csv format.
        sku_matrix_csv = FileFormatConvert(sku_matrix).csv_format()
        if len(sku_matrix) == 0:
            return render_template(
                                'search_failed.html',
                                data=skus,
                                sku_failed_matrix=sku_failed_matrix
                                )
        else:
            return render_template(
                                'search.html',
                                data=skus,
                                sku_matrix=sku_matrix,
                                sku_failed_matrix=sku_failed_matrix,
                                sku_matrix_csv=sku_matrix_csv
                                )

    ###########################################################
    #  Search Subscription SKUs - Search by SKU Attribute     #
    ###########################################################
    if search_attribute_form.validate_on_submit():
        # Total 4 attribute value.
        logging.info("====== Search Subscription SKUs - Search by SKU Attribute ======")
        sku_matrix = []
        sku_failed_matrix = ""

        attribute1 = handle_attribute(search_attribute_form.data_search_attribute1.data)
        attribute1_select = search_attribute_form.data_search_select1.data
        attribute1_text = search_attribute_form.data_search_attribute_text1.data

        attribute2 = handle_attribute(search_attribute_form.data_search_attribute2.data)
        attribute2_select = search_attribute_form.data_search_select2.data
        attribute2_text = search_attribute_form.data_search_attribute_text2.data

        attribute3 = handle_attribute(search_attribute_form.data_search_attribute3.data)
        attribute3_select = search_attribute_form.data_search_select3.data
        attribute3_text = search_attribute_form.data_search_attribute_text3.data

        attribute4 = handle_attribute(search_attribute_form.data_search_attribute4.data)
        attribute4_select = search_attribute_form.data_search_select4.data
        attribute4_text = search_attribute_form.data_search_attribute_text4.data

        # Handle the default choice "--Select Attribute--"
        (attribute_list, search_attribute) = advanced_search_default_choice(attribute1, attribute1_select, attribute1_text,
                                                                            attribute2, attribute2_select, attribute2_text,
                                                                            attribute3, attribute3_select, attribute3_text,
                                                                            attribute4, attribute4_select, attribute4_text)

        # Estimate which search method is attribute$_select used.
        # We support 10 kinds of search method: equal/not equal, contain/not contain, greater than/less than,
        # is empty or null/is not empty or null, is ture/false.
        search_attribute_text1 = advanced_search_str(attribute1_select, attribute_list[0], attribute1_text)
        search_attribute_text2 = advanced_search_str(attribute2_select, attribute_list[1], attribute2_text)
        search_attribute_text3 = advanced_search_str(attribute3_select, attribute_list[2], attribute3_text)
        search_attribute_text4 = advanced_search_str(attribute4_select, attribute_list[3], attribute4_text)

        search_str = 'SkuEntry.select().where({0} & {1} & {2} & {3})'.format(search_attribute_text1,
                                                                             search_attribute_text2,
                                                                             search_attribute_text3,
                                                                             search_attribute_text4)
        success = 1
        for row in eval(search_str):
            success = 0
            meta = {}
            meta["SKU"] = row.id
            meta['Product Hierarchy: Product Category'] = row.ph_category
            meta['Product Hierarchy: Product Line'] = row.ph_product_line
            meta['Product Hierarchy: Product Name'] = row.ph_product_name
            meta['Product Name'] = row.name
            meta['Virt Limit'] = row.virt_limit
            meta['Socket(s)'] = row.sockets
            meta['VCPU'] = row.vcpu
            meta['Multiplier'] = row.multiplier
            meta['Unlimited Product'] = row.unlimited_product
            meta['Required Consumer Type'] = row.requires_consumer_type
            meta['Product Family'] = row.product_family
            meta['Management Enabled'] = row.management_enabled
            meta['Variant'] = row.variant
            meta['Support Level'] = row.support_level
            meta['Support Type'] = row.support_type
            meta['Enabled Consumer Types'] = row.enabled_consumer_types
            meta['Virt-only'] = row.virt_only
            meta['Cores'] = row.cores
            meta['JON Management'] = row.jon_management
            meta['RAM'] = row.ram
            meta['Instance Based Virt Multiplier'] = row.instance_multiplier
            meta['Cloud Access Enabled'] = row.cloud_access_enabled
            meta['Stacking ID'] = row.stacking_id
            meta['Multi Entitlement'] = row.multi_entitlement
            meta['Host Limited'] = row.host_limited
            meta['Derived SKU'] = row.derived_sku
            meta['Eng Productid(s)'] = row.eng_product_ids
            meta['Arch'] = row.arch
            meta['Username'] = row.username
            sku_matrix.append(meta)
        logging.info("====== End: Search Subscription SKUs - Search by SKU Attribute ======")
        # Convert the result into csv format.
        sku_matrix_csv = FileFormatConvert(sku_matrix).csv_format()
        if success == 1:
            return render_template('search_failed.html', sku_failed_matrix=sku_failed_matrix)
        else:
            return render_template('search.html', data=search_attribute, sku_matrix=sku_matrix,
                                   sku_failed_matrix=sku_failed_matrix, sku_matrix_csv=sku_matrix_csv)

    ######################################
    # Manage - Refresh Subscriptions Tab #
    ######################################
    if refresh_form.validate_on_submit():
        logging.info("====== Refresh Subscription Pools ======")
        username = str(refresh_form.username_refresh.data).strip()
        password = str(refresh_form.password_refresh.data).strip()
        logging.info("Accounts to refresh: %s" % username)

        # check if user exists, if yes, return 0, if no, return 1
        check_result = check_user(username)
        if check_result:
            if check_result == 5:
                result = 5
            else:
                result = 1
            return render_template(
                            'refresh.html',
                            username=username,
                            result=result
                            )

        # check if password is correct
        # If yes, return 0
        # If no, return 2
        if check_password(username, password):
            result = 2
            return render_template(
                            'refresh.html',
                            username=username,
                            result=result
                            )

        result = refresh_account(username)
        logging.info("====== End: Refresh Subscription Pools ======")
        return render_template(
                            'refresh.html',
                            username=username,
                            result=result
                            )

    ################################
    # Manage - Export Accounts Tab #
    ################################
    if export_form.validate_on_submit():
        logging.info("====== Export Accounts ======")
        accounts_info = str(export_form.username_export.data).strip()
        logging.info("Accounts to export: %s" % accounts_info)
        account_info_list = accounts_info.split(',')
        info, quantity_mark, quantity_unlimited = account_info(account_info_list)
        logging.info("====== End: Export Account ======")
        return render_template(
                            'export.html',
                            info=info,
                            quantity_mark=quantity_mark,
                            quantity_unlimited=quantity_unlimited,
                            host=host
                            )


    ##############################
    # Manage - View Accounts Tab #
    ##############################
    if view_form.validate_on_submit():
        logging.info("====== View Accounts ======")
        accounts_info = view_form.username_view.data
        logging.info("Accounts to View: %s" % accounts_info)
        account_info_list = accounts_info.split(',')
        info, quantity_mark, quantity_unlimited = account_info(account_info_list)
        #quantity_mark = False
        #quantity_unlimited = 100
        #info = "stage_soliu_test,redhat,RH00545,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,10,RH00546,1,RH00546,10,RH00546,10,RH00546,10,MCT2844,100,MCT2888,10,"
        print "+"*20
        print info
        logging.info("====== End: View Accounts ======")
        return render_template(
                            'view.html',
                            info=info,
                            quantity_mark=quantity_mark,
                            quantity_unlimited=quantity_unlimited,
                            host=host
                            )

    return render_template(
                        'index.html',
                        create_form=create_form,
                        entitle_form=entitle_form,
                        refresh_form=refresh_form,
                        delete_form=delete_form,
                        view_form=view_form,
                        search_ph_product_line_form=search_ph_product_line_form,
                        search_ph_product_name_form=search_ph_product_name_form,
                        search_sku_name_form=search_sku_name_form,
                        search_attribute_form=search_attribute_form,
                        csv_form=csv_form,
                        export_form=export_form
                        )


if __name__ == '__main__':
    log_file()
    logging.info("====== Start/Reload Account Tool APP ======")
    #manager.run()
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)




