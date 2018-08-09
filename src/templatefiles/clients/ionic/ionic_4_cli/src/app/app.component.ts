import { Component } from '@angular/core';
import { Platform } from 'ionic-angular';
import { StatusBar } from '@ionic-native/status-bar';
import { SplashScreen } from '@ionic-native/splash-screen';

import { TabsPage } from '../pages/tabs/tabs';
import { Router, NavigationStart } from '@angular/router';

@Component({
  templateUrl: 'app.html'
})
export class MyApp {
  rootPage:any = TabsPage;

  constructor(platform: Platform, 
    statusBar: StatusBar,
    private router: Router,
   splashScreen: SplashScreen) {
    platform.ready().then(() => {
      // Okay, so the platform is ready and our plugins are available.
      // Here you can do any higher level native things you might need.
      statusBar.styleDefault();
      splashScreen.hide();
    });
    this.router.events.filter((event: any) => event instanceof NavigationStart)
    .subscribe((data: NavigationStart) => {
        if (data.url.indexOf('id_token') !== 0) {
            this.router.navigateByUrl('/');
        }
    });
  }
  
}
