import { Component } from '@angular/core';
import { NavController, ToastController } from 'ionic-angular';
import { OidcSecurityService } from 'angular-auth-oidc-client';
declare const window: any;
declare var cordova:any;
@Component({
  selector: 'page-login',
  templateUrl: 'login.html'
})
export class LoginPage {
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
      const browser = cordova.InAppBrowser.open(authUrl, '_blank',
        'location=no,clearsessioncache=yes,clearcache=yes');
      browser.addEventListener('loadstart', (event) => {
        console.log(event)
        if ((event.url).indexOf('localhost:8000') === 0) {
          browser.removeEventListener('exit', () => {});
          browser.close();
          const responseHash = ((event.url).split('#')[1])
          console.log(event.url)
          console.log(responseHash) 
          this.oidcSecurityService.authorizedCallback(responseHash)
          
        }
    });
  }
}
