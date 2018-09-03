// The file contents for the current environment will overwrite these during build.
// The build system defaults to the dev environment which uses `environment.ts`, but if you do
// `ng build --env=prod` then `environment.prod.ts` will be used instead.
// The list of which env maps to which file can be found in `.angular-cli.json`.

export const environment = {
  production: false,
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
};
