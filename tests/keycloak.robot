*** Settings ***
Library    SSHLibrary
Suite Teardown    Remove fixtures

*** Variables ***
${ADMIN_USER}    admin
${ADMIN_PASSWORD}    Nethesis,1234
${module_id}    ${EMPTY}
${HOST}    keycloak.example.org
${SCENARIO}    install
${RELEASE_IMAGE}    ghcr.io/geniusdynamics/keycloak:1.0.0
${LDAP_IMAGE}    ghcr.io/nethserver/openldap:2.8.1
${LDAP_DOMAIN}    keycloak-ci.test
${LDAP_USER}    oidctest
${LDAP_PASSWORD}    KeycloakLDAP-Test-2026
${directory_id}    ${EMPTY}
${SAMPLE_APP}    keycloaksample1

*** Keywords ***
Login to cluster-admin
    New Page    https://${NODE_ADDR}/cluster-admin/
    Fill Text    text="Username"    ${ADMIN_USER}
    Click    button >> text="Continue"
    Fill Text    text="Password"    ${ADMIN_PASSWORD}
    Click    button >> text="Log in"
    Wait For Elements State    css=#main-content    visible    timeout=10s

Keycloak answers through Traefik
    ${rc} =    Execute Command
    ...    curl -k -f -L --resolve ${HOST}:443:127.0.0.1 --resolve ${HOST}:80:127.0.0.1 http://${HOST}/realms/master/.well-known/openid-configuration
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Admin console is served through Traefik
    ${rc} =    Execute Command
    ...    curl -k -f -L --resolve ${HOST}:443:127.0.0.1 --resolve ${HOST}:80:127.0.0.1 http://${HOST}/admin/master/console/
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Run successfully
    [Arguments]    ${command}
    ${stdout}    ${stderr}    ${rc} =    Execute Command    ${command}    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0    ${stdout} ${stderr}
    RETURN    ${stdout}

Remove fixtures
    Execute Command    redis-cli --no-auth-warning hdel cluster/module_domains ${SAMPLE_APP}
    Execute Command    rm -f /root/keycloak-sso.py /root/keycloak-sso-app.json /root/keycloak-sso-app-repeat.json
    IF    '${module_id}' != ''
        Run successfully    remove-module --no-preserve ${module_id}
    END
    IF    '${directory_id}' != ''
        Run successfully    remove-module --no-preserve ${directory_id}
    END

*** Test Cases ***
Check if keycloak is installed correctly
    ${image} =    Set Variable If    '${SCENARIO}' == 'update'    ${RELEASE_IMAGE}    ${IMAGE_URL}
    ${output}  ${rc} =    Execute Command    add-module ${image} 1
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${module_id}    ${output.module_id}

Check if keycloak can be configured
    ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"host":"${HOST}","http2https":true,"lets_encrypt":false}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if the configuration is returned
    ${output}  ${rc} =    Execute Command    api-cli run module/${module_id}/get-configuration
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{config} =    Evaluate    json.loads($output)    json
    Should Be Equal    ${config.host}    ${HOST}

Check if keycloak works as expected
    ${rc} =    Execute Command    bash -c 'for i in $(seq 1 60); do curl -k -s -o /dev/null -f --resolve ${HOST}:443:127.0.0.1 https://${HOST}/ && exit 0; sleep 5; done; exit 1'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Upgrade from 1.0.0 and retain the existing installation
    Skip If    '${SCENARIO}' != 'update'    Fresh install scenario
    Wait Until Keyword Succeeds    180s    5s    Keycloak answers through Traefik
    Run successfully    api-cli run update-module --data '{"force":true,"module_url":"${IMAGE_URL}","instances":["${module_id}"]}'
    Wait Until Keyword Succeeds    180s    5s    Keycloak answers through Traefik
    Admin console is served through Traefik

Register an NS8 client and sign in against the user domain
    ${published} =    Run successfully    redis-cli --no-auth-warning exists module/${module_id}/srv/http/oidc
    Should Be Equal As Integers    ${published}    0
    ${grant} =    Run successfully    redis-cli --no-auth-warning sismember module/${module_id}/roles/clientadm register-client
    Should Be Equal As Integers    ${grant}    1
    ${output} =    Run successfully    add-module ${LDAP_IMAGE} 1
    ${id} =    Evaluate    ast.literal_eval($output)['module_id']    modules=ast
    Set Suite Variable    ${directory_id}    ${id}
    Run successfully    api-cli run module/${directory_id}/configure-module --data '{"provision":"new-domain","domain":"${LDAP_DOMAIN}","admuser":"admin","admpass":"${LDAP_PASSWORD}"}'
    Run successfully    api-cli run module/${directory_id}/add-user --data '{"user":"${LDAP_USER}","display_name":"OIDC Test","password":"${LDAP_PASSWORD}","mail":"${LDAP_USER}@${LDAP_DOMAIN}"}'
    Put File    ${CURDIR}/sso.py    /root/keycloak-sso.py
    Run successfully    api-cli run module/${module_id}/configure-ns8-sso --data '{"enabled":true}'
    ${prefix} =    Run successfully    redis-cli --no-auth-warning hget module/${module_id}/srv/http/oidc issuer_url_prefix
    Should Be Equal    ${prefix}    https://${HOST}/realms/
    ${data} =    Set Variable    {"domain":"${LDAP_DOMAIN}","module_id":"${SAMPLE_APP}","redirect_uris":["https://app.keycloak-ci.test/callback"]}
    ${response}    ${rc} =    Execute Command    api-cli run module/${module_id}/register-client --data '${data}'    return_rc=True
    Should Be Equal As Integers    ${rc}    2
    Should Contain    ${response}    domain_not_bound_to_module
    Run successfully    redis-cli --no-auth-warning hset cluster/module_domains ${SAMPLE_APP} ${LDAP_DOMAIN}
    Run successfully    umask 077 && api-cli run module/${module_id}/register-client --data '${data}' > /root/keycloak-sso-app.json
    Run successfully    umask 077 && api-cli run module/${module_id}/register-client --data '${data}' > /root/keycloak-sso-app-repeat.json && cmp /root/keycloak-sso-app.json /root/keycloak-sso-app-repeat.json
    Wait Until Keyword Succeeds    60s    5s    Run successfully    python3 /root/keycloak-sso.py ${HOST} ${LDAP_DOMAIN} ${LDAP_USER} ${LDAP_PASSWORD} < /root/keycloak-sso-app.json
    Run successfully    api-cli run module/${module_id}/configure-ns8-sso --data '{"enabled":false}'
    ${published} =    Run successfully    redis-cli --no-auth-warning exists module/${module_id}/srv/http/oidc
    Should Be Equal As Integers    ${published}    0

Take screenshots
    [Tags]    ui
    Import Library    Browser
    New Browser    chromium    headless=True
    New Context    ignoreHTTPSErrors=True
    Login to cluster-admin
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}
    Wait For Elements State    iframe >>> h2 >> text="Status"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/1._Status.png
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}?page=settings
    Wait For Elements State    iframe >>> h2 >> text="Settings"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/2._Settings.png
    Close Browser
