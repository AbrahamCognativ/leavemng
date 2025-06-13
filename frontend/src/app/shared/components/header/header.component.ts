import { Component, NgModule, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AuthService, IUser } from '../../services';
import { UserPanelModule } from '../user-panel/user-panel.component';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxToolbarModule } from 'devextreme-angular/ui/toolbar';

import { Router } from '@angular/router';
import {ThemeSwitcherModule} from "../theme-switcher/theme-switcher.component";
import { UserStateService } from '../../services/user-state.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-header',
  templateUrl: 'header.component.html',
  styleUrls: ['./header.component.scss'],
  standalone: false
})

export class HeaderComponent implements OnInit, OnDestroy {
  @Output()
  menuToggle = new EventEmitter<boolean>();

  @Input()
  menuToggleEnabled = false;

  @Input()
  title!: string;

  user: IUser | null = { email: '', id: '', role_band: '', role_title: '' };
  private userSubscription: Subscription | null = null;

  userMenuItems = [{
    text: 'Profile',
    icon: 'user',
    onClick: () => {
      this.router.navigate(['/profile']);
    }
  },
  {
    text: 'Logout',
    icon: 'runner',
    onClick: () => {
      this.authService.logOut();
    }
  }];

  constructor(
    private authService: AuthService, 
    private router: Router,
    private userStateService: UserStateService
  ) { }

   ngOnInit() {
    // Subscribe to user state changes for real-time updates
    this.userSubscription = this.userStateService.user$.subscribe(user => {
      if (user) {
        this.user = user;
      }
    });

    // Also load initial user data
    try {
      this.authService.getUser().then((e) => {
        if (e.data) {
          this.user = e.data;
          
          // If profile_image_url exists but avatarUrl doesn't, map it
          if (this.user && this.user.profile_image_url && !this.user.avatarUrl) {
            this.user.avatarUrl = this.user.profile_image_url;
          }
          
          // Update the user state service
          this.userStateService.updateUser(this.user);
        }
      });
    } catch (err) {
      console.error('Invalid user JSON in localStorage:', err);
    }
  }

  ngOnDestroy() {
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
  }

  toggleMenu = () => {
    this.menuToggle.emit();
  }
}

@NgModule({
  imports: [
    CommonModule,
    DxButtonModule,
    UserPanelModule,
    DxToolbarModule,
    ThemeSwitcherModule,
  ],
  declarations: [ HeaderComponent ],
  exports: [ HeaderComponent ]
})
export class HeaderModule { }
