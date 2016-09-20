__author__ = "ftan"

# host server
port = 80
hostname = "account-manager-stage.app.eng.rdu2.redhat.com"
host = "http://%s:%s/index.html" % (hostname, port)


# REST API
REST_USER = "http://servicejava.edge.stage.ext.phx2.redhat.com/svcrest/user/v3"
REST_REGNUM = "http://servicejava.edge.stage.ext.phx2.redhat.com/svcrest/regnum/v5"
REST_ACTIVATION = "http://servicejava.edge.stage.ext.phx2.redhat.com/svcrest/activation/v2"
REST_TERMS = "http://servicejava.edge.stage.ext.phx2.redhat.com/svcrest/terms"
REST_SUBSCRIPTIONS = "http://servicejava.edge.stage.ext.phx2.redhat.com/svcrest/subscription/v5"
REST_CANDLEPIN = "http://candlepin.dist.stage.ext.phx2.redhat.com/candlepin"

# Candlepin Server
stage_candlepin_server = "subscription.rhn.stage.redhat.com"

# super user for Stage Candlepin
user_candlepin = "candlepin_admin"
password_candlepin = "candlepin_admin"


# Error Number:
# 1 - account doesn't exist
# 2 - incorrect password
# 3 - refresh failure
# 4 - account already exists
# 5 - no response from server - Connection reset by peer
