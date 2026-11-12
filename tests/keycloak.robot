*** Settings ***
Library    SSHLibrary

*** Variables ***
${ADMIN_USER}    admin
${ADMIN_PASSWORD}    Nethesis,1234
${module_id}    ${EMPTY}
${HOST}    keycloak.example.org

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

*** Test Cases ***
Check if keycloak is installed correctly
    ${output}  ${rc} =    Execute Command    add-module ${IMAGE_URL} 1
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
    &{config} =    Evaluate    json.loads($output)['output']    json
    Should Be Equal    ${config.host}    ${HOST}

Check if keycloak works as expected
    # The first start builds the Keycloak runtime configuration and
    # initializes the database: allow enough time
    Wait Until Keyword Succeeds    300s    5s    Keycloak answers through Traefik
    Wait Until Keyword Succeeds    60s    3s    Admin console is served through Traefik

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

Check if keycloak is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
