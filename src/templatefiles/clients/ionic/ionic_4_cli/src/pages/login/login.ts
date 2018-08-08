import { Component } from '@angular/core';
import { IonicPage, NavController, ToastController } from 'ionic-angular';
import { OidcSecurityService } from 'angular-auth-oidc-client';
@IonicPage()
@Component({
  selector: 'page-login',
  templateUrl: 'login.html'
})
export class LoginPage {
  // The account fields for the login form.
  // If you're using the username field with or without email, make
  // sure to add it to the type
  // Our translated text strings
  private loginErrorString: string;
  private userData: any;
  private isAuthorized: boolean;
  constructor(public navCtrl: NavController,
    public oidcSecurityService: OidcSecurityService,
    public toastCtrl: ToastController) {
      this.oidcSecurityService.getUserData().subscribe(userdata=>{
        this.userData = userdata;
    })
    this.oidcSecurityService.getIsAuthorized().subscribe(isAuthorized=>{
        this.isAuthorized = isAuthorized;
    })
  }

  // Attempt to login in through our User service
  login() {
    this.oidcSecurityService.authorize((authUrl) => {
      // window.addEventListener('login_callback_message', this.loginCallbackLogic.bind(this), false);
      
      this.loginWithInnerAuth(authUrl);
      // window.open(authUrl, '_blank', 'toolbar=1,location=111,menubar=0,left=,width=500,height=600');
    });
  }
  loginWithInnerAuth(authUrl)
  {
    return new Promise((resolve, reject) => {
      const browser = window.cordova.InAppBrowser.open(authUrl, '_blank',
        'location=no,clearsessioncache=yes,clearcache=yes');
      browser.addEventListener('loadstart', (event) => {
        if ((event.url).indexOf('http://localhost:8100') === 0) {
          browser.removeEventListener('exit', () => {});
          browser.close();
          const responseHash = ((event.url).split('#')[1])
          this.oidcSecurityService.authorizedCallback(responseHash)
          resolve();
        }
      });
    });
  }
}
