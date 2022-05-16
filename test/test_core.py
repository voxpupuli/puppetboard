from textwrap import dedent

import pytest

from puppetboard.core import get_friendly_error


# flake8: noqa
@pytest.mark.parametrize("raw_message,friendly_message", [
    ("Could not retrieve catalog from remote server: Error 500 on SERVER: Server Error: Evaluation "
     "Error: Error while evaluating a Resource Statement, Evaluation Error: Error while evaluating "
     "a Function Call, This envs has Consul ACLs enabled. Please add the app 'statsproxy' to the "
     "'profiles::consul::server::policies' hiera key. (file: "
     "/etc/puppetlabs/code/environments/patch/modules/consul_wrapper/functions/service"
     "/get_acl_token.pp, line: 22, column: 7) (file: "
     "/etc/puppetlabs/code/environments/patch/modules/roles/manifests/tomcat/stats.pp, line: 39) "
     "on node foo.bar.com", """
     Error while evaluating a Resource Statement:

      Error while evaluating a Function Call:

      This envs has Consul ACLs enabled. Please add the app 'statsproxy' to the 'profiles::consul::server::policies' hiera key. (file: …/consul_wrapper/functions/service/get_acl_token.pp, line: 22, column: 7)

     …in …/roles/manifests/tomcat/stats.pp, line: 39.
     """),

    ("Could not retrieve catalog from remote server: Error 500 on SERVER: Server Error: "
     "Evaluation Error: Error while evaluating a Method call, Could not find class "
     "::profiles::snapshot_restore for foo.bar.com (file: "
     "/etc/puppetlabs/code/environments/qa/manifests/site.pp, line: 31, column: 7) on node "
     "foo.bar.com", """
     Error while evaluating a Method call:

      Could not find class ::profiles::snapshot_restore
    
     …in …/qa/manifests/site.pp, line: 31, column: 7. 
     """),
])
def test_get_friendly_error(raw_message, friendly_message):
    raw_message = dedent(raw_message)
    friendly_message = dedent(friendly_message).strip()
    assert get_friendly_error("Puppet", raw_message, "foo.bar.com") == friendly_message
