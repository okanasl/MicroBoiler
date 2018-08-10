import { Component } from '@angular/core';
import { NavController, ToastController, Platform } from 'ionic-angular';
import { OidcSecurityService } from 'angular-auth-oidc-client';
import { InAppBrowser } from '@ionic-native/in-app-browser';
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
    private iab: InAppBrowser,
    private platform: Platform,
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
    this.platform.ready().then(() => {
      this.oidcSecurityService.authorize((authUrl) => {
        this.loginWithInnerAuth(authUrl).then(data => {
            this.oidcSecurityService.authorizedCallback(data.hashString);
            console.log("s")
        }, (error) => {
          console.log(error);
          console.log("ee")
        });
    });
  });
    
      // window.addEventListener('login_callback_message', this.loginCallbackLogic.bind(this), false);
      
      
      // window.open(authUrl, '_blank', 'toolbar=1,location=111,menubar=0,left=,width=500,height=600');
    
  }
  loginWithInnerAuth(authUrl) : Promise<any>
  {
    return new Promise(function(resolve, reject) {
      const browserRef = window.cordova.InAppBrowser.open(authUrl, '_blank',
        'location=no,clearsessioncache=yes,clearcache=yes');
        browserRef.addEventListener('loadstop',(event) => {
          console.log("event")
          console.log(event)
          if ((event.url).indexOf('localhost:8000') !== -1) {
            browserRef.removeEventListener("exit", (event) => {});
            browserRef.close();
            let lastIndex = event.url.lastIndexOf('/')
            if (lastIndex == -1) reject();
            const responseHash = ((event.url).substring(++lastIndex))
            console.log(responseHash)
            console.log("event.url")
            console.log(event.url)
            console.log(responseHash) 
            
            resolve({hasString:responseHash})
          }else{
            reject()
          }
        });
    });
  }
}
