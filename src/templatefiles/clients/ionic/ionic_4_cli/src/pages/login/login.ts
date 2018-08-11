import { Component } from '@angular/core';
import { NavController, ToastController, Platform } from 'ionic-angular';
import { OidcSecurityService } from 'angular-auth-oidc-client';
import { InAppBrowser } from '@ionic-native/in-app-browser';
import { authConfig } from './authconfig';
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

  login() {
    this.platform.ready().then(() => {
      this.oidcSecurityService.authorize((authUrl) => {
        this.loginWithInnerAuth(authUrl).then(responseHash => {
            this.oidcSecurityService.authorizedCallback(responseHash);
        }, (error) => {
          console.log(error);
        });
      });
    });
  }
  loginWithInnerAuth(authUrl) : Promise<any>
  {
    return new Promise(function(resolve, reject) {
      const browserRef = window.cordova.InAppBrowser.open(authUrl, '_blank',
        'location=no,clearsessioncache=yes,clearcache=yes');
        browserRef.addEventListener('loadstop',(event) => {
          if ((event.url).indexOf('localhost:8000') !== -1) {
            browserRef.removeEventListener("exit", (event) => {});
            browserRef.close();
            let lastIndex = event.url.lastIndexOf('#')
            if (lastIndex === -1){
              reject("Hash is not valid");
            } 
            const responseHash = ((event.url).substring(++lastIndex))            
            resolve(responseHash)
          }else{
            reject("Check your identityserver redirect uri")
          }
        });
    });
  }
  logout(){
    // TODO:
    // Should get endSessionUrl
    const endSessionUrl  = authConfig.stsServer;
    this.platform.ready().then(() => {
      this.logoutWithIFrame(endSessionUrl).then((isLogout)=>{
        if (isLogout)
        {
          // TODO:
          // Reset Auth Data
          this.oidcSecurityService.refreshSession();
        }   
      })        
    });
  }

  logoutWithIFrame(endSessionUrl) : Promise<any> {
    return new Promise(function(resolve, reject) {
      const browserRef = window.cordova.InAppBrowser.open(endSessionUrl, '_blank',
        'location=no,clearsessioncache=yes,clearcache=yes,hidden=yes');
        browserRef.addEventListener('loadstop',(event) => {
          if ((event.url).indexOf('localhost:5000') !== -1) {
            browserRef.removeEventListener("exit", (event) => {});
            browserRef.close();            
            resolve(true)
          }else{
            reject("Check your identityserver redirect uri")
          }
        });
    });
  }
}
