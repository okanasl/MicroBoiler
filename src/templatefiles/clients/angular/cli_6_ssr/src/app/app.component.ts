import {Component} from '@angular/core';

@Component({
  selector: 'app-root',
  template: `
  <h1>Your Angular App (Universal)</h1>
  <a routerLink="/">Home</a>
  <a routerLink="/login">Login Page</a>
  <a routerLink="/lazy">Lazy</a>
  <a routerLink="/lazy/nested">Lazy_Nested</a>
  <router-outlet></router-outlet>
  `,
  styles: []
})
export class AppComponent {

}
