import { NgModule, ErrorHandler } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { IonicApp, IonicModule, IonicErrorHandler } from 'ionic-angular';
import { MyApp } from './app.component';

import { AboutPage } from '../pages/about/about';
import { ContactPage } from '../pages/contact/contact';
import { HomePage } from '../pages/home/home';
import { TabsPage } from '../pages/tabs/tabs';

import { StatusBar } from '@ionic-native/status-bar';
import { SplashScreen } from '@ionic-native/splash-screen';
import { LoginPage } from '../pages/login/login';
import { HttpClientModule } from '@angular/common/http';
import { AuthModule, OidcSecurityService, OpenIDImplicitFlowConfiguration, AuthWellKnownEndpoints } from "angular-auth-oidc-client";
import { authConfig as config} from '../pages/login/authconfig';
import { RouterModule } from '@angular/router';
import { InAppBrowser } from '@ionic-native/in-app-browser';

@NgModule({
  declarations: [
    MyApp,
    AboutPage,
    ContactPage,
    HomePage,
    TabsPage,
    LoginPage
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    RouterModule.forRoot([],{useHash:false}),
    AuthModule.forRoot(),
    IonicModule.forRoot(MyApp)
  ],
  bootstrap: [IonicApp],
  entryComponents: [
    MyApp,
    AboutPage,
    ContactPage,
    HomePage,
    TabsPage,
    LoginPage
  ],
  providers: [
    StatusBar,
    SplashScreen,
    InAppBrowser,
    {provide: ErrorHandler, useClass: IonicErrorHandler}
  ]
})
export class AppModule {
  constructor(
    private oidcSecurityService: OidcSecurityService
) {
        const openIDImplicitFlowConfiguration = new OpenIDImplicitFlowConfiguration();
        openIDImplicitFlowConfiguration.stsServer = config.stsServer;
        openIDImplicitFlowConfiguration.redirect_url = config.redirect_url;
        openIDImplicitFlowConfiguration.trigger_authorization_result_event = true;
        // The Client MUST validate that the aud (audience) Claim contains its client_id value registered at the Issuer
        // identified by the iss (issuer) Claim as an audience.
        // The ID Token MUST be rejected if the ID Token does not list the Client as a valid audience,
        // or if it contains additional audiences not trusted by the Client.
        openIDImplicitFlowConfiguration.client_id = config.client_id;
        openIDImplicitFlowConfiguration.response_type = config.response_type;
        openIDImplicitFlowConfiguration.scope = config.scope;
        openIDImplicitFlowConfiguration.post_logout_redirect_uri = config.post_logout_redirect_uri;
        openIDImplicitFlowConfiguration.start_checksession = typeof window !== 'undefined' ? config.start_checksession : false;
        openIDImplicitFlowConfiguration.silent_renew = typeof window !== 'undefined' ? config.silent_renew : false;
        openIDImplicitFlowConfiguration.silent_renew_url = config.silent_renew_url;
        openIDImplicitFlowConfiguration.post_login_route = config.startup_route;
        // HTTP 403
        openIDImplicitFlowConfiguration.forbidden_route = config.forbidden_route;
        // HTTP 401
        openIDImplicitFlowConfiguration.unauthorized_route = config.unauthorized_route;
        openIDImplicitFlowConfiguration.log_console_warning_active = config.log_console_warning_active;
        openIDImplicitFlowConfiguration.log_console_debug_active = config.log_console_debug_active;
        // id_token C8: The iat Claim can be used to reject tokens that were issued too far away from the current time,
        // limiting the amount of time that nonces need to be stored to prevent attacks.The acceptable range is Client specific.
        openIDImplicitFlowConfiguration.max_id_token_iat_offset_allowed_in_seconds = 20;
        openIDImplicitFlowConfiguration.storage = localStorage;
        const authWellKnownEndpoints = new AuthWellKnownEndpoints();
        authWellKnownEndpoints.issuer = config.stsServer;
        authWellKnownEndpoints.jwks_uri = `${config.stsServer}/.well-known/openid-configuration/jwks`;
        authWellKnownEndpoints.authorization_endpoint = `${config.stsServer}/connect/authorize`;
        authWellKnownEndpoints.token_endpoint = `${config.stsServer}/connect/token`;
        authWellKnownEndpoints.userinfo_endpoint = `${config.stsServer}/connect/userinfo`;
        authWellKnownEndpoints.end_session_endpoint = `${config.stsServer}/connect/endsession`;
        authWellKnownEndpoints.check_session_iframe = `${config.stsServer}/connect/checksession`;
        authWellKnownEndpoints.revocation_endpoint = `${config.stsServer}/connect/revocation`;
        authWellKnownEndpoints.introspection_endpoint = `${config.stsServer}/connect/introspect`;
        this.oidcSecurityService.setupModule(openIDImplicitFlowConfiguration, authWellKnownEndpoints);

  }
}
