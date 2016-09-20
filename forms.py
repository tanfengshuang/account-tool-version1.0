__author__ = "ftan"

from flask.ext.wtf import Form
from wtforms import StringField, SubmitField, IntegerField, BooleanField, FileField, SelectField
from wtforms.validators import DataRequired, Length

from choices import *
from environments import host


class CreateAccount(Form):
    username_create = StringField(
                        label="*Username: ",
                        description="Please fill in your username, aka login id.",
                        validators=[DataRequired()]
                        )
    password_create = StringField(
                        label="*Password: ",
                        description="Please fill in the password.",
                        validators=[DataRequired(), Length(min=1, max=25)]
                        )
    first_name_create = StringField(
                        label="First Name: ",
                        description="Please fill in your First Name. (Optional)"
                        )
    last_name_create = StringField(
                        label="Last Name: ",
                        description="Please fill in your Last Name. (Optional)"
                        )
    sku_create = StringField(
                        label="Subscription SKUs: ",
                        description="Please fill in the Subscription SKUs which you can get from \
                            <a href=%s#search>Search Subscription SKUs</a> tab. You can input 1 or more \
                            Subscriptions separated by comma. (Optional - can be added after account creation \
                            on the <a href=%s#entitle>Entitle the account</a> tab)" % (host, host)
                        )
    quantity_create = IntegerField(
                        label="Quantity: ",
                        default=0,
                        description="Please fill in the quantity(>0) which is effective to above all Subscriptions, \
                            such as 10. (Optional - can be added after account creation on the <a href=%s#entitle>\
                            Entitle the account</a> tab)" % host
                        )
    duration_create = StringField(
                        label="Subscription Expires:",
                        description="Subscription expires N days from now. (Optional - will be set as 1 year if leave it null.)"
                        )
    accept_create = BooleanField(
                        label="Accept Terms and Conditions",
                        default=True
                        )
    submit_create = SubmitField("Create")


class EntitleAccount(Form):
    sku_entitle = StringField(
                        label="*Subscription SKUs: ",
                        description="Please fill in the Subscription SKUs which you can get from \
                            <a href=%s#search>Search Subscription SKUs</a> tab. You can input 1 or more \
                            subscriptions separated by comma." % host,
                        validators=[DataRequired()]
                        )
    quantity_entitle = IntegerField(
                        label="*Quantity: ",
                        description="Please fill in the quantity(>0) which is effective to above all Subscriptions, such as 10."
                        )
    username_entitle = StringField(
                        label="*Username: ",
                        description="Please fill in your username.",
                        validators=[DataRequired()]
                        )
    password_entitle = StringField(
                        label="*Password: ",
                        description="Please fill in the password.",
                        validators=[DataRequired(), Length(min=1, max=25)]
                        )
    duration_entitle = StringField(
                        label="Subscription Expires:",
                        description="Subscription expires N days from now. (Optional - will be set as 1 year if leave it null.)"
                        )
    accept_entitle = BooleanField(
                        label="Accept Terms and Conditions",
                        default=True
                        )
    submit_entitle = SubmitField("Entitle")


class CreateFormCSV(Form):
    file_csv = FileField(
                        label="CSV File: ",
                        description="<p>Format: username,password,SKU(1),Qty(1),SKU(2),Qty(2)</p>\
                                    <p>Example: stage_test_1,redhat,MCT0995,100,MCT0996,100</p>",
                        #validators=[FileRequired(), FileAllowed(['csv'], 'CSV files only!')]
                        validators=[DataRequired()]
                        )
    accept_csv = BooleanField(
                        label="Accept Terms and Conditions",
                        default=True
                        )
    submit_csv = SubmitField("Create")


class SearchByPHProductName(Form):
    # Can use QuerySelectField later to refresh data from database automatically
    # wtforms.ext.sqlalchemy.fields.QuerySelectField
    # http://wtforms.simplecodes.com/docs/0.6.2/ext.html#module-wtforms.ext.sqlalchemy
    data_search_product = SelectField(
                        "*PH: Product Name: ",
                        choices=ph_product_name_choices
                        )
    submit_search_product = SubmitField("Search")


class SearchByPHProductLine(Form):
    # Can use QuerySelectField later to refresh data from database automatically
    # wtforms.ext.sqlalchemy.fields.QuerySelectField
    # http://wtforms.simplecodes.com/docs/0.6.2/ext.html#module-wtforms.ext.sqlalchemy
    data_search_product = SelectField(
                        "*PH: Product Line: ",
                        choices=ph_product_line_choices
                        )
    submit_search_product = SubmitField("Search")


class SearchBySKUName(Form):
    data_search_name = StringField(
                        label="*SKU: ",
                        description="Please fill in the SKU(s) you want to search, such as RH0103708 or RH0103708,MCT1067.",
                        validators=[DataRequired()]
                        )
    submit_search_name = SubmitField("Search")


class SearchBySkuAttribute(Form):
    data_search_attribute1 = SelectField(label="*SKU Attribute 1:", choices=attribute_choices)
    data_search_select1 = SelectField(label="", choices=select_choices)
    data_search_attribute_text1 = StringField(label="")

    data_search_attribute2 = SelectField(label="SKU Attribute 2:", choices=attribute_choices)
    data_search_select2 = SelectField(label="", choices=select_choices)
    data_search_attribute_text2 = StringField(label="")

    data_search_attribute3 = SelectField(label="SKU Attribute 3:", choices=attribute_choices)
    data_search_select3 = SelectField(label="", choices=select_choices)
    data_search_attribute_text3 = StringField(label="")

    data_search_attribute4 = SelectField(label="SKU Attribute 4:", choices=attribute_choices)
    data_search_select4 = SelectField(label="", choices=select_choices)
    data_search_attribute_text4 = StringField(label="")

    submit_search_attribute = SubmitField("Search")


class RefreshAccount(Form):
    username_refresh = StringField(
                        label="*Username: ",
                        #description="Please fill in the username.",
                        validators=[DataRequired()]
                        )
    password_refresh = StringField(
                        label="*Password: ",
                        #description="Please fill in the password.",
                        validators=[DataRequired()]
                        )
    submit_refresh = SubmitField("Refresh")


class ViewAccount(Form):
    username_view = StringField(
                        label="*Account Info: ",
                        description="Please fill in the username and password of your account, \
                            such as username1,password1,username2,password2,...",
                        validators=[DataRequired()]
                        )
    submit_view = SubmitField("View")

class ExportAccount(Form):
    username_export = StringField(
                        label="*Account Info: ",
                        description="Please fill in the username and password of your account, \
                            such as username1,password1,username2,password2,...",
                        validators=[DataRequired()]
                        )
    submit_export = SubmitField("Export")

class DeletePool(Form):
    pool_delete = StringField(
                        label="*Pool: ",
                        description="Please fill in the pool you want to delete here.",
                        validators=[DataRequired()]
                        )
    submit_delete = SubmitField("Delete")

