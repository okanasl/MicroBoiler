export const environment = {
  production: true,
  //& region (authorization)
  authConfig : {
    stsServer: '{{auth:stsServer}}',
    redirect_url: '{{auth:clientUrl}}/login-callback.html',
    client_id: '{{auth:client_id}}',
    response_type: 'id_token token',
    scope: '{{auth:scope}}',
    post_logout_redirect_uri: '{{auth:clientUrl}}',
    start_checksession: true,
    silent_renew: true,
    silent_renew_url: '{{auth:clientUrl}}/silent-renew.html',
    startup_route: '/',
    forbidden_route: '/',
    unauthorized_route: '/',
    log_console_warning_active: true,
    log_console_debug_active: false,
    max_id_token_iat_offset_allowed_in_seconds: '10',
  }
  //& end (authorization)
};
