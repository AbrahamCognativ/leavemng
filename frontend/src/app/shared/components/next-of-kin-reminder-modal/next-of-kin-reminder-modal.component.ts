import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { NextOfKinService } from '../../services/next-of-kin.service';
import { UserStateService } from '../../services/user-state.service';
import { NextOfKinContact } from '../../../models/next-of-kin.model';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-next-of-kin-reminder-modal',
  templateUrl: './next-of-kin-reminder-modal.component.html',
  styleUrls: ['./next-of-kin-reminder-modal.component.scss'],
  standalone: false
})
export class NextOfKinReminderModalComponent implements OnInit, OnDestroy {
  isVisible: boolean = false;
  nextOfKinContacts: NextOfKinContact[] = [];
  isAdmin: boolean = false;
  private userSubscription: Subscription | null = null;
  private checkInterval: any;

  constructor(
    private router: Router,
    private nextOfKinService: NextOfKinService,
    private userStateService: UserStateService
  ) {}

  ngOnInit(): void {
    // Subscribe to user state changes
    this.userSubscription = this.userStateService.user$.subscribe(user => {
      if (user) {
        this.isAdmin = user.role_band === 'Admin' || user.role_title === 'Admin';
        if (!this.isAdmin) {
          this.loadNextOfKinContacts();
        } else {
          this.isVisible = false; // Hide modal for admin users
        }
      } else {
        this.isVisible = false; // Hide modal if no user
      }
    });
    
        // Subscribe to route changes to hide modal when on profile page
        this.router.events.pipe(
          filter(event => event instanceof NavigationEnd)
        ).subscribe((event: NavigationEnd) => {
          if (event.url === '/profile') {
            this.isVisible = false;
          }
        });
        
        // Start timer based on initial contact count
        this.updateTimerBasedOnContacts();
  }

  ngOnDestroy(): void {
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
    }
  }

  private loadNextOfKinContacts(): void {
    this.nextOfKinService.getNextOfKin().subscribe({
      next: (contacts) => {
        this.nextOfKinContacts = contacts;
        this.showModalIfNeeded();
        this.updateTimerBasedOnContacts();
      },
      error: (error) => {
        console.error('Failed to load next of kin contacts:', error);
        // Show modal even if there's an error loading contacts
        this.showModalIfNeeded();
        this.updateTimerBasedOnContacts();
      }
    });
  }

  private showModalIfNeeded(): void {
    // Don't show modal if user is on profile page
    if (this.router.url === '/profile') {
      return;
    }
    
    // Show modal if user is not admin and has no next of kin contacts
    if (!this.isAdmin && this.nextOfKinContacts.length === 0) {
      this.isVisible = true;
    }
  }

  private updateTimerBasedOnContacts(): void {
    // Stop existing timer
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }

    // Only start timer if user has no contacts and is not admin
    if (!this.isAdmin && this.nextOfKinContacts.length === 0) {
      this.startReminderTimer();
    }
  }

  private startReminderTimer(): void {
    // Check every 5 seconds if modal should be shown
    this.checkInterval = setInterval(() => {
      const currentUser = this.userStateService.getCurrentUser();
      if (currentUser && !this.isAdmin && this.router.url !== '/profile') {
        this.loadNextOfKinContacts();
      }
    }, 5000);
  }

  goToProfile(): void {
    this.isVisible = false;
    this.router.navigate(['/profile']);
  }

  dismissModal(): void {
    this.isVisible = false;
  }

  // Public method to refresh contacts (can be called from profile page)
  refreshContacts(): void {
    this.loadNextOfKinContacts();
  }
}
